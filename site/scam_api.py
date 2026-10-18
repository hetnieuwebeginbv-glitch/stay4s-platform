#!/usr/bin/env python3
"""Stay4S Scam-Check API — scam.stay4s.com (poort 8100)
Draait de v2 DistilBERT-classifier op CPU. Onafhankelijk van /mnt/usb4.
Start: python3 /opt/stay4s/scam/scam_api.py
Vereist: transformers==4.46.3, torch (CPU), fastapi, uvicorn
"""
import os, time, threading, collections
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

MODEL_DIR = os.environ.get("SCAM_MODEL_DIR", "/opt/stay4s/models/scam-v2")
SITE_HTML = os.environ.get("SCAM_SITE_HTML", "/opt/stay4s/scam/scam.html")
PORT = int(os.environ.get("SCAM_PORT", "8100"))
MAX_LEN = 4000
RATE_LIMIT = 30          # checks per IP per uur
_rate = collections.defaultdict(list)
_lock = threading.Lock()
_pipe = None

app = FastAPI(title="Stay4S Scam-Check", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=[
    "https://stay4s.com", "https://www.stay4s.com", "https://scam.stay4s.com",
], allow_methods=["POST", "GET"], allow_headers=["*"])

class CheckIn(BaseModel):
    text: str = Field(min_length=10, max_length=MAX_LEN)

def get_pipe():
    global _pipe
    if _pipe is None:
        from transformers import pipeline
        _pipe = pipeline("text-classification", model=MODEL_DIR, tokenizer=MODEL_DIR,
                         device=-1, truncation=True, max_length=512)
    return _pipe

def toegestaan(ip: str) -> bool:
    nu = time.time()
    with _lock:
        hits = [t for t in _rate[ip] if nu - t < 3600]
        if len(hits) >= RATE_LIMIT:
            _rate[ip] = hits
            return False
        hits.append(nu)
        _rate[ip] = hits
        return True

@app.get("/")
def index():
    if os.path.exists(SITE_HTML):
        return FileResponse(SITE_HTML)
    return JSONResponse({"service": "stay4s-scam-check", "status": "ok"})

@app.get("/health")
def health():
    return {"status": "ok", "model_geladen": _pipe is not None, "model_dir": MODEL_DIR}

@app.post("/check")
def check(inp: CheckIn, req: Request):
    ip = req.client.host if req.client else "onbekend"
    if not toegestaan(ip):
        return JSONResponse({"error": "Te veel verzoeken, probeer het later opnieuw."}, status_code=429)
    try:
        uit = get_pipe()(inp.text)[0]
    except Exception as e:
        return JSONResponse({"error": f"analyse mislukt: {e}"}, status_code=500)
    label = str(uit.get("label", "")).lower()
    score = float(uit.get("score", 0.0))
    # Normaliseer naar: score = kans op scam (0..1)
    scam_labels = {"scam", "label_1", "1", "positive", "spam"}
    p_scam = score if label in scam_labels else (1.0 - score)
    if p_scam >= 0.95:   # v2: duidelijke scams scoren 0.999+; 0.8-0.95 = twijfelzone (FP koffie-test 18-10)
        verdict = "scam"
    elif p_scam >= 0.55:
        verdict = "verdacht"
    else:
        verdict = "ok"
    return {"verdict": verdict, "score": round(p_scam, 4), "label": label,
            "raw_score": round(score, 4), "model": "stay4s-scam-v2", "ms": None}

if __name__ == "__main__":
    import uvicorn
    # Model alvast laden bij opstarten (warm start)
    try:
        get_pipe()
        print(f"[scam-api] model geladen uit {MODEL_DIR}")
    except Exception as e:
        print(f"[scam-api] WAARSCHUWING: model nog niet geladen: {e}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

