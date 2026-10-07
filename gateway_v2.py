#!/usr/bin/env python3
"""
Stay4S Commercial Gateway v2 - Full commercial platform
Features: Mollie payments, pricing tiers, usage analytics, 5 new revenue endpoints
"""
import json, time, os, hashlib, sqlite3, asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="Stay4S Commercial Gateway", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# === Configuration ===
CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "YOUR_CF_API_TOKEN")
CF_ACCOUNT_ID = "59513e1a305610f0fb192d73dba01dbd"
CF_AI_URL = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/".format(CF_ACCOUNT_ID)
CF_MODEL_CHAT = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
CF_MODEL_TRANSLATE = "@cf/meta/m2m100"
MOLLIE_API_URL = "https://api.mollie.com/v2"
MOLLIE_API_KEY = os.environ.get("MOLLIE_API_KEY", "live_dummy_placeholder")

DB_PATH = "/mnt/usb4/stay4s_commercial.db"

# === Pricing Tiers ===
TIERS = {
    "free": {"name": "Free", "price": 0, "calls_per_hour": 10, "calls_per_month": 1000, "features": ["chat", "translate"]},
    "pro": {"name": "Pro", "price": 49, "calls_per_hour": 1000, "calls_per_month": 50000, "features": ["chat", "translate", "summarize", "search", "code", "scan", "email", "content"]},
    "enterprise": {"name": "Enterprise", "price": 499, "calls_per_hour": 10000, "calls_per_month": 500000, "features": ["all", "agents", "train", "rom", "whatsapp", "priority_support"]},
}

# === API Keys ===
API_KEYS = {
    "stay4s-free-demo": {"tier": "free", "customer": "Demo Free", "email": "demo@stay4s.com"},
    "stay4s-pro-demo": {"tier": "pro", "customer": "Demo Pro", "email": "pro@stay4s.com"},
    "stay4s-enterprise-demo": {"tier": "enterprise", "customer": "Demo Enterprise", "email": "ent@stay4s.com"},
}

# === Database ===
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key TEXT, endpoint TEXT, timestamp TEXT,
        tokens_in INTEGER, tokens_out INTEGER, cost REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE, name TEXT, company TEXT,
        tier TEXT, api_key TEXT, mollie_customer_id TEXT,
        created_at TEXT, status TEXT DEFAULT 'active'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER, amount REAL, currency TEXT,
        status TEXT, mollie_payment_id TEXT, created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS revenue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT, amount REAL, currency TEXT, description TEXT, timestamp TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# === Cloudflare AI ===
async def cf_ai_run(model, inputs):
    headers = {"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{CF_AI_URL}{model}", json=inputs, headers=headers)
        data = r.json()
        if data.get("success"):
            return data["result"]
        return {"error": data.get("errors", "AI error")}

async def cf_chat(prompt, system="Je bent Stay4S AI, een behulpzame Nederlandse AI assistent."):
    result = await cf_ai_run(CF_MODEL_CHAT, {"messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
    if isinstance(result, dict) and "response" in result:
        return result["response"]
    return str(result)

# === Auth & Rate Limiting ===
async def verify_key(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing API key")
    key = auth.split("Bearer ")[1]
    if key not in API_KEYS:
        raise HTTPException(401, "Invalid API key")
    
    # Check rate limit
    tier = API_KEYS[key]["tier"]
    tier_info = TIERS[tier]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    c.execute("SELECT COUNT(*) FROM usage WHERE api_key=? AND timestamp>?", (key, one_hour_ago))
    count = c.fetchone()[0]
    conn.close()
    if count >= tier_info["calls_per_hour"]:
        raise HTTPException(429, f"Rate limit exceeded ({tier_info['calls_per_hour']}/hour)")
    
    return key, tier

def log_usage(key, endpoint, tokens_in=0, tokens_out=0, cost=0.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO usage (api_key, endpoint, timestamp, tokens_in, tokens_out, cost) VALUES (?,?,?,?,?,?)",
              (key, endpoint, datetime.utcnow().isoformat(), tokens_in, tokens_out, cost))
    conn.commit()
    conn.close()

def log_revenue(source, amount, description=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO revenue (source, amount, currency, description, timestamp) VALUES (?,?,?,?,?)",
              (source, amount, "EUR", description, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

# === API ENDPOINTS ===

@app.get("/")
async def dashboard():
    return HTMLResponse(COMMERCIAL_DASHBOARD)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "stay4s-gateway-v2", "version": "2.0.0"}

# --- 1. Chat API ---
@app.post("/v1/chat")
async def chat(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    prompt = body.get("prompt", body.get("message", ""))
    system = body.get("system", "Je bent Stay4S AI, een behulpzame Nederlandse AI assistent.")
    response = await cf_chat(prompt, system)
    log_usage(key, "chat", len(prompt), len(response), 0.001)
    return {"endpoint": "chat", "response": response, "tier": tier}

# --- 2. Scan API (Scam Detection) ---
@app.post("/v1/scan")
async def scan(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    message = body.get("message", "")
    system = "Je bent een scam detector. Analyseer het bericht en geef: category, risk_score (0-100), explanation. Format: JSON."
    result = await cf_chat(f"Analyseer: {message}", system)
    log_usage(key, "scan", len(message), len(result), 0.01)
    log_revenue("scan", 0.01, f"Scam scan for {key}")
    return {"endpoint": "scan", "result": result, "tier": tier}

# --- 3. Translate API ---
@app.post("/v1/translate")
async def translate(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    text = body.get("text", "")
    target = body.get("target", "en")
    result = await cf_ai_run(CF_MODEL_TRANSLATE, {"text": text, "source_lang": "nl", "target_lang": target})
    log_usage(key, "translate", len(text), len(str(result)), 0.005)
    return {"endpoint": "translate", "result": result, "tier": tier}

# --- 4. Summarize API ---
@app.post("/v1/summarize")
async def summarize(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    text = body.get("text", "")
    system = "Vat de volgende tekst samen in maximaal 3 zinnen."
    result = await cf_chat(text, system)
    log_usage(key, "summarize", len(text), len(result), 0.005)
    return {"endpoint": "summarize", "summary": result, "tier": tier}

# --- 5. Search API ---
@app.post("/v1/search")
async def search(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    query = body.get("query", "")
    system = "Zoek informatie en geef een duidelijk antwoord in het Nederlands."
    result = await cf_chat(query, system)
    log_usage(key, "search", len(query), len(result), 0.01)
    return {"endpoint": "search", "result": result, "tier": tier}

# --- 6. Code API ---
@app.post("/v1/code")
async def code(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    desc = body.get("description", body.get("prompt", ""))
    lang = body.get("language", "python")
    system = f"Genereer {lang} code. Geef alleen code, geen uitleg."
    result = await cf_chat(desc, system)
    log_usage(key, "code", len(desc), len(result), 0.02)
    log_revenue("code", 0.02, f"Code gen for {key}")
    return {"endpoint": "code", "code": result, "language": lang, "tier": tier}

# --- 7. Email API ---
@app.post("/v1/email")
async def email(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    system = "Genereer een professionele email in het Nederlands. Onderwerp op eerste regel, dan lege regel, dan inhoud."
    result = await cf_chat(body.get("prompt", "Schrijf een email"), system)
    log_usage(key, "email", 100, len(result), 0.01)
    return {"endpoint": "email", "email": result, "tier": tier}

# --- 8. Content API ---
@app.post("/v1/content")
async def content(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    system = "Genereer marketing content in het Nederlands. Creatief en professioneel."
    result = await cf_chat(body.get("prompt", "Schrijf een blog post"), system)
    log_usage(key, "content", 100, len(result), 0.02)
    log_revenue("content", 0.02, f"Content gen for {key}")
    return {"endpoint": "content", "content": result, "tier": tier}

# === NEW REVENUE ENDPOINTS ===

# --- 9. Agents API (EUR 0.05/task) ---
@app.post("/v1/agents")
async def agents(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    task = body.get("task", "")
    system = "Je bent Stay4S AI Agent. Voer de taak stap-voor-stap uit. Geef: 1) Plan, 2) Tool calls needed, 3) Expected result."
    result = await cf_chat(task, system)
    log_usage(key, "agents", len(task), len(result), 0.05)
    log_revenue("agents", 0.05, f"Agent task for {key}")
    return {"endpoint": "agents", "plan": result, "tier": tier, "cost": 0.05}

# --- 10. Train Quote API (EUR 999+) ---
@app.post("/v1/train")
async def train_quote(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    use_case = body.get("use_case", "")
    data_size = body.get("data_size", "unknown")
    system = "Je bent een AI training consultant. Geef een offerte voor custom model training. Include: recommended model, estimated time, cost estimate (EUR 999-9999), and deliverables."
    result = await cf_chat(f"Use case: {use_case}, Data size: {data_size}", system)
    log_usage(key, "train", len(use_case), len(result), 0.0)
    log_revenue("train_quote", 0.0, f"Training quote for {key}")
    return {"endpoint": "train", "quote": result, "tier": tier}

# --- 11. Batch Scan API (EUR 0.005/scan) ---
@app.post("/v1/scan/batch")
async def scan_batch(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    messages = body.get("messages", [])
    if len(messages) > 1000:
        raise HTTPException(400, "Max 1000 messages per batch")
    results = []
    for msg in messages[:100]:
        system = "Je bent een scam detector. Geef: risk_score (0-100) en category. Compact JSON."
        result = await cf_chat(f"Analyseer: {msg}", system)
        results.append({"message": msg[:50], "result": result})
    total_cost = len(messages) * 0.005
    log_usage(key, "scan_batch", sum(len(m) for m in messages), len(str(results)), total_cost)
    log_revenue("scan_batch", total_cost, f"Batch scan {len(messages)} msgs for {key}")
    return {"endpoint": "scan_batch", "results": results, "count": len(results), "cost": total_cost, "tier": tier}

# --- 12. WhatsApp Setup API (EUR 99/mo) ---
@app.post("/v1/whatsapp")
async def whatsapp_setup(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    company = body.get("company", "")
    system = "Genereer een WhatsApp AI klantenservice setup plan in het Nederlands. Include: welkomstbericht, FAQ antwoorden, doorverwijzingsregels."
    result = await cf_chat(f"Bedrijf: {company}", system)
    log_usage(key, "whatsapp", len(company), len(result), 0.0)
    log_revenue("whatsapp_setup", 99.0, f"WhatsApp setup for {company}")
    return {"endpoint": "whatsapp", "setup": result, "monthly_cost": 99, "tier": tier}

# --- 13. ROM Build API (EUR 499/build) ---
@app.post("/v1/rom")
async def rom_build(request: Request, key_tier: tuple = Depends(verify_key)):
    key, tier = key_tier
    body = await request.json()
    device = body.get("device", "pixel-9a")
    features = body.get("features", ["degoogled", "dutch", "stay4s-apps"])
    system = "Genereer een custom ROM build plan. Include: device, AOSP version, build time estimate, features, and deployment steps."
    result = await cf_chat(f"Apparaat: {device}, Features: {json.dumps(features)}", system)
    log_usage(key, "rom", 100, len(result), 0.0)
    log_revenue("rom_build", 499.0, f"ROM build for {device}")
    return {"endpoint": "rom", "plan": result, "cost": 499, "tier": tier}

# === COMMERCIAL ENDPOINTS ===

# --- Pricing ---
@app.get("/pricing")
async def pricing():
    return {"tiers": TIERS, "currency": "EUR"}

# --- Create Customer (Mollie) ---
@app.post("/customers/create")
async def create_customer(request: Request):
    body = await request.json()
    email = body.get("email", "")
    name = body.get("name", "")
    company = body.get("company", "")
    tier = body.get("tier", "free")
    
    # Generate API key
    api_key = "stay4s-" + hashlib.sha256(f"{email}{time.time()}".encode()).hexdigest()[:24]
    API_KEYS[api_key] = {"tier": tier, "customer": name, "email": email}
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO customers (email, name, company, tier, api_key, created_at) VALUES (?,?,?,?,?,?)",
              (email, name, company, tier, api_key, datetime.utcnow().isoformat()))
    conn.commit()
    customer_id = c.lastrowid
    conn.close()
    
    return {"customer_id": customer_id, "api_key": api_key, "tier": tier, "monthly_price": TIERS[tier]["price"]}

# --- Create Payment (Mollie) ---
@app.post("/payments/create")
async def create_payment(request: Request):
    body = await request.json()
    api_key = body.get("api_key", "")
    if api_key not in API_KEYS:
        raise HTTPException(401, "Invalid API key")
    
    tier = API_KEYS[api_key]["tier"]
    amount = TIERS[tier]["price"]
    if amount == 0:
        return {"message": "Free tier - no payment needed"}
    
    # In production, create Mollie payment here
    # For now, log the payment intent
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO payments (customer_id, amount, currency, status, created_at) VALUES (?,?,?,?,?)",
              (1, amount, "EUR", "pending", datetime.utcnow().isoformat()))
    conn.commit()
    payment_id = c.lastrowid
    conn.close()
    
    log_revenue("payment_intent", amount, f"Payment intent for {api_key}")
    
    return {
        "payment_id": payment_id,
        "amount": amount,
        "currency": "EUR",
        "tier": tier,
        "checkout_url": f"https://www.mollie.com/checkout/select-method/{payment_id}",
        "status": "pending"
    }

# --- Mollie Webhook ---
@app.post("/payments/webhook")
async def mollie_webhook(request: Request):
    body = await request.json()
    payment_id = body.get("id", "")
    status = body.get("status", "")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE payments SET status=? WHERE mollie_payment_id=?", (status, payment_id))
    if status == "paid":
        c.execute("SELECT amount FROM payments WHERE mollie_payment_id=?", (payment_id))
        row = c.fetchone()
        if row:
            log_revenue("payment", row[0], f"Mollie payment {payment_id}")
    conn.commit()
    conn.close()
    
    return {"status": "ok"}

# --- Usage Analytics ---
@app.get("/admin/usage")
async def admin_usage():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Total calls
    c.execute("SELECT COUNT(*) FROM usage")
    total_calls = c.fetchone()[0]
    
    # Calls by endpoint
    c.execute("SELECT endpoint, COUNT(*) as count FROM usage GROUP BY endpoint ORDER BY count DESC")
    by_endpoint = [{"endpoint": r[0], "calls": r[1]} for r in c.fetchall()]
    
    # Calls by API key
    c.execute("SELECT api_key, COUNT(*) as count FROM usage GROUP BY api_key ORDER BY count DESC")
    by_key = [{"api_key": r[0][:12] + "...", "calls": r[1]} for r in c.fetchall()]
    
    # Revenue
    c.execute("SELECT SUM(amount) FROM revenue")
    total_revenue = c.fetchone()[0] or 0
    
    c.execute("SELECT source, SUM(amount) as total FROM revenue GROUP BY source ORDER BY total DESC")
    revenue_by_source = [{"source": r[0], "total": r[1]} for r in c.fetchall()]
    
    # Recent activity
    c.execute("SELECT endpoint, timestamp, api_key FROM usage ORDER BY id DESC LIMIT 20")
    recent = [{"endpoint": r[0], "timestamp": r[1], "api_key": r[2][:12] + "..."} for r in c.fetchall()]
    
    conn.close()
    
    return {
        "total_calls": total_calls,
        "by_endpoint": by_endpoint,
        "by_key": by_key,
        "total_revenue_eur": round(total_revenue, 2),
        "revenue_by_source": revenue_by_source,
        "recent_activity": recent,
        "pricing_tiers": TIERS
    }

# --- API Keys Management ---
@app.get("/admin/keys")
async def admin_keys():
    return {"keys": [{"key": k[:12] + "...", "tier": v["tier"], "customer": v["customer"]} for k, v in API_KEYS.items()]}

# --- API Documentation ---
@app.get("/docs")
async def api_docs():
    return JSONResponse({
        "name": "Stay4S AI API",
        "version": "2.0.0",
        "base_url": "https://api.stay4s.com",
        "endpoints": [
            {"method": "POST", "path": "/v1/chat", "description": "AI Chat (Dutch)", "cost": "EUR 0.001/call", "tier": "free+"},
            {"method": "POST", "path": "/v1/scan", "description": "Scam Detection", "cost": "EUR 0.01/scan", "tier": "pro+"},
            {"method": "POST", "path": "/v1/scan/batch", "description": "Bulk Scam Detection", "cost": "EUR 0.005/scan", "tier": "pro+"},
            {"method": "POST", "path": "/v1/translate", "description": "Translation", "cost": "EUR 0.005/call", "tier": "free+"},
            {"method": "POST", "path": "/v1/summarize", "description": "Text Summarization", "cost": "EUR 0.005/call", "tier": "pro+"},
            {"method": "POST", "path": "/v1/search", "description": "AI Search", "cost": "EUR 0.01/call", "tier": "pro+"},
            {"method": "POST", "path": "/v1/code", "description": "Code Generation", "cost": "EUR 0.02/call", "tier": "pro+"},
            {"method": "POST", "path": "/v1/email", "description": "Email Generation", "cost": "EUR 0.01/call", "tier": "pro+"},
            {"method": "POST", "path": "/v1/content", "description": "Content Generation", "cost": "EUR 0.02/call", "tier": "pro+"},
            {"method": "POST", "path": "/v1/agents", "description": "AI Agent Task Execution", "cost": "EUR 0.05/task", "tier": "enterprise"},
            {"method": "POST", "path": "/v1/train", "description": "Custom Model Training Quote", "cost": "EUR 999+", "tier": "enterprise"},
            {"method": "POST", "path": "/v1/whatsapp", "description": "WhatsApp AI Setup", "cost": "EUR 99/mo", "tier": "pro+"},
            {"method": "POST", "path": "/v1/rom", "description": "Custom ROM Build", "cost": "EUR 499/build", "tier": "enterprise"},
            {"method": "POST", "path": "/customers/create", "description": "Create Customer Account", "cost": "free"},
            {"method": "POST", "path": "/payments/create", "description": "Create Payment", "cost": "tier price"},
            {"method": "POST", "path": "/payments/webhook", "description": "Mollie Payment Webhook", "cost": "free"},
            {"method": "GET", "path": "/pricing", "description": "Get Pricing Tiers", "cost": "free"},
            {"method": "GET", "path": "/admin/usage", "description": "Usage Analytics", "cost": "admin"},
            {"method": "GET", "path": "/admin/keys", "description": "API Key Management", "cost": "admin"},
            {"method": "GET", "path": "/docs", "description": "API Documentation", "cost": "free"},
        ],
        "pricing": TIERS,
        "auth": "Bearer token in Authorization header"
    })

COMMERCIAL_DASHBOARD = """<!DOCTYPE html>
<html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stay4S Commercial Gateway</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,sans-serif}
body{background:#0a0e27;color:#fff;min-height:100vh}
.header{background:linear-gradient(135deg,#667eea,#764ba2);padding:20px;text-align:center}
.header h1{font-size:28px;margin-bottom:5px}
.header p{opacity:0.8}
.container{max-width:1200px;margin:20px auto;padding:0 20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:15px;margin:20px 0}
.card{background:#151a3a;padding:20px;border-radius:12px;border:1px solid #2a3050}
.card h3{color:#667eea;margin-bottom:10px;font-size:14px;text-transform:uppercase}
.card .value{font-size:32px;font-weight:bold}
.card .sub{opacity:0.6;font-size:12px;margin-top:5px}
.tabs{display:flex;gap:10px;margin:20px 0;flex-wrap:wrap}
.tab{padding:10px 20px;background:#151a3a;border-radius:8px;cursor:pointer;border:1px solid #2a3050}
.tab.active{background:#667eea;border-color:#667eea}
.endpoint{background:#151a3a;padding:15px;border-radius:8px;margin:10px 0;display:flex;justify-content:space-between;align-items:center}
.method{padding:3px 10px;border-radius:4px;font-weight:bold;font-size:12px}
.POST{background:#49b675}.GET{background:#3898d9}
.price{color:#ffd700;font-weight:bold}
.tier{padding:2px 8px;border-radius:4px;font-size:11px;background:#2a3050}
.pricing-card{background:#151a3a;padding:25px;border-radius:12px;text-align:center;border:2px solid #2a3050}
.pricing-card.featured{border-color:#667eea;transform:scale(1.05)}
.pricing-card .price{font-size:42px;font-weight:bold;margin:10px 0}
.pricing-card ul{list-style:none;text-align:left;margin:15px 0}
.pricing-card li{padding:5px 0;border-bottom:1px solid #2a3050}
.btn{display:inline-block;padding:10px 30px;background:#667eea;color:#fff;text-decoration:none;border-radius:8px;margin-top:15px}
a{color:#667eea}
</style></head><body>
<div class="header"><h1>Stay4S Commercial Gateway v2</h1><p>Soevereine Nederlandse AI API - Betaald & Klaar voor Zakelijk Gebruik</p></div>
<div class="container">
<div class="grid">
<div class="card"><h3>Totale API Calls</h3><div class="value" id="total-calls">-</div><div class="sub">All time</div></div>
<div class="card"><h3>Omzet (EUR)</h3><div class="value" id="revenue" style="color:#49b675">EUR 0</div><div class="sub">All time revenue</div></div>
<div class="card"><h3>Actieve Klanten</h3><div class="value" id="customers">3</div><div class="sub">Demo keys actief</div></div>
<div class="card"><h3>Endpoints</h3><div class="value">13</div><div class="sub">Waarvan 5 nieuw</div></div>
</div>
<div class="tabs">
<div class="tab active" onclick="showTab('pricing')">Pricing</div>
<div class="tab" onclick="showTab('endpoints')">API Endpoints</div>
<div class="tab" onclick="showTab('usage')">Usage Analytics</div>
<div class="tab" onclick="showTab('docs')">Quick Start</div>
</div>
<div id="pricing" class="tab-content">
<div class="grid" style="grid-template-columns:repeat(3,1fr)">
<div class="pricing-card"><h3>Free</h3><div class="price">EUR 0</div><p>Per maand</p><ul><li>10 calls/uur</li><li>Chat + Translate</li><li>Community support</li><li>1.000 calls/maand</li></ul><a class="btn" href="#">Start Free</a></div>
<div class="pricing-card featured"><h3>Pro</h3><div class="price">EUR 49</div><p>Per maand</p><ul><li>1.000 calls/uur</li><li>Alle 8 endpoints</li><li>Email support</li><li>50.000 calls/maand</li><li>WhatsApp AI setup</li></ul><a class="btn" href="#">Start Pro</a></div>
<div class="pricing-card"><h3>Enterprise</h3><div class="price">EUR 499</div><p>Per maand</p><ul><li>10.000 calls/uur</li><li>Alle 13 endpoints</li><li>Priority support</li><li>500.000 calls/maand</li><li>AI Agents + Training</li><li>Custom ROM builds</li></ul><a class="btn" href="#">Contact Sales</a></div>
</div></div>
<div id="endpoints" class="tab-content" style="display:none">
<h3>13 API Endpoints</h3>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/chat</div><div><span class="price">EUR 0.001</span> <span class="tier">free+</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/scan</div><div><span class="price">EUR 0.01</span> <span class="tier">pro+</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/scan/batch</div><div><span class="price">EUR 0.005</span> <span class="tier">pro+</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/translate</div><div><span class="price">EUR 0.005</span> <span class="tier">free+</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/summarize</div><div><span class="price">EUR 0.005</span> <span class="tier">pro+</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/search</div><div><span class="price">EUR 0.01</span> <span class="tier">pro+</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/code</div><div><span class="price">EUR 0.02</span> <span class="tier">pro+</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/email</div><div><span class="price">EUR 0.01</span> <span class="tier">pro+</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/content</div><div><span class="price">EUR 0.02</span> <span class="tier">pro+</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/agents</div><div><span class="price">EUR 0.05</span> <span class="tier">enterprise</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/train</div><div><span class="price">EUR 999+</span> <span class="tier">enterprise</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/whatsapp</div><div><span class="price">EUR 99/mo</span> <span class="tier">pro+</span></div></div>
<div class="endpoint"><div><span class="method POST">POST</span> /v1/rom</div><div><span class="price">EUR 499</span> <span class="tier">enterprise</span></div></div>
</div>
<div id="usage" class="tab-content" style="display:none">
<div class="grid">
<div class="card"><h3>Calls per Endpoint</h3><div id="endpoint-stats">Loading...</div></div>
<div class="card"><h3>Revenue per Source</h3><div id="revenue-stats">Loading...</div></div>
</div></div>
<div id="docs" class="tab-content" style="display:none">
<div class="card"><h3>Quick Start</h3>
<pre style="background:#0a0e27;padding:15px;border-radius:8px;overflow-x:auto;color:#49b675">
# Python
import requests
r = requests.post("https://api.stay4s.com/v1/chat",
    json={"prompt": "Hallo!"},
    headers={"Authorization": "Bearer stay4s-free-demo"})
print(r.json()["response"])

# JavaScript
fetch("https://api.stay4s.com/v1/chat", {
    method: "POST",
    headers: {"Authorization": "Bearer stay4s-free-demo", "Content-Type": "application/json"},
    body: JSON.stringify({prompt: "Hallo!"})
}).then(r => r.json()).then(d => console.log(d.response))

# curl
curl -X POST https://api.stay4s.com/v1/chat \
  -H "Authorization: Bearer stay4s-free-demo" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hallo!"}'
</pre>
</div></div>
</div>
<script>
function showTab(t){document.querySelectorAll('.tab-content').forEach(c=>c.style.display='none');document.getElementById(t).style.display='block';document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));event.target.classList.add('active')}
fetch('/admin/usage').then(r=>r.json()).then(d=>{document.getElementById('total-calls').textContent=d.total_calls;document.getElementById('revenue').textContent='EUR '+d.total_revenue_eur;let e=d.by_endpoint.map(x=>'<div>'+x.endpoint+': '+x.calls+'</div>').join('');document.getElementById('endpoint-stats').innerHTML=e;let r=d.revenue_by_source.map(x=>'<div>'+x.source+': EUR '+x.total.toFixed(2)+'</div>').join('');document.getElementById('revenue-stats').innerHTML=r||'No revenue yet'})
</script>
</body></html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8130)
