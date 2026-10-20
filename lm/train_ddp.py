#!/usr/bin/env python3
"""Stay4S-LM — Stap 5: multi-GPU training (DDP, torch.distributed).

Identiek aan train.py maar dan over N GPU's via torchrun:
    torchrun --nproc_per_node=2 train_ddp.py --size reus --block 1024 \
        --batch-size 4 --grad-accum 16 --max-iters 6000

Nieuw tov train.py:
- DDP: elke GPU eigen proces + eigen batches (seed + rank)
- --init-from <ckpt.pt>: hervat vanaf checkpoint (ook voor Fase 6 resume!)
- alleen rank 0 logt + checkpoint
- batch-size is PER GPU; effectief = batch x world_size x grad_accum
"""
import argparse, math, os, time
import numpy as np
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from model import build, SIZES


def get_batch(data, block, batch_size, device, gen):
    ix = torch.randint(len(data) - block - 1, (batch_size,), generator=gen)
    x = torch.stack([torch.from_numpy(data[i:i + block].astype(np.int64)) for i in ix])
    y = torch.stack([torch.from_numpy(data[i + 1:i + 1 + block].astype(np.int64)) for i in ix])
    return x.to(device, non_blocking=True), y.to(device, non_blocking=True)


def lr_at(it, warmup, max_iters, lr, min_lr):
    if it < warmup:
        return lr * it / max(1, warmup)
    if it > max_iters:
        return min_lr
    ratio = (it - warmup) / max(1, max_iters - warmup)
    coeff = 0.5 * (1.0 + math.cos(math.pi * ratio))
    return min_lr + coeff * (lr - min_lr)


@torch.no_grad()
def estimate_loss(model, train, val, block, batch_size, device, gen, iters=50):
    model.eval()
    out = {}
    for name, data in (("train", train), ("val", val)):
        losses = torch.zeros(iters)
        for k in range(iters):
            x, y = get_batch(data, block, batch_size, device, gen)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                _, loss = model(x, y)
            losses[k] = loss.item()
        out[name] = losses.mean().item()
    model.train()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/stay4s-llm"))
    ap.add_argument("--arch", choices=["v1", "v2"], default="v1",
                    help="v1 = model.py (GPT), v2 = model_v2.py (Titaan: RoPE/GQA/SwiGLU/MoE)")
    ap.add_argument("--size", default="nano", help="v1: %s | v2: SIZES_V2 in model_v2.py" % list(SIZES))
    ap.add_argument("--block", type=int, default=256)
    ap.add_argument("--batch-size", type=int, default=32, help="per GPU")
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--max-iters", type=int, default=2000)
    ap.add_argument("--eval-interval", type=int, default=200)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--lr", type=float, default=6e-4)
    ap.add_argument("--min-lr", type=float, default=6e-5)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--out", default=None)
    ap.add_argument("--init-from", default=None, help="pad naar ckpt om vanaf te hervatten")
    ap.add_argument("--opt8bit", action="store_true", help="bitsandbytes AdamW8bit (scheelt ~9GB bij 1.5B)")
    ap.add_argument("--grad-ckpt", action="store_true", help="gradient checkpointing (xl op 24GB)")
    ap.add_argument("--eval-batch", type=int, default=1)
    ap.add_argument("--bf16", action="store_true", help="model in bf16 (halveert geheugen)")
    a = ap.parse_args()

    # --- DDP init ---
    ddp = int(os.environ.get("WORLD_SIZE", "1")) > 1
    if ddp:
        dist.init_process_group(backend="nccl")
        rank = dist.get_rank()
        world = dist.get_world_size()
        local_rank = int(os.environ["LOCAL_RANK"])
        device = torch.device(f"cuda:{local_rank}")
        torch.cuda.set_device(device)
    else:
        rank, world, local_rank = 0, 1, 0
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    master = rank == 0
    # elke rank eigen random-stroom -> andere batches
    gen = torch.Generator().manual_seed(a.seed + rank * 1000)
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)

    out_dir = a.out or os.path.join(a.root, "runs", f"stay4s-lm-001-{a.size}-ddp")
    if master:
        os.makedirs(out_dir, exist_ok=True)
        log = open(os.path.join(out_dir, "train.log"), "a", encoding="utf-8")

    def say(*s):
        if master:
            line = " ".join(str(x) for x in s)
            print(line, flush=True)
            log.write(line + "\n")
            log.flush()

    ds_dir = os.path.join(a.root, "data", "datasets")
    train = np.memmap(os.path.join(ds_dir, "train.bin"), dtype=np.uint16, mode="r")
    val = np.memmap(os.path.join(ds_dir, "val.bin"), dtype=np.uint16, mode="r")
    say(f"ddp={ddp} world={world} | device={device} | train={len(train):,} val={len(val):,} tokens")

    from tokenizers import Tokenizer
    vocab_size = Tokenizer.from_file(
        os.path.join(a.root, "data", "tokenizer", "tokenizer.json")
    ).get_vocab_size()
    if a.arch == "v2":
        from model_v2 import build_v2, SIZES_V2
        assert a.size in SIZES_V2, f"onbekende v2-size {a.size!r}; kies uit {list(SIZES_V2)}"
        raw_model = build_v2(vocab_size, a.size).to(device)
    else:
        assert a.size in SIZES, f"onbekende v1-size {a.size!r}; kies uit {list(SIZES)}"
        raw_model = build(vocab_size, a.size, a.dropout).to(device)
    raw_model.grad_ckpt = a.grad_ckpt
    if a.bf16:
        raw_model = raw_model.to(torch.bfloat16)

    start_iter = 0
    if a.init_from and os.path.exists(a.init_from):
        ck = torch.load(a.init_from, map_location=device)
        raw_model.load_state_dict(ck["model"])
        start_iter = ck.get("iter", 0)
        say(f"hervat vanaf {a.init_from} (iter {start_iter}, val {ck.get('val_loss')})")

    model = DDP(raw_model, device_ids=[local_rank], gradient_as_bucket_view=True) if ddp else raw_model
    _act = f" actief={raw_model.num_params_active():,}" if a.arch == "v2" else ""
    say(f"model={a.arch}/{a.size} params={raw_model.num_params():,}{_act} block={a.block} "
        f"| effectieve batch={a.batch_size * world * a.grad_accum}")

    decay, no_decay = [], []
    for n, p in raw_model.named_parameters():
        (decay if p.dim() >= 2 else no_decay).append(p)
    groups = [{"params": decay, "weight_decay": 0.1}, {"params": no_decay, "weight_decay": 0.0}]
    if a.opt8bit:
        import bitsandbytes as bnb
        opt = bnb.optim.PagedAdamW8bit(groups, lr=a.lr, betas=(0.9, 0.95))
        say("optimizer: AdamW8bit (bitsandbytes)")
    else:
        opt = torch.optim.AdamW(groups, lr=a.lr, betas=(0.9, 0.95))

    t0 = time.time()
    best = float("inf")
    for it in range(start_iter, a.max_iters + 1):
        for g in opt.param_groups:
            g["lr"] = lr_at(it, a.warmup, a.max_iters, a.lr, a.min_lr)
        opt.zero_grad(set_to_none=True)
        for k in range(a.grad_accum):
            # geen gradient-sync op tussentijdse accum-stappen (sneller)
            ctx = model.no_sync() if (ddp and k < a.grad_accum - 1) else torch.enable_grad()
            with ctx:
                x, y = get_batch(train, a.block, a.batch_size, device, gen)
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=(device.type == "cuda")):
                    _, loss = model(x, y)
                    loss = loss / a.grad_accum
                loss.backward()
        torch.nn.utils.clip_grad_norm_(raw_model.parameters(), 1.0)
        opt.step()

        if it % a.eval_interval == 0 or it == a.max_iters:
            m = estimate_loss(raw_model, train, val, a.block, a.eval_batch, device, gen)
            dt = time.time() - t0
            say(f"iter {it:5d} | lr {lr_at(it, a.warmup, a.max_iters, a.lr, a.min_lr):.2e} "
                f"| train {m['train']:.4f} | val {m['val']:.4f} | {dt:6.1f}s")
            if master:
                ck = {"model": raw_model.state_dict(), "args": vars(a), "iter": it,
                      "val_loss": m["val"], "vocab_size": vocab_size}
                torch.save(ck, os.path.join(out_dir, "ckpt_last.pt"))
                if m["val"] < best:
                    best = m["val"]
                    torch.save(ck, os.path.join(out_dir, "ckpt_best.pt"))
        if ddp:
            dist.barrier()

    say(f"KLAAR. beste val loss={best:.4f} | ckpt in {out_dir}")
    if ddp:
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
