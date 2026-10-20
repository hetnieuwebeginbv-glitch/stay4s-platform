#!/usr/bin/env python3
"""Unit-tests voor model_v2.py (Titaan). Draait op CPU met titaan-pico."""
import os, sys, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from torch.nn import functional as F
from model_v2 import build_v2, Titaan, SIZES_V2

torch.manual_seed(0)
V = 256
ok = 0

def check(name, cond):
    global ok
    assert cond, f"FAIL: {name}"
    ok += 1
    print(f"  ok: {name}")

# --- 1. vormen & forward (MoE en dicht) ---
for size in ("titaan-pico",):
    m = build_v2(V, size)
    x = torch.randint(0, V, (2, 32))
    y = torch.randint(0, V, (2, 32))
    logits, loss = m(x, y)
    check("logits-vorm", logits.shape == (2, 32, V))
    check("loss-scalar", loss.dim() == 0 and torch.isfinite(loss))
    g, none_loss = m(x)
    check("generatie-pad", g.shape == (2, 1, V) and none_loss is None)

m = build_v2(V, "titaan-pico")
check("weight-tying", m.wte.weight.data_ptr() == m.lm_head.weight.data_ptr())

# --- 2. params tellen (totaal vs actief) ---
tot, act = m.num_params(), m.num_params_active()
print(f"  pico: totaal={tot:,} actief={act:,}")
check("actief<totaal bij MoE", act < tot)
mt = build_v2(32000, "titaan")
print(f"  titaan: totaal={mt.num_params():,} actief={mt.num_params_active():,}")
check("titaan-actief rond 0.4-0.6B", 0.35e9 < mt.num_params_active() < 0.65e9)
check("titaan-totaal rond 1-2B", 1.0e9 < mt.num_params() < 2.2e9)
del mt

# --- 3. backward: grads stromen ---
m = build_v2(V, "titaan-pico")
x = torch.randint(0, V, (2, 32)); y = torch.randint(0, V, (2, 32))
_, loss = m(x, y)
loss.backward()
n_grad = sum(1 for p in m.parameters() if p.grad is not None and p.grad.abs().sum() > 0)
n_all = sum(1 for p in m.parameters())
print(f"  params met grad: {n_grad}/{n_all}")
check("meeste params hebben grad", n_grad >= n_all * 0.6)  # ongekozen experts mogen 0 zijn
check("router heeft grad", m.h[0].mlp.router.weight.grad is not None)

# --- 4. overfit-test: leert het ding? ---
m = build_v2(V, "titaan-pico")
opt = torch.optim.AdamW(m.parameters(), lr=3e-3)
xb = torch.randint(0, V, (4, 64)); yb = torch.randint(0, V, (4, 64))
l0 = None
for i in range(300):
    _, loss = m(xb, yb)
    if l0 is None: l0 = loss.item()
    opt.zero_grad(); loss.backward(); opt.step()
print(f"  overfit: {l0:.3f} -> {loss.item():.3f}")
check("overfit leert (loss < 0.15 * start)", loss.item() < 0.15 * l0)

# --- 5. MoE-dekking: alle experts worden gebruikt ---
m.eval()
with torch.no_grad():
    xs = torch.randint(0, V, (8, 128))
    used = set()
    for blk in m.h:
        pass
    # tel router-keuzes over hele model via eerste MoE-laag
    moe = m.h[0].mlp
    h = m.wte(xs)
    lg = moe.router(h.view(-1, h.shape[-1]))
    topi = lg.float().softmax(-1).topk(moe.top_k, -1).indices
    used = set(topi.flatten().tolist())
print(f"  experts gebruikt: {sorted(used)}")
check("alle 4 experts komen aan bod", len(used) == 4)

# --- 6. determinisme ---
torch.manual_seed(42); m1 = build_v2(V, "titaan-pico")
torch.manual_seed(42); m2 = build_v2(V, "titaan-pico")
torch.manual_seed(7); xa = torch.randint(0, V, (2, 16))
m1.eval(); m2.eval()
with torch.no_grad():
    la, _ = m1(xa); lb, _ = m2(xa)
check("deterministisch bij zelfde seed", torch.equal(la, lb))

# --- 7. gradient checkpointing pad ---
m = build_v2(V, "titaan-pico"); m.grad_ckpt = True; m.train()
_, loss = m(xb, yb); loss.backward()
check("grad_ckpt backward werkt", torch.isfinite(loss))

# --- 8. causaliteit: toekomst lekt niet ---
m = build_v2(V, "titaan-pico"); m.eval()
xa = torch.randint(0, V, (1, 32)); xb2 = xa.clone(); xb2[0, -1] = (xb2[0, -1] + 1) % V
with torch.no_grad():
    la = m.lm_head(m.ln_f(sum([torch.zeros(1),])) ) if False else None
    fa, _ = m(xa, xa); fb, _ = m(xb2, xb2)
# logits op posities 0..-2 mogen niet veranderen als alleen laatste token wijzigt
check("causaal (vroege posities ongevoelig)", torch.allclose(fa[:, :-1], fb[:, :-1], atol=1e-5))

print(f"\nALLE {ok} TESTS GESLAAGD")
