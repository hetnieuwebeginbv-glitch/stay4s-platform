#!/usr/bin/env python3
"""f7_watch.py - Stay4S Live Lab orchestrator (1 tick per aanroep).

Doet per tick:
1. Leest train.log op de Vast-box (iter/val/train/tempo)
2. GPU-status (util/mem/temp)
3. Herstart training vanaf ckpt_last als het proces dood is (max 3x)
4. Mijlpaal-samples: bij elke 1000 iters laat hij het lopende model NL-tekst schrijven (CPU op box)
5. Insurance: downloadt ckpt_best.pt naar K: als hij nieuwer is (achtergrond, hash-verified)
6. Publiceert status.json naar de Pi (stay4s.nl/lab)
Alleen stdlib. Print 1 regel samenvatting voor de automation-agent.
"""
import json, os, re, subprocess, sys, time
from datetime import datetime, timezone

ROOT = r"K:\stay4s\STAY4S-LM"
STATE_F = os.path.join(ROOT, "f7_state.json")
STATUS_F = os.path.join(ROOT, "lab", "status.json")
CKPT_LOCAL = os.path.join(ROOT, "checkpoints", "fase7_ckpt_best.pt")
SSH_BOX = ["ssh", "-o", "ConnectTimeout=25", "-o", "StrictHostKeyChecking=no", "-p", "30478", "root@ssh8.vast.ai"]
SCP_BOX = ["scp", "-o", "ConnectTimeout=25", "-o", "StrictHostKeyChecking=no", "-P", "30478"]
PI_KEY = r"C:\Users\Gebruiker\.ssh\stay4pi_ed25519"
SCP_PI = ["scp", "-o", "ConnectTimeout=25", "-i", PI_KEY]
PI_DEST = "Miesdevries@192.168.8.120:/var/www/lab/status.json"
RUN_DIR = "/root/stay4s-llm/runs/stay4s-lm-003-xl"
MAX_ITERS, TOK_PER_ITER, BURN = 13000, 131072, 0.9743
PROMPTS = ["Nederland is een land waar", "De toekomst van kunstmatige intelligentie is", "Op een mooie dag in Amsterdam"]

ITER_RE = re.compile(r"iter\s+(\d+) \| lr ([\d.e-]+) \| train ([\d.]+) \| val ([\d.]+) \| \s*([\d.]+)s")

def sh(cmd, timeout=100):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except Exception as e:
        return f"__ERR__ {e}"

def load_state():
    if os.path.exists(STATE_F):
        return json.load(open(STATE_F, encoding="utf-8"))
    return {"restarts": 0, "runtime_s": 0.0, "last_tick": None, "sampled": [], "sample_pending": None,
            "ckpt_mtime": 0, "download": None, "samples": [], "history": []}

def save_state(s):
    json.dump(s, open(STATE_F, "w", encoding="utf-8"), indent=1)

def main():
    st = load_state()
    now = time.time()
    out = sh(SSH_BOX + [f"tail -c 200000 /root/fase7_train.log; echo @@; pgrep -fc train_ddp.py; echo @@; "
                        f"nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader; "
                        f"echo @@; stat -c '%Y %s' {RUN_DIR}/ckpt_best.pt 2>/dev/null; echo @@; "
                        f"grep -c KLAAR /root/fase7_train.log; echo @@; ls /root/f7_samples/ 2>/dev/null"])
    parts = out.split("@@")
    log_tail = parts[0] if len(parts) > 0 else ""
    nproc = int((parts[1].strip() or "0").splitlines()[-1]) if len(parts) > 1 and parts[1].strip().splitlines() else 0
    gpu_lines = (parts[2].strip().splitlines() if len(parts) > 2 else [])
    ckpt_stat = parts[3].strip().split() if len(parts) > 3 else []
    klaar = (parts[4].strip() or "0") if len(parts) > 4 else "0"
    remote_samples = parts[5].strip().splitlines() if len(parts) > 5 else []

    iters = ITER_RE.findall(log_tail)
    hist = st["history"]
    for it, lr, tr, va, dt in iters:
        it = int(it)
        found = [h for h in hist if h[0] == it]
        if found:
            if len(found[0]) < 4:
                found[0].append(float(dt))
        else:
            hist.append([it, float(tr), float(va), float(dt)])
    hist.sort()
    cur_it = hist[-1][0] if hist else 0
    val_now, val_best = (hist[-1][2] if hist else None), (min(h[2] for h in hist) if hist else None)
    pts = [(h[0], h[3]) for h in hist if len(h) > 3]
    sp_iter = None
    if len(pts) >= 2:
        (i1, t1), (i2, t2) = pts[0], pts[-1]
        if i2 > i1 and t2 > t1:  # guard tegen dt-reset na herstart
            sp_iter = (t2 - t1) / (i2 - i1)
    if sp_iter is None:
        sp_iter = 14.4  # fallback: gemeten ~9,1k tok/s
    tok_s = TOK_PER_ITER / sp_iter
    eta_h = (MAX_ITERS - cur_it) * sp_iter / 3600
    gpus = []
    for gl in gpu_lines:
        m = re.match(r"\s*(\d+)\s*%,\s*(\d+)\s*MiB,\s*(\d+)", gl)
        if m: gpus.append({"util": int(m.group(1)), "mem": int(m.group(2)), "temp": int(m.group(3))})

    running = nproc >= 2
    done = klaar.strip().startswith("1") or (klaar.strip().isdigit() and int(klaar.strip()) >= 1)
    if st["last_tick"] and running:
        st["runtime_s"] += min(now - st["last_tick"], 2400)
    st["last_tick"] = now
    state = "klaar" if done else ("training" if running else "gestopt")

    # --- herstart bij crash (max 3x) ---
    restart_note = ""
    if not running and not done and st["restarts"] < 3 and "__ERR__" not in out:
        cmd = (f"cd /root/stay4s-llm && setsid nohup env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True "
               f"torchrun --standalone --nproc_per_node=2 scripts/train_ddp.py --size xl --block 1024 "
               f"--batch-size 8 --grad-accum 8 --max-iters {MAX_ITERS} --eval-interval 500 --warmup 500 "
               f"--lr 3e-4 --min-lr 3e-5 --opt8bit --grad-ckpt --bf16 "
               f"--init-from {RUN_DIR}/ckpt_last.pt --out {RUN_DIR} >> /root/fase7_train.log 2>&1 < /dev/null &")
        sh(SSH_BOX + [cmd], timeout=40)
        st["restarts"] += 1
        state = "training"
        restart_note = f" HERSTART #{st['restarts']}"

    # --- mijlpaal-samples starten (elke 1000 iters) ---
    milestone = (cur_it // 1000) * 1000
    if running and milestone >= 1000 and milestone not in st["sampled"] and st["sample_pending"] != milestone:
        jobs = " ; ".join(
            f"OMP_NUM_THREADS=12 python3 /root/stay4s-llm/scripts/sample.py --ckpt {RUN_DIR}/ckpt_best.pt "
            f"--prompt '{p}' --tokens 80 --temperature 0.8 > /root/f7_samples/m{milestone}_{i}.txt 2>&1"
            for i, p in enumerate(PROMPTS))
        sh(SSH_BOX + [f"mkdir -p /root/f7_samples && setsid nohup bash -c \"{jobs}\" > /dev/null 2>&1 < /dev/null &"], timeout=40)
        st["sample_pending"] = milestone

    # --- klaarstaande samples ophalen ---
    if st["sample_pending"] is not None:
        m = st["sample_pending"]
        ready = [f for f in remote_samples if f.startswith(f"m{m}_")]
        if len(ready) >= len(PROMPTS):
            for i, p in enumerate(PROMPTS):
                txt = sh(SSH_BOX + [f"cat /root/f7_samples/m{m}_{i}.txt"], timeout=40)
                body = txt.split("---")[-1].strip() if "---" in txt else txt.strip()
                body = "\n".join(body.splitlines()[1:]).strip() if body else ""
                if body:
                    st["samples"].append({"iter": m, "prompt": p, "text": body[:600], "val": round(val_best or 0, 4)})
            st["samples"] = st["samples"][-6:]
            st["sampled"].append(m)
            st["sample_pending"] = None

    # --- insurance sync (achtergrond-download, voltooit volgende tick) ---
    if ckpt_stat and len(ckpt_stat) == 2:
        mt, sz = int(ckpt_stat[0]), int(ckpt_stat[1])
        dl = st.get("download")
        if dl:
            part = CKPT_LOCAL + ".part"
            if os.path.exists(part) and os.path.getsize(part) == sz:
                lhash = sh(["powershell", "-c", f"(Get-FileHash '{part}' -Algorithm SHA256).Hash"], timeout=180)
                rhash = sh(SSH_BOX + [f"sha256sum {RUN_DIR}/ckpt_best.pt"], timeout=180)
                if lhash.strip().splitlines()[0].lower() in rhash.lower():
                    os.replace(part, CKPT_LOCAL)
                    st["ckpt_mtime"] = mt
                    restart_note += f" CKPT_GESYNCT@{dl['milestone']}"
                else:
                    os.remove(part)
                    restart_note += " CKPT_HASH_MISMATCH"
                st["download"] = None
            elif os.path.exists(part) and (now - os.path.getmtime(part)) > 600:
                os.remove(part); st["download"] = None  # vastgelopen download
        if not st.get("download") and mt > st["ckpt_mtime"] and cur_it >= 1000:
            ps = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-c",
                " ".join(SCP_BOX) + f" root@ssh8.vast.ai:{RUN_DIR}/ckpt_best.pt '{CKPT_LOCAL}.part'"],
                creationflags=0x00000008 | 0x00000200)
            st["download"] = {"pid": ps.pid, "size": sz, "milestone": milestone, "started": now}

    status = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "state": state, "iter": cur_it, "max_iters": MAX_ITERS,
        "tokens_seen": cur_it * TOK_PER_ITER, "pct": round(100 * cur_it / MAX_ITERS, 1),
        "tok_s": round(tok_s), "eta_hours": round(eta_h, 1),
        "cost_usd": round(st["runtime_s"] / 3600 * BURN, 2),
        "val_now": val_now, "val_best": val_best, "history": hist,
        "gpu": gpus, "samples": st["samples"], "restarts": st["restarts"],
        "model": {"name": "stay4s-lm-003-xl", "params": 1528400000},
    }
    os.makedirs(os.path.dirname(STATUS_F), exist_ok=True)
    json.dump(status, open(STATUS_F, "w", encoding="utf-8"))
    up = sh(SCP_PI + [STATUS_F, PI_DEST], timeout=60)
    pub = "OK" if "__ERR__" not in up else "MISLUKT"
    save_state(st)
    print(f"F7WATCH iter={cur_it}/{MAX_ITERS} val={val_now} best={val_best} state={state} "
          f"tok/s={round(tok_s)} eta={round(eta_h,1)}h cost=${status['cost_usd']} pub={pub}.{restart_note}")

    # multi-box: Titaan + dicht meenemen (best effort, faalt nooit de xl-tick)
    try:
        import runs_watch
        runs_watch.main()
    except Exception as e:
        print(f"RUNSWATCH overgeslagen: {e}")

if __name__ == "__main__":
    main()
