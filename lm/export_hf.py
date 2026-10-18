#!/usr/bin/env python3
"""Stay4S-LM ckpt -> HuggingFace GPT2 formaat (voor GGUF conversie)."""
import os, sys, torch
sys.path.insert(0, "/root/stay4s-llm/scripts")
from model import build
from transformers import GPT2Config, GPT2LMHeadModel, PreTrainedTokenizerFast
from tokenizers import Tokenizer

CKPT = "/root/stay4s-llm/runs/stay4s-lm-001-reus/ckpt_best.pt"
TOK  = "/root/stay4s-llm/data/tokenizer/tokenizer.json"
OUT  = "/root/stay4s-llm/export/reus-hf"

ck = torch.load(CKPT, map_location="cpu", weights_only=False)
vocab = ck["vocab_size"]
model = build(vocab, "reus", 0.0)
model.load_state_dict(ck["model"])
model.eval()

cfg = GPT2Config(
    vocab_size=vocab, n_positions=1024, n_embd=1280, n_layer=24, n_head=16,
    activation_function="gelu_new", resid_pdrop=0.0, embd_pdrop=0.0,
    attn_pdrop=0.0, layer_norm_epsilon=1e-5,
)
hf = GPT2LMHeadModel(cfg)

sd = dict(ck["model"])
sd = {k: v for k, v in sd.items() if not k.endswith(".attn.bias")}
sd.pop("lm_head.weight", None)  # tied aan wte
# HF GPT2 gebruikt Conv1D [in,out]; wij nn.Linear [out,in] -> transponeren
for k in list(sd):
    if k.endswith(("c_attn.weight", "c_proj.weight", "c_fc.weight")):
        sd[k] = sd[k].t().contiguous()
missing, unexpected = hf.load_state_dict(sd, strict=False)
print("missing:", missing)
print("unexpected:", unexpected)

tok = Tokenizer.from_file(TOK)
ids = torch.tensor([tok.encode("Amsterdam is de hoofdstad").ids], dtype=torch.long)
with torch.no_grad():
    a = model(ids)[0] if isinstance(model(ids), tuple) else model(ids)
    b = hf(ids).logits
diff = (a - b[:, -1:, :]).abs().max().item()
print("max logits diff:", diff)
assert diff < 1e-3, "LOGITS KOMEN NIET OVEREEN"

os.makedirs(OUT, exist_ok=True)
hf.save_pretrained(OUT)
PreTrainedTokenizerFast(tokenizer_file=TOK).save_pretrained(OUT)
print("OK ->", OUT)

