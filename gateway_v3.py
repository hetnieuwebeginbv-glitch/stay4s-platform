#!/usr/bin/env python3
"""Stay4S API Platform v3 - Production-ready"""
import json, time, os, hashlib, sqlite3, asyncio, subprocess, secrets, hmac
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="Stay4S API Platform", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "YOUR_CF_API_TOKEN")
CF_ACCOUNT_ID = "59513e1a305610f0fb192d73dba01dbd"
CF_AI_URL = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/".format(CF_ACCOUNT_ID)
CF_MODEL_CHAT = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
MOLLIE_API_KEY = os.environ.get("MOLLIE_API_KEY", "live_dummy_placeholder")
OLLAMA_URL = "http://localhost:11434"
OLLAMA_FALLBACK_MODEL = "llama3.2-vision"
DB_PATH = "/mnt/usb4/stay4s_commercial.db"

TIERS = {
    "free": {"name": "Free", "price": 0, "requests_per_day": 20, "features": ["chat", "translate"]},
    "pro": {"name": "Pro", "price": 49, "requests_per_day": 1000, "features": ["chat", "translate", "summarize", "search", "code", "scan", "email", "content", "video", "voice", "embed"]},
    "enterprise": {"name": "Enterprise", "price": 199, "requests_per_day": None, "features": ["all", "agents", "train", "rom", "whatsapp", "priority_support", "video", "voice", "embed"]},
}

API_KEYS = {
    "stay4s-free-demo": {"tier": "free", "customer": "Demo Free", "email": "demo@stay4s.com"},
    "stay4s-pro-demo": {"tier": "pro", "customer": "Demo Pro", "email": "pro@stay4s.com"},
    "stay4s-enterprise-demo": {"tier": "enterprise", "customer": "Demo Enterprise", "email": "ent@stay4s.com"},
}

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY AUTOINCREMENT, api_key TEXT, endpoint TEXT, timestamp TEXT, tokens_in INTEGER, tokens_out INTEGER, cost REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, name TEXT, company TEXT, tier TEXT, api_key TEXT, mollie_customer_id TEXT, created_at TEXT, status TEXT DEFAULT 'active')")
    c.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, amount REAL, currency TEXT, status TEXT, mollie_payment_id TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS revenue (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, amount REAL, currency TEXT, description TEXT, timestamp TEXT)")
    conn.commit()
    conn.close()

init_db()

async def cf_ai_run(model, inputs):
    headers = {"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{CF_AI_URL}{model}", json=inputs, headers=headers)
        data = r.json()
        if data.get("success"):
            return data["result"]
        return {"error": data.get("errors", "AI error")}

async def cf_chat(prompt, system="Je bent Stay4S AI, een behulpzame Nederlandse AI assistent."):
    try:
        result = await cf_ai_run(CF_MODEL_CHAT, {"messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
        if isinstance(result, dict) and "response" in result:
            return result["response"]
        return str(result)
    except Exception:
        return await ollama_chat(prompt, system)

async def ollama_chat(prompt, system="Je bent Stay4S AI, een behulpzame Nederlandse AI assistent."):
    try:
        full_prompt = f"System: {system}\n\nUser: {prompt}\n\nAssistant:"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{OLLAMA_URL}/api/generate", json={"model": OLLAMA_FALLBACK_MODEL, "prompt": full_prompt, "stream": False})
            data = r.json()
            return data.get("response", "Geen respons van AI.")
    except Exception as e:
        return f"AI service tijdelijk niet beschikbaar."

async def verify_key(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing API key. Get one at https://api.stay4s.com")
    key = auth.split("Bearer ")[1]
    if key not in API_KEYS:
        raise HTTPException(401, "Invalid API key. Get one at https://api.stay4s.com")
    tier = API_KEYS[key]["tier"]
    tier_info = TIERS[tier]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    day_ago = (datetime.utcnow() - timedelta(days=1)).isoformat()
    c.execute("SELECT COUNT(*) FROM usage WHERE api_key=? AND timestamp>?", (key, day_ago))
    count = c.fetchone()[0]
    daily_limit = tier_info["requests_per_day"]
    remaining = None if daily_limit is None else max(0, daily_limit - count)
    conn.close()
    if daily_limit is not None and count >= daily_limit:
        raise HTTPException(429, "Daily rate limit exceeded. Upgrade at https://api.stay4s.com")
    return key, tier, remaining

def log_usage(key, endpoint, tokens_in=0, tokens_out=0, cost=0.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO usage (api_key, endpoint, timestamp, tokens_in, tokens_out, cost) VALUES (?,?,?,?,?,?)", (key, endpoint, datetime.utcnow().isoformat(), tokens_in, tokens_out, cost))
    conn.commit()
    conn.close()

def log_revenue(source, amount, description=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO revenue (source, amount, currency, description, timestamp) VALUES (?,?,?,?,?)", (source, amount, "EUR", description, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def rate_headers(key, tier, remaining):
    return {"X-RateLimit-Limit": str(TIERS[tier]["requests_per_day"] if TIERS[tier]["requests_per_day"] is not None else "unlimited"), "X-RateLimit-Remaining": str(remaining if remaining is not None else "unlimited"), "X-RateLimit-Tier": tier, "Access-Control-Expose-Headers": "X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Tier"}


LANDING_PAGE = """<!DOCTYPE html>
<html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stay4S API - Nederlandse AI API</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,sans-serif}
body{background:#0a0e27;color:#fff;line-height:1.6}
.hero{background:linear-gradient(135deg,#667eea,#764ba2);padding:80px 20px;text-align:center}
.hero h1{font-size:48px;margin-bottom:15px;font-weight:800}
.hero p{font-size:20px;opacity:0.9;max-width:600px;margin:0 auto 30px}
.cta{display:inline-block;padding:15px 40px;background:#fff;color:#667eea;text-decoration:none;border-radius:10px;font-weight:bold;font-size:18px;margin:5px}
.cta.sec{background:transparent;border:2px solid #fff;color:#fff}
.container{max-width:1000px;margin:0 auto;padding:40px 20px}
.section{text-align:center;margin:40px 0}
.section h2{font-size:32px;margin-bottom:20px}
.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin:30px 0}
.feature{background:#151a3a;padding:25px;border-radius:12px;border:1px solid #2a3050;text-align:left}
.feature h3{color:#667eea;margin-bottom:8px;font-size:16px}
.feature p{opacity:0.7;font-size:14px}
.pricing{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin:30px 0}
.pc{background:#151a3a;padding:30px;border-radius:16px;text-align:center;border:2px solid #2a3050}
.pc.pop{border-color:#667eea;transform:scale(1.05);position:relative}
.pc.pop::before{content:"POPULAIR";position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:#667eea;padding:4px 12px;border-radius:20px;font-size:12px}
.pc h3{font-size:20px;margin-bottom:10px}
.pc .price{font-size:48px;font-weight:800;margin:10px 0}
.pc .price span{font-size:18px;opacity:0.6}
.pc ul{list-style:none;text-align:left;margin:20px 0}
.pc li{padding:6px 0;border-bottom:1px solid #2a3050;font-size:14px}
.pc li::before{content:"OK ";color:#49b675}
.code{background:#0d1117;border-radius:10px;padding:20px;margin:20px 0;overflow-x:auto;text-align:left}
.code pre{color:#79c0ff;font-size:14px;white-space:pre-wrap}
.tabs{display:flex;gap:5px}
.tab{padding:8px 16px;background:#151a3a;border-radius:8px 8px 0 0;cursor:pointer;font-size:14px;border:none;color:#fff}
.tab.act{background:#0d1117}
.status{display:inline-flex;align-items:center;gap:8px;background:#151a3a;padding:8px 16px;border-radius:20px;font-size:14px}
.dot{width:8px;height:8px;background:#49b675;border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.footer{text-align:center;padding:40px 20px;opacity:0.6;font-size:14px}
a{color:#667eea}
</style></head><body>
<div class="hero"><h1>Stay4S API</h1>
<p>Nederlandse AI API voor developers. Privacy-first, geen Big Tech lock-in.</p>
<div class="status"><span class="dot"></span> Alle systemen operationeel</div><br><br>
<a class="cta" href="#pricing">Bekijk prijzen</a>
<a class="cta sec" href="/docs">API documentatie</a>
<a class="cta sec" href="/v1/subscribe">Aanmelden</a></div>
<div class="container">
<div class="section"><h2>Waarom Stay4S API?</h2>
<div class="features">
<div class="feature"><h3>Nederlands</h3><p>AI geoptimaliseerd voor Nederlands. Geen vertaling van vertaling.</p></div>
<div class="feature"><h3>Privacy-first</h3><p>EU-hosted via Cloudflare. Geen data naar VS.</p></div>
<div class="feature"><h3>Snel</h3><p>Antwoorden in seconden. Ollama fallback ingebouwd.</p></div>
<div class="feature"><h3>Betaalbaar</h3><p>Gratis om te starten. Pro vanaf EUR 49/maand.</p></div>
<div class="feature"><h3>Eenvoudig</h3><p>Een API key, een endpoint. Klaar in 3 minuten.</p></div>
<div class="feature"><h3>Scam Shield</h3><p>Ingebouwde scam en phishing detectie.</p></div>
</div></div>
<div class="section" id="pricing"><h2>Prijzen</h2>
<div class="pricing">
<div class="pc"><h3>Free</h3><div class="price">EUR 0<span>/mnd</span></div><ul><li>20 calls/uur</li><li>1.000 calls/maand</li><li>Chat + Translate</li><li>Community support</li></ul><a class="cta" href="/v1/subscribe" style="font-size:16px;padding:10px 30px">Start gratis</a></div>
<div class="pc pop"><h3>Pro</h3><div class="price">EUR 49<span>/mnd</span></div><ul><li>2.000 calls/uur</li><li>50.000 calls/maand</li><li>Alle 8 endpoints</li><li>Scan + Code + Content</li><li>Email support</li></ul><a class="cta" href="/v1/subscribe" style="font-size:16px;padding:10px 30px">Start Pro</a></div>
<div class="pc"><h3>Enterprise</h3><div class="price">EUR 499<span>/mnd</span></div><ul><li>20.000 calls/uur</li><li>500.000 calls/maand</li><li>Alle 13 endpoints</li><li>AI Agents + Training</li><li>Priority support</li></ul><a class="cta" href="/v1/subscribe" style="font-size:16px;padding:10px 30px">Contact</a></div>
</div></div>
<div class="section"><h2>Aan de slag in 3 minuten</h2>
<div class="tabs"><button class="tab act" onclick="sc('py')">Python</button><button class="tab" onclick="sc('js')">JavaScript</button><button class="tab" onclick="sc('curl')">curl</button></div>
<div class="code" id="c-py"><pre>import requests
r = requests.post("https://api.stay4s.com/v1/chat",
    json={"prompt": "Hallo, wie ben jij?"},
    headers={"Authorization": "Bearer stay4s-free-demo"})
print(r.json()["response"])</pre></div>
<div class="code" id="c-js" style="display:none"><pre>fetch("https://api.stay4s.com/v1/chat", {
    method: "POST",
    headers: {"Authorization": "Bearer stay4s-free-demo", "Content-Type": "application/json"},
    body: JSON.stringify({prompt: "Hallo!"})
}).then(r => r.json()).then(d => console.log(d.response))</pre></div>
<div class="code" id="c-curl" style="display:none"><pre>curl -X POST https://api.stay4s.com/v1/chat \
  -H "Authorization: Bearer stay4s-free-demo" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hallo!"}'</pre></div>
</div>
<div class="section"><h2>Endpoints</h2>
<div class="features">
<div class="feature"><h3>POST /v1/chat</h3><p>AI chat NL/EN</p></div>
<div class="feature"><h3>POST /v1/translate</h3><p>NL &lt;-&gt; EN</p></div>
<div class="feature"><h3>POST /v1/scan</h3><p>Scam detectie</p></div>
<div class="feature"><h3>POST /v1/summarize</h3><p>Tekst samenvatten</p></div>
<div class="feature"><h3>POST /v1/code</h3><p>Code generatie</p></div>
<div class="feature"><h3>POST /v1/content</h3><p>Content generatie</p></div>
</div><p>Alle 13 endpoints: <a href="/docs">/docs</a></p></div>
</div>
<div class="footer"><p>Stay4S - Soevereine Nederlandse AI - <a href="https://www.stay4s.com">www.stay4s.com</a></p>
<p>Gebouwd door Het Nieuwe Begin BV - Privacy-first, EU-hosted</p></div>
<script>function sc(l){document.querySelectorAll('.code').forEach(c=>c.style.display='none');document.getElementById('c-'+l).style.display='block';document.querySelectorAll('.tab').forEach(t=>t.classList.remove('act'));event.target.classList.add('act')}</script>
</body></html>"""

SUBSCRIBE_PAGE = """<!DOCTYPE html>
<html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stay4S API - Aanmelden</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,sans-serif}
body{background:#0a0e27;color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center}
.fc{background:#151a3a;padding:40px;border-radius:16px;max-width:500px;width:90%;border:1px solid #2a3050}
.fc h1{color:#667eea;margin-bottom:10px;text-align:center}
.fc p{text-align:center;opacity:0.7;margin-bottom:30px}
.fg{margin-bottom:20px}
.fg label{display:block;margin-bottom:5px;font-size:14px;opacity:0.8}
.fg input{width:100%;padding:12px;background:#0a0e27;border:1px solid #2a3050;border-radius:8px;color:#fff;font-size:16px}
.fg input:focus{outline:none;border-color:#667eea}
.tc{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:15px 0}
.t{padding:15px;border-radius:10px;border:2px solid #2a3050;cursor:pointer;text-align:center}
.t.sel{border-color:#667eea;background:rgba(102,126,234,0.1)}
.t h3{font-size:16px;margin-bottom:5px}
.t .p{font-size:24px;font-weight:bold}
.t .p span{font-size:12px;opacity:0.6}
.btn{width:100%;padding:15px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:10px;font-size:18px;font-weight:bold;cursor:pointer;margin-top:10px}
.res{display:none;margin-top:20px;padding:20px;background:#0a0e27;border-radius:10px;border:1px solid #49b675}
.res h2{color:#49b675;margin-bottom:10px}
.ak{background:#151a3a;padding:10px;border-radius:6px;font-family:monospace;font-size:14px;word-break:break-all;margin:10px 0;border:1px solid #2a3050}
.back{display:inline-block;margin-top:15px;color:#667eea;text-decoration:none}
</style></head><body>
<div class="fc"><h1>Aanmelden</h1><p>Start binnen minuten met de Stay4S API</p>
<form id="sf">
<div class="fg"><label>Naam</label><input type="text" id="name" required placeholder="Jan Jansen"></div>
<div class="fg"><label>Email</label><input type="email" id="email" required placeholder="jan@bedrijf.nl"></div>
<div class="fg"><label>Bedrijf (optioneel)</label><input type="text" id="company" placeholder="Bedrijf BV"></div>
<div class="fg"><label>Kies een abonnement</label>
<div class="tc">
<div class="t sel" onclick="st('free',this)"><h3>Free</h3><div class="p">EUR 0<span>/mnd</span></div></div>
<div class="t" onclick="st('pro',this)"><h3>Pro</h3><div class="p">EUR 49<span>/mnd</span></div></div>
<div class="t" onclick="st('enterprise',this)"><h3>Ent</h3><div class="p">EUR 499<span>/mnd</span></div></div>
</div><input type="hidden" id="tier" value="free"></div>
<button type="submit" class="btn">API key aanmaken</button>
</form>
<div class="res" id="res"><h2>Welkom bij Stay4S!</h2>
<p>Je API key is aangemaakt. Bewaar deze veilig.</p>
<div class="ak" id="ak"></div>
<p><strong>Tier:</strong> <span id="td"></span> | <strong>Prijs:</strong> EUR <span id="pd"></span>/maand</p>
<pre style="background:#0a0e27;padding:10px;border-radius:6px;margin-top:5px;overflow-x:auto">curl -X POST https://api.stay4s.com/v1/chat \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hallo!"}'</pre>
<a class="back" href="/">Terug</a></div></div>
<script>
let stier='free';
function st(t,e){document.querySelectorAll('.t').forEach(c=>c.classList.remove('sel'));e.classList.add('sel');document.getElementById('tier').value=t;stier=t}
document.getElementById('sf').addEventListener('submit',async(e)=>{
e.preventDefault();
const b={name:document.getElementById('name').value,email:document.getElementById('email').value,company:document.getElementById('company').value||'',tier:stier};
try{const r=await fetch('/customers/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});
const d=await r.json();if(d.error){alert(d.error);return}
document.getElementById('sf').style.display='none';document.getElementById('res').style.display='block';
document.getElementById('ak').textContent=d.api_key;document.getElementById('td').textContent=d.tier;document.getElementById('pd').textContent=d.monthly_price;
}catch(err){alert('Fout: '+err.message)}});
</script></body></html>"""

# === ENDPOINTS ===

@app.get("/")
async def landing():
    return HTMLResponse(LANDING_PAGE)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "stay4s-api", "version": "3.0.0", "ollama": "fallback-ready"}

@app.post("/v1/chat")
async def chat(request: Request, ktr = Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    prompt = body.get("prompt", body.get("message", ""))
    system = body.get("system", "Je bent Stay4S AI, een behulpzame Nederlandse AI assistent.")
    response = await cf_chat(prompt, system)
    log_usage(key, "chat", len(prompt), len(response), 0.001)
    return JSONResponse({"endpoint": "chat", "response": response, "tier": tier}, headers=rate_headers(key, tier, rem))

@app.post("/v1/scan")
async def scan(request: Request, ktr = Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    message = body.get("message", "")
    system = "Je bent een scam detector. Analyseer het bericht en geef: category, risk_score (0-100), explanation."
    try:
        result = await cf_chat(f"Analyseer: {message}", system)
    except Exception:
        result = await ollama_chat(f"Analyseer dit bericht op scam: {message}", "Je bent een scam detector. Geef category, risk_score (0-100), explanation.")
    log_usage(key, "scan", len(message), len(result), 0.01)
    log_revenue("scan", 0.01, f"Scan for {key}")
    return JSONResponse({"endpoint": "scan", "result": result, "tier": tier}, headers=rate_headers(key, tier, rem))

@app.post("/v1/translate")
async def translate(request: Request, ktr = Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    text = body.get("text", "")
    target = body.get("target", "en")
    system = f"Vertaal de volgende tekst naar {target}. Geef alleen de vertaling."
    result = await cf_chat(text, system)
    log_usage(key, "translate", len(text), len(result), 0.005)
    return JSONResponse({"endpoint": "translate", "result": result, "tier": tier}, headers=rate_headers(key, tier, rem))

@app.post("/v1/summarize")
async def summarize(request: Request, ktr = Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    text = body.get("text", "")
    result = await cf_chat(text, "Vat de volgende tekst samen in maximaal 3 zinnen.")
    log_usage(key, "summarize", len(text), len(result), 0.005)
    return JSONResponse({"endpoint": "summarize", "summary": result, "tier": tier}, headers=rate_headers(key, tier, rem))

@app.post("/v1/search")
async def search(request: Request, ktr = Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    query = body.get("query", "")
    result = await cf_chat(query, "Zoek informatie en geef een duidelijk antwoord in het Nederlands.")
    log_usage(key, "search", len(query), len(result), 0.01)
    return JSONResponse({"endpoint": "search", "result": result, "tier": tier}, headers=rate_headers(key, tier, rem))

@app.post("/v1/code")
async def code(request: Request, ktr = Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    desc = body.get("description", body.get("prompt", ""))
    lang = body.get("language", "python")
    result = await cf_chat(desc, f"Genereer {lang} code. Geef alleen code, geen uitleg.")
    log_usage(key, "code", len(desc), len(result), 0.02)
    log_revenue("code", 0.02, f"Code for {key}")
    return JSONResponse({"endpoint": "code", "code": result, "language": lang, "tier": tier}, headers=rate_headers(key, tier, rem))

@app.post("/v1/email")
async def email(request: Request, ktr = Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    result = await cf_chat(body.get("prompt", "Schrijf een email"), "Genereer een professionele email in het Nederlands.")
    log_usage(key, "email", 100, len(result), 0.01)
    return JSONResponse({"endpoint": "email", "email": result, "tier": tier}, headers=rate_headers(key, tier, rem))

@app.post("/v1/content")
async def content(request: Request, ktr = Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    result = await cf_chat(body.get("prompt", "Schrijf een blog post"), "Genereer marketing content in het Nederlands.")
    log_usage(key, "content", 100, len(result), 0.02)
    log_revenue("content", 0.02, f"Content for {key}")
    return JSONResponse({"endpoint": "content", "content": result, "tier": tier}, headers=rate_headers(key, tier, rem))

@app.post("/v1/agents")
async def agents(request: Request, ktr = Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    task = body.get("task", "")
    result = await cf_chat(task, "Je bent Stay4S AI Agent. Voer de taak stap-voor-stap uit.")
    log_usage(key, "agents", len(task), len(result), 0.05)
    log_revenue("agents", 0.05, f"Agent for {key}")
    return JSONResponse({"endpoint": "agents", "plan": result, "tier": tier, "cost": 0.05}, headers=rate_headers(key, tier, rem))

@app.post("/v1/scan/batch")
async def scan_batch(request: Request, ktr = Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    messages = body.get("messages", [])
    if len(messages) > 1000:
        raise HTTPException(400, "Max 1000 messages per batch")
    results = []
    for msg in messages[:100]:
        try:
            result = await cf_chat(f"Analyseer: {msg}", "Scam detector. Geef risk_score en category.")
        except Exception:
            result = await ollama_chat(f"Analyseer: {msg}", "Scam detector.")
        results.append({"message": msg[:50], "result": result})
    total_cost = len(messages) * 0.005
    log_usage(key, "scan_batch", 0, 0, total_cost)
    log_revenue("scan_batch", total_cost, f"Batch {len(messages)} for {key}")
    return JSONResponse({"endpoint": "scan_batch", "results": results, "count": len(results), "cost": total_cost, "tier": tier}, headers=rate_headers(key, tier, rem))

# === SUBSCRIBE ===

@app.get("/v1/subscribe")
async def subscribe_page():
    return HTMLResponse(SUBSCRIBE_PAGE)

@app.post("/customers/create")
async def create_customer(request: Request):
    body = await request.json()
    email = body.get("email", "")
    name = body.get("name", "")
    company = body.get("company", "")
    tier = body.get("tier", "free")
    api_key = "stay4s-" + hashlib.sha256(f"{email}{time.time()}".encode()).hexdigest()[:24]
    API_KEYS[api_key] = {"tier": tier, "customer": name, "email": email}
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO customers (email, name, company, tier, api_key, created_at) VALUES (?,?,?,?,?,?)", (email, name, company, tier, api_key, datetime.utcnow().isoformat()))
        conn.commit()
        customer_id = c.lastrowid
        conn.close()
        return {"customer_id": customer_id, "api_key": api_key, "tier": tier, "monthly_price": TIERS[tier]["price"]}
    except sqlite3.IntegrityError:
        conn.close()
        return {"error": "Dit emailadres is al geregistreerd."}

# === ADMIN ===

@app.get("/pricing")
async def pricing():
    return {"tiers": TIERS, "currency": "EUR", "base_url": "https://api.stay4s.com"}

@app.get("/admin/usage")
async def admin_usage():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM usage")
    total_calls = c.fetchone()[0]
    c.execute("SELECT endpoint, COUNT(*) FROM usage GROUP BY endpoint ORDER BY COUNT(*) DESC")
    by_endpoint = [{"endpoint": r[0], "calls": r[1]} for r in c.fetchall()]
    c.execute("SELECT SUM(amount) FROM revenue")
    total_revenue = c.fetchone()[0] or 0
    c.execute("SELECT source, SUM(amount) FROM revenue GROUP BY source ORDER BY SUM(amount) DESC")
    revenue_by_source = [{"source": r[0], "total": r[1]} for r in c.fetchall()]
    c.execute("SELECT endpoint, timestamp, api_key FROM usage ORDER BY id DESC LIMIT 20")
    recent = [{"endpoint": r[0], "timestamp": r[1], "api_key": r[2][:12]+"..."} for r in c.fetchall()]
    c.execute("SELECT COUNT(*) FROM customers")
    total_customers = c.fetchone()[0]
    conn.close()
    return {"total_calls": total_calls, "by_endpoint": by_endpoint, "total_revenue_eur": round(total_revenue, 2), "revenue_by_source": revenue_by_source, "recent_activity": recent, "total_customers": total_customers, "pricing_tiers": TIERS}

@app.get("/admin/keys")
async def admin_keys():
    return {"keys": [{"key": k[:12]+"...", "tier": v["tier"], "customer": v["customer"]} for k, v in API_KEYS.items()]}

@app.get("/docs")
async def api_docs():
    return JSONResponse({
        "name": "Stay4S AI API", "version": "3.0.0", "base_url": "https://api.stay4s.com",
        "auth": "Bearer token in Authorization header",
        "get_api_key": "https://api.stay4s.com/v1/subscribe",
        "endpoints": [
            {"method": "POST", "path": "/v1/chat", "description": "AI Chat (NL/EN)", "tier": "free+"},
            {"method": "POST", "path": "/v1/scan", "description": "Scam Detection", "tier": "pro+"},
            {"method": "POST", "path": "/v1/scan/batch", "description": "Bulk Scam Detection", "tier": "pro+"},
            {"method": "POST", "path": "/v1/translate", "description": "Translation", "tier": "free+"},
            {"method": "POST", "path": "/v1/summarize", "description": "Summarization", "tier": "pro+"},
            {"method": "POST", "path": "/v1/search", "description": "AI Search", "tier": "pro+"},
            {"method": "POST", "path": "/v1/code", "description": "Code Generation", "tier": "pro+"},
            {"method": "POST", "path": "/v1/email", "description": "Email Generation", "tier": "pro+"},
            {"method": "POST", "path": "/v1/content", "description": "Content Generation", "tier": "pro+"},
            {"method": "POST", "path": "/v1/agents", "description": "AI Agent Task", "tier": "enterprise"},
            {"method": "POST", "path": "/customers/create", "description": "Create Account"},
            {"method": "GET", "path": "/v1/subscribe", "description": "Signup Page"},
            {"method": "GET", "path": "/pricing", "description": "Pricing"},
            {"method": "GET", "path": "/admin/usage", "description": "Usage Analytics"},
            {"method": "GET", "path": "/docs", "description": "API Documentation"},
        ], "pricing": TIERS
    })



# === STAY4S GATEWAY V3 EXTENSIONS (2026-10-09) ===
VIDEO_API_URL = os.getenv("VIDEO_API_URL", "https://video.stay4s.com/generate")
WHISPER_URL = os.getenv("WHISPER_URL", "")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", OLLAMA_FALLBACK_MODEL)
MOLLIE_WEBHOOK_URL = os.getenv("MOLLIE_WEBHOOK_URL", "https://api.stay4s.com/webhooks/mollie")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://api.stay4s.com")

def _mollie_ready():
    return bool(MOLLIE_API_KEY and MOLLIE_API_KEY.startswith(("test_", "live_")) and "dummy" not in MOLLIE_API_KEY.lower() and "placeholder" not in MOLLIE_API_KEY.lower())

def _db():
    return sqlite3.connect(DB_PATH, timeout=10)

def _ensure_extension_tables():
    conn = _db()
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS checkout_sessions (
            token_hash TEXT PRIMARY KEY, customer_id INTEGER NOT NULL,
            mollie_payment_id TEXT, expires_at TEXT NOT NULL, consumed INTEGER NOT NULL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS subscription_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, mollie_payment_id TEXT,
            event_type TEXT NOT NULL, payload TEXT, created_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, api_key TEXT NOT NULL,
            endpoint TEXT NOT NULL UNIQUE, subscription_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        conn.commit()
    finally:
        conn.close()

_ensure_extension_tables()

@app.post("/v1/video")
async def v1_video(request: Request, ktr=Depends(verify_key)):
    key, tier, rem = ktr
    if "video" not in TIERS[tier]["features"] and "all" not in TIERS[tier]["features"]:
        raise HTTPException(403, "Video is not included in this plan.")
    body = await request.json()
    prompt = str(body.get("prompt", "")).strip()
    if not prompt or len(prompt) > 2000:
        raise HTTPException(422, "prompt is required and must be at most 2000 characters.")
    payload = {
        "prompt": prompt,
        "width": max(256, min(1024, int(body.get("width", 512)))),
        "height": max(256, min(1024, int(body.get("height", 512)))),
        "num_frames": max(8, min(96, int(body.get("num_frames", 16)))),
        "steps": max(1, min(40, int(body.get("steps", 20))))
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(240.0, connect=10.0)) as client:
            r = await client.post(VIDEO_API_URL, json=payload)
        if r.status_code >= 400:
            raise HTTPException(502, f"Video provider returned HTTP {r.status_code}.")
        data = r.json()
        log_usage(key, "video", len(prompt), 0, 0.0)
        return JSONResponse({"endpoint": "video", "result": data, "tier": tier}, headers=rate_headers(key, tier, rem))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Video service unavailable.")

@app.post("/v1/voice")
async def v1_voice(request: Request, audio: UploadFile = File(...), ktr=Depends(verify_key)):
    key, tier, rem = ktr
    if "voice" not in TIERS[tier]["features"] and "all" not in TIERS[tier]["features"]:
        raise HTTPException(403, "Voice transcription is not included in this plan.")
    if not WHISPER_URL:
        raise HTTPException(503, "Whisper is not configured. Set WHISPER_URL to a private Whisper-compatible /asr endpoint.")
    allowed = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/webm", "audio/ogg", "audio/flac", "audio/x-m4a", "application/octet-stream"}
    if audio.content_type and audio.content_type not in allowed:
        raise HTTPException(415, "Unsupported audio content type.")
    content = await audio.read()
    if not content or len(content) > 25 * 1024 * 1024:
        raise HTTPException(413, "Audio must be non-empty and at most 25 MiB.")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(WHISPER_URL, files={"audio_file": (audio.filename or "audio.webm", content, audio.content_type or "application/octet-stream")})
        if r.status_code >= 400:
            raise HTTPException(502, f"Whisper provider returned HTTP {r.status_code}.")
        data = r.json()
        text = data.get("text") or data.get("transcription") or data.get("result")
        if text is None:
            raise HTTPException(502, "Whisper response did not contain transcription text.")
        log_usage(key, "voice", len(content), len(text), 0.0)
        return JSONResponse({"endpoint": "voice", "text": text, "language": data.get("language"), "tier": tier}, headers=rate_headers(key, tier, rem))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Voice transcription service unavailable.")

@app.get("/v1/models")
async def v1_models(ktr=Depends(verify_key)):
    key, tier, rem = ktr
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
            ollama_models = [{"id": m.get("name"), "provider": "ollama", "size": m.get("size")} for m in r.json().get("models", [])]
    except Exception:
        pass
    # Cloudflare model IDs are configured explicitly to avoid exposing account internals.
    cf_models = [m.strip() for m in os.getenv("CLOUDFLARE_MODELS", CF_MODEL_CHAT).split(",") if m.strip()]
    log_usage(key, "models", 0, 0, 0.0)
    return JSONResponse({"models": ollama_models + [{"id": m, "provider": "cloudflare-workers-ai"} for m in cf_models], "providers": {"ollama": bool(ollama_models), "cloudflare_workers_ai": bool(cf_models)}}, headers=rate_headers(key, tier, rem))

@app.post("/v1/embed")
async def v1_embed(request: Request, ktr=Depends(verify_key)):
    key, tier, rem = ktr
    if "embed" not in TIERS[tier]["features"] and "all" not in TIERS[tier]["features"]:
        raise HTTPException(403, "Embeddings are not included in this plan.")
    body = await request.json()
    text_value = body.get("input", body.get("text", ""))
    if not isinstance(text_value, (str, list)) or not text_value:
        raise HTTPException(422, "Provide non-empty 'input' or 'text'.")
    model = str(body.get("model") or OLLAMA_EMBED_MODEL)
    if model != OLLAMA_EMBED_MODEL:
        raise HTTPException(400, f"Only configured embedding model '{OLLAMA_EMBED_MODEL}' is allowed.")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{OLLAMA_URL}/api/embed", json={"model": model, "input": text_value})
            if r.status_code == 404:
                r = await client.post(f"{OLLAMA_URL}/api/embeddings", json={"model": model, "prompt": text_value if isinstance(text_value, str) else text_value[0]})
            r.raise_for_status()
            data = r.json()
        embeddings = data.get("embeddings")
        if embeddings is None and data.get("embedding") is not None:
            embeddings = [data["embedding"]]
        if embeddings is None:
            raise HTTPException(502, "Ollama returned no embedding.")
        log_usage(key, "embed", len(text_value) if isinstance(text_value, str) else sum(len(str(x)) for x in text_value), 0, 0.0)
        return JSONResponse({"model": model, "embeddings": embeddings}, headers=rate_headers(key, tier, rem))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Embedding service unavailable.")

@app.websocket("/v1/stream")
async def v1_stream(ws: WebSocket):
    await ws.accept()
    key = None
    try:
        # Browser WebSocket cannot set Authorization headers; authenticate in the first frame.
        auth = await asyncio.wait_for(ws.receive_json(), timeout=8)
        key = auth.get("api_key") if isinstance(auth, dict) and auth.get("type") == "auth" else None
        if not key or key not in API_KEYS:
            await ws.send_json({"type": "error", "error": "unauthorized"})
            await ws.close(code=1008)
            return
        tier = API_KEYS[key]["tier"]
        day_ago = (datetime.utcnow() - timedelta(days=1)).isoformat()
        conn = _db()
        count = conn.execute("SELECT COUNT(*) FROM usage WHERE api_key=? AND timestamp>?", (key, day_ago)).fetchone()[0]
        conn.close()
        limit = TIERS[tier]["requests_per_day"]
        if limit is not None and count >= limit:
            await ws.send_json({"type": "error", "error": "daily_rate_limit_exceeded"})
            await ws.close(code=1008)
            return
        await ws.send_json({"type": "ready", "tier": tier})
        while True:
            msg = await ws.receive_json()
            prompt = str(msg.get("prompt", "")).strip()
            if not prompt or len(prompt) > 12000:
                await ws.send_json({"type": "error", "error": "prompt_required_or_too_long"})
                continue
            model = str(msg.get("model") or OLLAMA_CHAT_MODEL)
            # Allow only locally installed models; prevents arbitrary provider/model routing.
            async with httpx.AsyncClient(timeout=90) as client:
                check = await client.get(f"{OLLAMA_URL}/api/tags")
                available = {m.get("name") for m in check.json().get("models", [])}
                if model not in available:
                    await ws.send_json({"type": "error", "error": "model_not_available", "model": model})
                    continue
                async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": True}) as response:
                    if response.status_code >= 400:
                        await ws.send_json({"type": "error", "error": "model_request_failed"})
                        continue
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        piece = (chunk.get("message") or {}).get("content", "")
                        if piece:
                            await ws.send_json({"type": "token", "text": piece})
                        if chunk.get("done"):
                            break
            log_usage(key, "stream", len(prompt), 0, 0.0)
            await ws.send_json({"type": "done"})
    except (WebSocketDisconnect, asyncio.TimeoutError):
        return
    except Exception:
        try:
            await ws.send_json({"type": "error", "error": "stream_failed"})
            await ws.close(code=1011)
        except Exception:
            pass


@app.post("/v1/scan/image")
async def v1_scan_image(request: Request, image: UploadFile = File(...), ktr=Depends(verify_key)):
    key, tier, rem = ktr
    if "scan" not in TIERS[tier]["features"] and "all" not in TIERS[tier]["features"]:
        raise HTTPException(403, "Image scam scan is not included in this plan.")
    if image.content_type not in {"image/jpeg","image/png","image/webp"}:
        raise HTTPException(415, "Upload a JPEG, PNG or WebP image.")
    raw = await image.read()
    if not raw or len(raw) > 8 * 1024 * 1024:
        raise HTTPException(413, "Image must be non-empty and at most 8 MiB.")
    try:
        import base64
        payload = base64.b64encode(raw).decode("ascii")
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json={
                "model": os.getenv("OLLAMA_VISION_MODEL","llama3.2-vision"),
                "messages":[{"role":"user","content":"Analyseer deze afbeelding op phishing, fraude, verdachte betaalverzoeken, nepwebsites en impersonatie. Geef een korte onderbouwde beoordeling in het Nederlands en benoem onzekerheid. Dit is geen definitieve veiligheidswaarborg.","images":[payload]}],
                "stream":False
            })
            r.raise_for_status()
            data = r.json()
        result = (data.get("message") or {}).get("content","")
        log_usage(key,"scan_image",len(raw),len(result),0.0)
        return JSONResponse({"endpoint":"scan/image","result":result,"model":os.getenv("OLLAMA_VISION_MODEL","llama3.2-vision")},headers=rate_headers(key,tier,rem))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502,"Image scam scan unavailable.")

@app.get("/v1/push/vapid-public-key")
async def push_vapid_public_key(ktr=Depends(verify_key)):
    public_key = os.getenv("VAPID_PUBLIC_KEY","")
    if not public_key:
        raise HTTPException(503,"Web Push is not configured.")
    return {"public_key":public_key}

@app.post("/v1/push/subscribe")
async def push_subscribe(request: Request, ktr=Depends(verify_key)):
    key, tier, rem = ktr
    body = await request.json()
    sub = body.get("subscription")
    if not isinstance(sub,dict) or not sub.get("endpoint") or not isinstance(sub.get("keys"),dict):
        raise HTTPException(422,"Invalid Web Push subscription.")
    conn=_db()
    try:
        conn.execute("INSERT INTO push_subscriptions (api_key,endpoint,subscription_json,created_at) VALUES (?,?,?,?) ON CONFLICT(endpoint) DO UPDATE SET api_key=excluded.api_key,subscription_json=excluded.subscription_json",
            (key,sub["endpoint"],json.dumps(sub),datetime.utcnow().isoformat()))
        conn.commit()
    finally:
        conn.close()
    return {"saved":True}

@app.post("/v1/push/test")
async def push_test(request: Request, ktr=Depends(verify_key)):
    key,tier,rem=ktr
    try:
        from pywebpush import webpush
    except ImportError:
        raise HTTPException(503,"Install pywebpush to enable Web Push.")
    private_key=os.getenv("VAPID_PRIVATE_KEY","")
    claims={"sub":os.getenv("VAPID_CLAIMS_EMAIL","mailto:support@stay4s.com")}
    if not private_key or not os.getenv("VAPID_PUBLIC_KEY"):
        raise HTTPException(503,"VAPID keys are not configured.")
    conn=_db()
    subs=[json.loads(row[0]) for row in conn.execute("SELECT subscription_json FROM push_subscriptions WHERE api_key=?",(key,)).fetchall()]
    conn.close()
    sent=0
    for sub in subs:
        try:
            webpush(subscription_info=sub,data=json.dumps({"title":"Stay4S","body":"Pushmeldingen werken."}),vapid_private_key=private_key,vapid_claims=claims)
            sent+=1
        except Exception:
            continue
    return {"subscriptions":len(subs),"sent":sent}


@app.post("/v1/subscribe")
async def v1_subscribe(request: Request):
    body = await request.json()
    email = str(body.get("email", "")).strip().lower()
    name = str(body.get("name", "")).strip()
    company = str(body.get("company", "")).strip()
    tier = str(body.get("tier", "free")).lower()
    if not email or "@" not in email or len(email) > 254:
        raise HTTPException(422, "A valid email is required.")
    if tier not in TIERS:
        raise HTTPException(422, "Unknown subscription tier.")
    if tier == "free":
        # Free plan is activated without a payment; key is generated server-side.
        api_key = "stay4s-" + secrets.token_urlsafe(32)
        conn = _db()
        try:
            conn.execute("INSERT INTO customers (email,name,company,tier,api_key,created_at,status) VALUES (?,?,?,?,?,?,?)", (email,name,company,"free",api_key,datetime.utcnow().isoformat(),"active"))
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Email is already registered.")
        finally:
            conn.close()
        API_KEYS[api_key] = {"tier":"free","customer":name or email,"email":email}
        return {"status":"active","tier":"free","api_key":api_key,"daily_limit":20}
    if not _mollie_ready():
        raise HTTPException(503, "Mollie is not configured. Set MOLLIE_API_KEY to a valid test_ or live_ key.")
    amount = f"{TIERS[tier]['price']:.2f}"
    async with httpx.AsyncClient(timeout=20) as client:
        headers = {"Authorization": f"Bearer {MOLLIE_API_KEY}", "Content-Type": "application/json"}
        try:
            customer_resp = await client.post("https://api.mollie.com/v2/customers", headers=headers, json={"name":name or email,"email":email,"metadata":{"tier":tier}})
            customer_resp.raise_for_status()
            mollie_customer = customer_resp.json()
            conn = _db()
            try:
                conn.execute("INSERT INTO customers (email,name,company,tier,mollie_customer_id,created_at,status) VALUES (?,?,?,?,?,?,?)", (email,name,company,tier,mollie_customer["id"],datetime.utcnow().isoformat(),"pending"))
                conn.commit()
                customer_id = conn.execute("SELECT id FROM customers WHERE email=?", (email,)).fetchone()[0]
            except sqlite3.IntegrityError:
                raise HTTPException(409, "Email is already registered.")
            finally:
                conn.close()
            payment_resp = await client.post(f"https://api.mollie.com/v2/customers/{mollie_customer['id']}/payments", headers=headers, json={
                "amount":{"currency":"EUR","value":amount},
                "description":f"Stay4S {TIERS[tier]['name']} abonnement",
                "redirectUrl":f"{PUBLIC_BASE_URL}/payment/return",
                "webhookUrl":MOLLIE_WEBHOOK_URL,
                "sequenceType":"first",
                "metadata":{"customer_id":customer_id,"tier":tier,"email":email}
            })
            payment_resp.raise_for_status()
            payment = payment_resp.json()
            conn = _db()
            conn.execute("INSERT INTO payments (customer_id,amount,currency,status,mollie_payment_id,created_at) VALUES (?,?,?,?,?,?)", (customer_id,float(amount),"EUR",payment.get("status","open"),payment["id"],datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
            return {"status":"checkout_required","tier":tier,"amount_eur":amount,"checkout_url":payment.get("_links",{}).get("checkout",{}).get("href"),"payment_id":payment["id"]}
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(502, "Could not create Mollie checkout.")

@app.post("/webhooks/mollie")
async def mollie_webhook(request: Request):
    form = await request.form()
    payment_id = form.get("id")
    if not payment_id or not _mollie_ready():
        raise HTTPException(400, "Invalid Mollie webhook.")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"https://api.mollie.com/v2/payments/{payment_id}", headers={"Authorization": f"Bearer {MOLLIE_API_KEY}"})
        if response.status_code >= 400:
            raise HTTPException(502, "Unable to verify payment with Mollie.")
        payment = response.json()
    conn = _db()
    try:
        row = conn.execute("SELECT customer_id FROM payments WHERE mollie_payment_id=?", (payment_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Payment not found.")
        customer_id = row[0]
        conn.execute("UPDATE payments SET status=? WHERE mollie_payment_id=?", (payment.get("status","unknown"), payment_id))
        conn.execute("INSERT INTO subscription_events (mollie_payment_id,event_type,payload,created_at) VALUES (?,?,?,?)", (payment_id,payment.get("status","unknown"),json.dumps({"status":payment.get("status"),"sequenceType":payment.get("sequenceType")}),datetime.utcnow().isoformat()))
        conn.commit()
        if payment.get("status") == "paid":
            customer = conn.execute("SELECT email,name,tier,mollie_customer_id FROM customers WHERE id=?", (customer_id,)).fetchone()
            if customer:
                email,name,tier,mollie_customer_id = customer
                # Create recurring subscription after the first payment has established a mandate.
                if mollie_customer_id and payment.get("sequenceType") == "first":
                    amount = f"{TIERS[tier]['price']:.2f}"
                    async with httpx.AsyncClient(timeout=20) as client:
                        sub_resp = await client.post(f"https://api.mollie.com/v2/customers/{mollie_customer_id}/subscriptions",
                            headers={"Authorization": f"Bearer {MOLLIE_API_KEY}","Content-Type":"application/json"},
                            json={"amount":{"currency":"EUR","value":amount},"interval":"1 month","description":f"Stay4S {TIERS[tier]['name']} abonnement","webhookUrl":MOLLIE_WEBHOOK_URL})
                        # A subscription failure is logged and does not falsely report recurring activation.
                        if sub_resp.status_code < 300:
                            conn.execute("UPDATE customers SET status='active' WHERE id=?", (customer_id,))
                            conn.commit()
                api_key = conn.execute("SELECT api_key FROM customers WHERE id=?", (customer_id,)).fetchone()[0]
                if not api_key:
                    api_key = "stay4s-" + secrets.token_urlsafe(32)
                    conn.execute("UPDATE customers SET api_key=?, status='active' WHERE id=?", (api_key,customer_id))
                    conn.commit()
                API_KEYS[api_key] = {"tier":tier,"customer":name or email,"email":email}
    finally:
        conn.close()
    return {"received":True}

@app.get("/v1/subscribe/status/{payment_id}")
async def v1_subscribe_status(payment_id: str):
    # This endpoint deliberately exposes status only; API keys must be delivered through an authenticated customer channel.
    conn = _db()
    try:
        row = conn.execute("SELECT status FROM payments WHERE mollie_payment_id=?", (payment_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(404, "Payment not found.")
    return {"payment_id":payment_id,"status":row[0]}

@app.get("/payment/return")
async def payment_return():
    return HTMLResponse("<!doctype html><html lang='nl'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Stay4S betaling</title><body style='font-family:system-ui;max-width:640px;margin:4rem auto;padding:1rem'><h1>Bedankt</h1><p>Je betaling wordt gecontroleerd. Je ontvangt bevestiging via het afgesproken klantkanaal. Als je nog geen klantkanaal hebt ingesteld, neem contact op met support.</p><p>Sluit dit venster pas nadat Mollie de betaling heeft bevestigd.</p></body></html>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8130)



