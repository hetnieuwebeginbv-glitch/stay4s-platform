#!/usr/bin/env python3
"""Stay4S Landing — commerciele homepage (poort 8161). Serveert /opt/stay4s/landing/index.html."""
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

BASE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(BASE, "index.html")
PORT = int(os.environ.get("LANDING_PORT", "8161"))

app = FastAPI(title="Stay4S Landing", docs_url=None, redoc_url=None)

@app.get("/", response_class=None)
def home():
    return FileResponse(INDEX, media_type="text/html")

@app.get("/health")
def health():
    return {"status": "ok", "service": "stay4s-landing"}

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nAllow: /\n"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
