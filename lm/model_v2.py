#!/usr/bin/env python3
"""Stay4S-LM v2 "Titaan" - moderne from-scratch architectuur (zelfde interface als model.py).

Modernisering t.o.v. de GPT-2-stijl v1:
- RoPE (rotary position embeddings) i.p.v. geleerde posities -> context 4096+
- RMSNorm (pre-norm) i.p.v. LayerNorm
- SwiGLU i.p.v. GELU-MLP
- GQA (grouped-query attention) -> kleine KV-cache, snelle Pi-inferentie
- Optionele MoE-MLP (token-choice top-k + Switch load-balancing)
- z-loss op de logits (optioneel), standaard dropout 0.0
- gradient-checkpointing-vlag zoals v1 (self.grad_ckpt)

Interface: build_v2(vocab_size, size) -> model met forward(idx, targets) -> (logits, loss).
"""
import math
from dataclasses import dataclass

import torch
import torch.nn as nn
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint as _grad_ckpt


@dataclass
class V2Cfg:
    n_layer: int
    n_head: int
    n_kv_head: int
    n_embd: int
    block_size: int
    ffn_hidden: int          # per-expert (MoE) of totale (dicht) SwiGLU-hidden
    moe_experts: int = 0     # 0 = dicht
    moe_top_k: int = 2
    aux_coef: float = 0.01   # Switch load-balancing
    z_coef: float = 0.0      # logits z-loss (0 = uit)
    dropout: float = 0.0
    rope_base: float = 10000.0


SIZES_V2 = {
    # testformaat voor unit-tests (CPU-sneltrein)
    "titaan-pico": V2Cfg(2, 4, 2, 64, 128, 96, moe_experts=4, moe_top_k=2),
    # dicht referentiepunt (~350M): zelfde budget als MoE-actief
    "titaan-dicht": V2Cfg(24, 20, 5, 1280, 4096, 3584, moe_experts=0),
    # de kicker: ~1,5B totaal / ~0,5B actief per token
    "titaan": V2Cfg(24, 20, 5, 1280, 4096, 1792, moe_experts=8, moe_top_k=2),
}


class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x):
        xf = x.float()
        out = xf * torch.rsqrt(xf.pow(2).mean(-1, keepdim=True) + self.eps)
        return (out * self.weight.float()).to(x.dtype)


def precompute_rope(head_dim, max_seq, base=10000.0):
    inv = 1.0 / (base ** (torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim))
    t = torch.arange(max_seq, dtype=torch.float32)
    freqs = torch.outer(t, inv)                       # [T, D/2]
    return freqs.cos(), freqs.sin()


def apply_rope(x, cos, sin):
    # x: [B, H, T, D]; cos/sin: [1, 1, T, D/2] fp32
    xf = x.float()
    x1, x2 = xf.chunk(2, dim=-1)
    out = torch.cat([x1 * cos - x2 * sin, x1 * sin + x2 * cos], dim=-1)
    return out.to(x.dtype)


class Attention(nn.Module):
    def __init__(self, cfg: V2Cfg):
        super().__init__()
        assert cfg.n_embd % cfg.n_head == 0
        assert cfg.n_head % cfg.n_kv_head == 0
        self.n_head = cfg.n_head
        self.n_kv = cfg.n_kv_head
        self.head_dim = cfg.n_embd // cfg.n_head
        self.q = nn.Linear(cfg.n_embd, cfg.n_head * self.head_dim, bias=False)
        self.k = nn.Linear(cfg.n_embd, cfg.n_kv_head * self.head_dim, bias=False)
        self.v = nn.Linear(cfg.n_embd, cfg.n_kv_head * self.head_dim, bias=False)
        self.o = nn.Linear(cfg.n_head * self.head_dim, cfg.n_embd, bias=False)
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x, cos, sin):
        B, T, _ = x.shape
        q = self.q(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = self.k(x).view(B, T, self.n_kv, self.head_dim).transpose(1, 2)
        v = self.v(x).view(B, T, self.n_kv, self.head_dim).transpose(1, 2)
        q = apply_rope(q, cos, sin)
        k = apply_rope(k, cos, sin)
        if self.n_kv != self.n_head:
            rep = self.n_head // self.n_kv
            k = k.repeat_interleave(rep, dim=1)
            v = v.repeat_interleave(rep, dim=1)
        y = F.scaled_dot_product_attention(
            q, k, v, is_causal=True,
            dropout_p=self.drop.p if self.training else 0.0,
        )
        y = y.transpose(1, 2).contiguous().view(B, T, -1)
        return self.o(y)


class SwiGLU(nn.Module):
    def __init__(self, n_embd, hidden):
        super().__init__()
        self.w1 = nn.Linear(n_embd, hidden, bias=False)   # gate
        self.w3 = nn.Linear(n_embd, hidden, bias=False)   # up
        self.w2 = nn.Linear(hidden, n_embd, bias=False)   # down

    def forward(self, x):
        return self.w2(F.silu(self.w1(x)) * self.w3(x))


class MoE(nn.Module):
    """Token-choice top-k routing, Switch-style load-balancing."""

    def __init__(self, cfg: V2Cfg):
        super().__init__()
        self.n_experts = cfg.moe_experts
        self.top_k = cfg.moe_top_k
        self.router = nn.Linear(cfg.n_embd, self.n_experts, bias=False)
        self.experts = nn.ModuleList(
            [SwiGLU(cfg.n_embd, cfg.ffn_hidden) for _ in range(self.n_experts)]
        )

    def forward(self, x):
        B, T, C = x.shape
        xf = x.view(-1, C)
        logits = self.router(xf)                          # [N, E]
        probs = F.softmax(logits.float(), dim=-1)
        topv, topi = probs.topk(self.top_k, dim=-1)       # [N, k]
        topv = topv / topv.sum(-1, keepdim=True).clamp_min(1e-9)
        out = torch.zeros_like(xf)
        for e in range(self.n_experts):
            sel = (topi == e).any(-1)                     # [N]
            if not bool(sel.any()):
                continue
            w = (topv * (topi == e).float()).sum(-1)[sel].to(x.dtype)
            out[sel] = out[sel] + w.unsqueeze(-1) * self.experts[e](xf[sel])
        # Switch load-balancing: E * sum(f_e * P_e)
        f = torch.stack([(topi == e).any(-1).float().mean() for e in range(self.n_experts)])
        aux = self.n_experts * (f * probs.mean(0)).sum()
        return out.view(B, T, C), aux


class Block(nn.Module):
    def __init__(self, cfg: V2Cfg):
        super().__init__()
        self.ln1 = RMSNorm(cfg.n_embd)
        self.attn = Attention(cfg)
        self.ln2 = RMSNorm(cfg.n_embd)
        self.is_moe = cfg.moe_experts > 0
        self.mlp = MoE(cfg) if self.is_moe else SwiGLU(cfg.n_embd, cfg.ffn_hidden)
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x, cos, sin):
        x = x + self.drop(self.attn(self.ln1(x), cos, sin))
        h = self.ln2(x)
        if self.is_moe:
            m, aux = self.mlp(h)
            return x + self.drop(m), aux
        return x + self.drop(self.mlp(h)), x.new_zeros(())


class Titaan(nn.Module):
    def __init__(self, vocab_size, cfg: V2Cfg):
        super().__init__()
        self.cfg = cfg
        self.block_size = cfg.block_size
        self.wte = nn.Embedding(vocab_size, cfg.n_embd)
        self.h = nn.ModuleList([Block(cfg) for _ in range(cfg.n_layer)])
        self.ln_f = RMSNorm(cfg.n_embd)
        self.lm_head = nn.Linear(cfg.n_embd, vocab_size, bias=False)
        self.wte.weight = self.lm_head.weight             # weight tying zoals v1
        self.drop = nn.Dropout(cfg.dropout)
        cos, sin = precompute_rope(cfg.n_embd // cfg.n_head, cfg.block_size, cfg.rope_base)
        self.register_buffer("rope_cos", cos, persistent=False)
        self.register_buffer("rope_sin", sin, persistent=False)
        self.grad_ckpt = False
        self.apply(self._init)
        for name, p in self.named_parameters():
            if name.endswith("w2.weight") or name.endswith("o.weight"):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * cfg.n_layer))

    def _init(self, m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)

    def _rope(self, T, device, dtype):
        cos = self.rope_cos[:T].to(device=device).float()[None, None]
        sin = self.rope_sin[:T].to(device=device).float()[None, None]
        return cos, sin

    def forward(self, idx, targets=None):
        B, T = idx.size()
        assert T <= self.block_size, f"seq len {T} > block {self.block_size}"
        cos, sin = self._rope(T, idx.device, idx.dtype)
        x = self.drop(self.wte(idx))
        aux_sum = x.new_zeros(())
        for blk in self.h:
            if self.grad_ckpt and self.training:
                x, aux = _grad_ckpt(blk, x, cos, sin, use_reentrant=False)
            else:
                x, aux = blk(x, cos, sin)
            aux_sum = aux_sum + aux
        x = self.ln_f(x)
        if targets is not None:
            logits = self.lm_head(x)
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)).float(), targets.view(-1))
            if self.cfg.z_coef > 0:
                loss = loss + self.cfg.z_coef * torch.logsumexp(
                    logits.view(-1, logits.size(-1)).float(), dim=-1).pow(2).mean()
            if self.cfg.moe_experts > 0:
                loss = loss + self.cfg.aux_coef * aux_sum / len(self.h)
            return logits, loss
        return self.lm_head(x[:, [-1], :]), None

    def num_params(self):
        return sum(p.numel() for p in self.parameters())

    def num_params_active(self):
        """Params die per token meedoen (MoE: shared + top_k experts)."""
        total = self.num_params()
        if self.cfg.moe_experts == 0:
            return total
        expert = sum(p.numel() for m in self.modules() if isinstance(m, MoE)
                     for e in m.experts for p in e.parameters())
        return total - expert + expert * self.cfg.moe_top_k // self.cfg.moe_experts


def build_v2(vocab_size, size="titaan"):
    return Titaan(vocab_size, SIZES_V2[size])
