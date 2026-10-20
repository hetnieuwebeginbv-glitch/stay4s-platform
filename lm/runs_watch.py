#!/usr/bin/env python3
"""runs_watch.py - pollt box2 (Titaan) en box3 (dicht), schrijft lab/runs_extra.json.
Wordt aangeroepen aan het einde van f7_watch.py (best effort). Alleen stdlib.
Eigen state-bestand zodat histories/ETA per run bijgehouden worden.
"""
import json, os, re, subprocess, time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_F = os.path.join(ROOT, "f7_state_multi.json")
EXTRA_F = os.path.join(ROOT, "lab", "runs_extra.json")
PI_KEY = r"C:\Users\Gebruiker\.ssh\stay4pi_ed25519"
SCP_PI = ["scp", "-o", "ConnectTimeout=25", "-i", PI_KEY]
PI_DEST = "Miesdevries@192.168.8.120:/var/www/lab/runs_extra.json"

BOXES = [
    {"id": "titaan", "host": "ssh4.vast.ai", "port": 29104,
     "log": "/root/titaan_train.log",
     "name": "Stay4S-Titaan (MoE)", "params": "1,46B totaal / 470M actief",
     "burn": 0.962, "tok_per_iter": 131072, "max_iters": 13000},
    {"id": "dicht", "host": "ssh7.vast.ai", "port": 25940,
     "log": "/root/dicht_train.log",
     "name": "titaan-dicht", "params": "470M dicht",
     "burn": 0.9085, "tok_per_iter": 131072, "max_iters": 13000},
]

ITER_RE = re.compile(r"iter\s+(\d+) \| lr ([\d.e-]+) \| train ([\d.]+) \| val ([\d.]+) \| \s*([\d.]+)s")

def sh(cmd, timeout=90):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except Exception as e:
        return "__ERR__ %s" % e

def load_state():
    if os.path.exists(STATE_F):
        return json.load(open(STATE_F, encoding="utf-8"))
    return {"runs": {}}

def poll_box(box, rstate):
    ssh = ["ssh", "-o", "ConnectTimeout=20", "-o", "StrictHostKeyChecking=no",
           "-p", str(box["port"]), "root@" + box["host"]]
    out = sh(ssh + ["tail -c 100000 %s; echo @@; pgrep -fc train_ddp.py; echo @@; "
                    "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader" % box["log"]])
    if "__ERR__" in out and not re.search(r"iter\s+\d+", out):
        rstate["bereikbaar"] = False
        return
    rstate["bereikbaar"] = True
    parts = out.split("@@")
    log_tail = parts[0]
    try:
        nproc = int((parts[1].strip().splitlines() or ["0"])[-1])
    except Exception:
        nproc = 0
    utils = []
    if len(parts) > 2:
        utils = [int(m.group(1)) for m in re.finditer(r"(\d+)\s*%", parts[2])]

    hist = rstate.setdefault("history", [])
    for it, lr, tr, va, dt in ITER_RE.findall(log_tail):
        it = int(it)
        found = [h for h in hist if h[0] == it]
        if found:
            if len(found[0]) < 4:
                found[0].append(float(dt))
        else:
            hist.append([it, float(tr), float(va), float(dt)])
    hist.sort()
    hist = hist[-400:]
    rstate["history"] = hist
    if not hist:
        return
    cur_it = hist[-1][0]
    val_now = hist[-1][2]
    val_best = min(h[2] for h in hist)
    pts = [(h[0], h[3]) for h in hist if len(h) > 3]
    sp_iter = None
    if len(pts) >= 2:
        (i1, t1), (i2, t2) = pts[0], pts[-1]
        if i2 > i1 and t2 > t1:
            sp_iter = (t2 - t1) / (i2 - i1)
    tok_s = round(box["tok_per_iter"] / sp_iter) if sp_iter else None
    eta_h = round((box["max_iters"] - cur_it) * sp_iter / 3600, 1) if sp_iter else None
    rstate.update({
        "iter": cur_it, "val_now": val_now, "val_best": val_best,
        "tok_s": tok_s, "eta_hours": eta_h,
        "state": "training" if nproc >= 1 else "gestopt",
        "gpu_util": utils,
    })

def main():
    st = load_state()
    runs = []
    for box in BOXES:
        rs = st["runs"].setdefault(box["id"], {})
        poll_box(box, rs)
        if not rs.get("bereikbaar") and "iter" not in rs:
            runs.append({"id": box["id"], "name": box["name"], "params": box["params"],
                         "state": "onbereikbaar", "iter": None, "max_iters": box["max_iters"]})
            continue
        runs.append({
            "id": box["id"], "name": box["name"], "params": box["params"],
            "state": rs.get("state", "onbereikbaar" if not rs.get("bereikbaar") else "onbekend"),
            "iter": rs.get("iter"), "max_iters": box["max_iters"],
            "pct": round(100 * rs["iter"] / box["max_iters"], 1) if rs.get("iter") else None,
            "val_now": rs.get("val_now"), "val_best": rs.get("val_best"),
            "tok_s": rs.get("tok_s"), "eta_hours": rs.get("eta_hours"),
            "gpu_util": rs.get("gpu_util", []),
        })
    payload = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "runs": runs}
    os.makedirs(os.path.dirname(EXTRA_F), exist_ok=True)
    json.dump(payload, open(EXTRA_F, "w", encoding="utf-8"))
    json.dump(st, open(STATE_F, "w", encoding="utf-8"), indent=1)
    up = sh(SCP_PI + [EXTRA_F, PI_DEST], timeout=60)
    samen = " | ".join("%s:%s@%s val=%s" % (r["id"], r["state"], r["iter"], r.get("val_now")) for r in runs)
    print("RUNSWATCH %s pub=%s" % (samen, "OK" if "__ERR__" not in up else "MISLUKT"))

if __name__ == "__main__":
    main()