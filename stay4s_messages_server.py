#!/usr/bin/env python3
"""
Stay4S Message Server - Eigen messaging platform
WebSocket real-time + REST API + AI integration
"""
import asyncio, json, time, os, hashlib, sqlite3, uuid
from datetime import datetime
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="Stay4S Messages", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = "/mnt/usb4/stay4s_messages.db"
CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "YOUR_CF_API_TOKEN")
CF_ACCOUNT_ID = "59513e1a305610f0fb192d73dba01dbd"
CF_AI_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/"
CF_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

# Connected clients: {user_id: websocket}
clients = {}

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, name TEXT, phone TEXT UNIQUE, 
        password_hash TEXT, created_at TEXT, avatar TEXT DEFAULT 'S4'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY, sender_id TEXT, receiver_id TEXT,
        content TEXT, timestamp TEXT, status TEXT DEFAULT 'sent',
        is_ai BOOLEAN DEFAULT 0, chat_id TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS contacts (
        user_id TEXT, contact_id TEXT, added_at TEXT,
        PRIMARY KEY (user_id, contact_id)
    )""")
    conn.commit()
    conn.close()

init_db()

async def cf_chat(prompt, system="Je bent Stay4S AI, een behulpzame Nederlandse AI assistent. Geef kort en heldere antwoorden."):
    headers = {"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{CF_AI_URL}{CF_MODEL}", 
            json={"messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}, 
            headers=headers)
        data = r.json()
        if data.get("success"):
            return data["result"].get("response", str(data["result"]))
        return "Sorry, ik kan nu niet antwoorden."

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# === REST API ===

@app.get("/")
async def home():
    return HTMLResponse(MESSAGING_PWA)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "stay4s-messages", "users": len(clients), "version": "1.0.0"}

# --- Register ---
@app.post("/api/register")
async def register(request: Request):
    body = await request.json()
    name = body.get("name", "")
    phone = body.get("phone", "")
    password = body.get("password", "")
    if not name or not phone or not password:
        return {"error": "Vul alle velden in"}
    
    user_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (id, name, phone, password_hash, created_at) VALUES (?,?,?,?,?)",
                  (user_id, name, phone, hash_pw(password), datetime.utcnow().isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return {"error": "Dit nummer is al geregistreerd"}
    conn.close()
    return {"user_id": user_id, "name": name, "phone": phone}

# --- Login ---
@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    phone = body.get("phone", "")
    password = body.get("password", "")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name FROM users WHERE phone=? AND password_hash=?", (phone, hash_pw(password)))
    row = c.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "name": row[1], "phone": phone}
    return {"error": "Onjuist nummer of wachtwoord"}

# --- Search user by phone ---
@app.post("/api/search")
async def search_user(request: Request):
    body = await request.json()
    phone = body.get("phone", "")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, phone FROM users WHERE phone=?", (phone,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "name": row[1], "phone": row[2]}
    return {"error": "Gebruiker niet gevonden"}

# --- Add contact ---
@app.post("/api/contacts/add")
async def add_contact(request: Request):
    body = await request.json()
    user_id = body.get("user_id", "")
    contact_id = body.get("contact_id", "")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO contacts (user_id, contact_id, added_at) VALUES (?,?,?)",
              (user_id, contact_id, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return {"status": "added"}

# --- Get contacts ---
@app.get("/api/contacts/{user_id}")
async def get_contacts(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT u.id, u.name, u.phone, u.avatar FROM contacts co 
                 JOIN users u ON co.contact_id = u.id WHERE co.user_id=?""", (user_id,))
    contacts = [{"id": r[0], "name": r[1], "phone": r[2], "avatar": r[3]} for r in c.fetchall()]
    # Also add Stay4S AI as a contact
    contacts.insert(0, {"id": "stay4s-ai", "name": "Stay4S AI", "phone": "AI", "avatar": "AI"})
    conn.close()
    return {"contacts": contacts}

# --- Get messages ---
@app.get("/api/messages/{user_id}/{contact_id}")
async def get_messages(user_id: str, contact_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT id, sender_id, content, timestamp, status, is_ai FROM messages 
                 WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                 ORDER BY timestamp ASC""", (user_id, contact_id, contact_id, user_id))
    messages = [{"id": r[0], "sender": r[1], "content": r[2], "timestamp": r[3], "status": r[4], "is_ai": r[5]} for r in c.fetchall()]
    conn.close()
    return {"messages": messages}

# --- Send message (REST fallback) ---
@app.post("/api/send")
async def send_message(request: Request):
    body = await request.json()
    sender_id = body.get("sender_id", "")
    receiver_id = body.get("receiver_id", "")
    content = body.get("content", "")
    
    msg_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    is_ai = 1 if receiver_id == "stay4s-ai" or sender_id == "stay4s-ai" else 0
    c.execute("INSERT INTO messages (id, sender_id, receiver_id, content, timestamp, is_ai, chat_id) VALUES (?,?,?,?,?,?,?)",
              (msg_id, sender_id, receiver_id, content, timestamp, is_ai, f"{sender_id}_{receiver_id}"))
    conn.commit()
    conn.close()
    
    # Try to deliver via WebSocket
    if receiver_id in clients:
        try:
            await clients[receiver_id].send_json({"type": "message", "id": msg_id, "sender": sender_id, "content": content, "timestamp": timestamp})
        except:
            pass
    
    # If sending to Stay4S AI, get AI response
    if receiver_id == "stay4s-ai":
        ai_response = await cf_chat(content)
        ai_msg_id = str(uuid.uuid4())[:8]
        ai_timestamp = datetime.utcnow().isoformat()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO messages (id, sender_id, receiver_id, content, timestamp, is_ai, chat_id) VALUES (?,?,?,?,?,?,?)",
                  (ai_msg_id, "stay4s-ai", sender_id, ai_response, ai_timestamp, 1, f"stay4s-ai_{sender_id}"))
        conn.commit()
        conn.close()
        # Send AI response via WebSocket
        if sender_id in clients:
            try:
                await clients[sender_id].send_json({"type": "message", "id": ai_msg_id, "sender": "stay4s-ai", "content": ai_response, "timestamp": ai_timestamp, "is_ai": True})
            except:
                pass
        return {"status": "sent", "ai_response": ai_response}
    
    return {"status": "sent", "message_id": msg_id}

# === WebSocket for real-time messaging ===
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    clients[user_id] = websocket
    try:
        # Notify user is online
        for uid, ws in list(clients.items()):
            if uid != user_id:
                try:
                    await ws.send_json({"type": "presence", "user_id": user_id, "status": "online"})
                except:
                    pass
        
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "message":
                receiver_id = msg.get("receiver", "")
                content = msg.get("content", "")
                msg_id = str(uuid.uuid4())[:8]
                timestamp = datetime.utcnow().isoformat()
                
                # Store in DB
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                is_ai = 1 if receiver_id == "stay4s-ai" else 0
                c.execute("INSERT INTO messages (id, sender_id, receiver_id, content, timestamp, is_ai, chat_id) VALUES (?,?,?,?,?,?,?)",
                          (msg_id, user_id, receiver_id, content, timestamp, is_ai, f"{user_id}_{receiver_id}"))
                conn.commit()
                conn.close()
                
                # Send to receiver if online
                if receiver_id in clients:
                    await clients[receiver_id].send_json({"type": "message", "id": msg_id, "sender": user_id, "content": content, "timestamp": timestamp})
                
                # If AI, get response and send back
                if receiver_id == "stay4s-ai":
                    await websocket.send_json({"type": "typing", "sender": "stay4s-ai"})
                    ai_response = await cf_chat(content)
                    ai_msg_id = str(uuid.uuid4())[:8]
                    ai_timestamp = datetime.utcnow().isoformat()
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("INSERT INTO messages (id, sender_id, receiver_id, content, timestamp, is_ai, chat_id) VALUES (?,?,?,?,?,?,?)",
                              (ai_msg_id, "stay4s-ai", user_id, ai_response, ai_timestamp, 1, f"stay4s-ai_{user_id}"))
                    conn.commit()
                    conn.close()
                    await websocket.send_json({"type": "message", "id": ai_msg_id, "sender": "stay4s-ai", "content": ai_response, "timestamp": ai_timestamp, "is_ai": True})
                
                # Confirm sent
                await websocket.send_json({"type": "sent", "id": msg_id})
                
            elif msg.get("type") == "typing":
                receiver_id = msg.get("receiver", "")
                if receiver_id in clients:
                    await clients[receiver_id].send_json({"type": "typing", "sender": user_id})
                    
    except WebSocketDisconnect:
        if user_id in clients:
            del clients[user_id]
        # Notify offline
        for uid, ws in list(clients.items()):
            try:
                await ws.send_json({"type": "presence", "user_id": user_id, "status": "offline"})
            except:
                pass

MESSAGING_PWA = """<!DOCTYPE html>
<html lang="nl"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Stay4S">
<meta name="theme-color" content="#0a0e27">
<link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%23667eea'/><text x='50' y='68' font-size='52' text-anchor='middle' fill='white' font-family='system-ui' font-weight='bold'>S4</text></svg>">
<title>Stay4S Messages</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent;font-family:-apple-system,BlinkMacSystemFont,sans-serif}
:root{--bg:#0a0e27;--card:#151a3a;--border:#2a3050;--primary:#667eea;--text:#e0e0e0;--green:#49b675;--blue:#3898d9}
body{background:var(--bg);color:var(--text);min-height:100vh;overflow:hidden}
#app{max-width:500px;margin:0 auto;height:100vh;display:flex;flex-direction:column;padding-top:env(safe-area-inset-top,44px);padding-bottom:env(safe-area-inset-bottom,34px)}
.screen{flex:1;display:none;flex-direction:column;overflow:hidden}
.screen.active{display:flex}
.header{background:linear-gradient(135deg,#667eea,#764ba2);padding:16px;color:#fff;display:flex;align-items:center;gap:10px;flex-shrink:0}
.header h1{font-size:20px;flex:1}
.header .btn{background:rgba(255,255,255,0.2);border:none;color:#fff;width:36px;height:36px;border-radius:50%;font-size:18px;cursor:pointer}
.input{padding:12px;background:var(--bg);border-bottom:1px solid var(--border);flex-shrink:0}
.input input{width:100%;padding:12px 16px;background:var(--card);border:1px solid var(--border);border-radius:12px;color:#fff;font-size:16px;outline:none}
.input input::placeholder{color:#555}
.list{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch}
.contact-item{display:flex;align-items:center;gap:12px;padding:14px 16px;border-bottom:1px solid var(--border);cursor:pointer;transition:background 0.2s}
.contact-item:active{background:var(--card)}
.avatar{width:48px;height:48px;border-radius:50%;background:var(--primary);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:bold;font-size:18px;flex-shrink:0}
.contact-info{flex:1;min-width:0}
.contact-name{font-size:16px;font-weight:600;color:#fff}
.contact-last{font-size:13px;color:#666;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.presence-dot{width:10px;height:10px;border-radius:50%;background:var(--green);flex-shrink:0}
.presence-dot.offline{background:#555}
.chat-header{display:flex;align-items:center;gap:10px;padding:12px 16px;background:var(--card);border-bottom:1px solid var(--border);flex-shrink:0}
.chat-header .back{background:none;border:none;color:var(--primary);font-size:24px;cursor:pointer}
.chat-header .name{flex:1;font-size:17px;font-weight:600;color:#fff}
.messages{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;-webkit-overflow-scrolling:touch}
.msg{max-width:80%;padding:10px 14px;border-radius:16px;font-size:15px;line-height:1.4;word-wrap:break-word;animation:fadeIn 0.2s}
@keyframes fadeIn{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.msg.sent{align-self:flex-end;background:var(--primary);color:#fff;border-bottom-right-radius:4px}
.msg.received{align-self:flex-start;background:var(--card);border:1px solid var(--border);border-bottom-left-radius:4px}
.msg.ai{align-self:flex-start;background:rgba(102,126,234,0.15);border:1px solid var(--primary);border-bottom-left-radius:4px}
.typing-indicator{align-self:flex-start;padding:10px 14px;background:var(--card);border-radius:16px;border-bottom-left-radius:4px}
.typing-indicator span{display:inline-block;width:6px;height:6px;background:#555;border-radius:50%;margin:0 2px;animation:typing 1.4s infinite}
.typing-indicator span:nth-child(2){animation-delay:0.2s}
.typing-indicator span:nth-child(3){animation-delay:0.4s}
@keyframes typing{0%,60%,100%{opacity:0.3}30%{opacity:1}}
.chat-input{padding:10px 12px;background:var(--bg);border-top:1px solid var(--border);display:flex;gap:8px;flex-shrink:0}
.chat-input input{flex:1;padding:12px 16px;background:var(--card);border:1px solid var(--border);border-radius:20px;color:#fff;font-size:15px;outline:none}
.chat-input input::placeholder{color:#555}
.chat-input button{width:40px;height:40px;border-radius:50%;background:var(--primary);border:none;color:#fff;font-size:18px;cursor:pointer;flex-shrink:0}
.btn-primary{display:block;width:100%;padding:14px;background:var(--primary);color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;margin:10px 0}
.btn-secondary{display:block;width:100%;padding:14px;background:var(--card);color:var(--primary);border:1px solid var(--border);border-radius:12px;font-size:16px;cursor:pointer;margin:5px 0}
.form{padding:20px;overflow-y:auto}
.form h2{color:#fff;margin-bottom:20px;text-align:center}
.form .label{font-size:14px;color:#888;margin:10px 0 5px}
.error{color:#e74c3c;font-size:14px;text-align:center;margin:10px 0}
</style></head><body>
<div id="app">
<!-- Login/Register Screen -->
<div id="screen-auth" class="screen active">
<div class="header"><h1>Stay4S Messages</h1></div>
<div class="form">
<h2>Welkom</h2>
<div class="label">Naam</div>
<input type="text" id="reg-name" placeholder="Jouw naam" class="input" style="width:100%;padding:12px;background:var(--card);border:1px solid var(--border);border-radius:12px;color:#fff;font-size:16px;outline:none">
<div class="label">Telefoonnummer</div>
<input type="tel" id="reg-phone" placeholder="+31..." style="width:100%;padding:12px;background:var(--card);border:1px solid var(--border);border-radius:12px;color:#fff;font-size:16px;outline:none;margin:5px 0">
<div class="label">Wachtwoord</div>
<input type="password" id="reg-password" placeholder="Wachtwoord" style="width:100%;padding:12px;background:var(--card);border:1px solid var(--border);border-radius:12px;color:#fff;font-size:16px;outline:none;margin:5px 0">
<button class="btn-primary" onclick="register()">Account aanmaken</button>
<button class="btn-secondary" onclick="showLogin()">Al een account? Inloggen</button>
<div id="auth-error" class="error"></div>
</div>
</div>
<!-- Login Screen -->
<div id="screen-login" class="screen">
<div class="header"><h1>Inloggen</h1><button class="btn" onclick="showAuth()">Terug</button></div>
<div class="form">
<div class="label">Telefoonnummer</div>
<input type="tel" id="login-phone" placeholder="+31..." style="width:100%;padding:12px;background:var(--card);border:1px solid var(--border);border-radius:12px;color:#fff;font-size:16px;outline:none;margin:5px 0">
<div class="label">Wachtwoord</div>
<input type="password" id="login-password" placeholder="Wachtwoord" style="width:100%;padding:12px;background:var(--card);border:1px solid var(--border);border-radius:12px;color:#fff;font-size:16px;outline:none;margin:5px 0">
<button class="btn-primary" onclick="login()">Inloggen</button>
<div id="login-error" class="error"></div>
</div>
</div>
<!-- Contacts List -->
<div id="screen-contacts" class="screen">
<div class="header"><h1>Berichten</h1><button class="btn" onclick="addContact()">+</button></div>
<div class="input"><input type="text" id="search-phone" placeholder="Zoek op telefoonnummer..." onkeypress="if(event.key==='Enter')searchUser()"></div>
<div class="list" id="contacts-list"></div>
</div>
<!-- Add Contact -->
<div id="screen-add" class="screen">
<div class="header"><button class="btn" onclick="showContacts()">&lt;</button><h1>Contact toevoegen</h1></div>
<div class="form">
<div class="label">Telefoonnummer</div>
<input type="tel" id="add-phone" placeholder="+31..." style="width:100%;padding:12px;background:var(--card);border:1px solid var(--border);border-radius:12px;color:#fff;font-size:16px;outline:none;margin:5px 0">
<button class="btn-primary" onclick="searchUser()">Zoeken</button>
<div id="search-result"></div>
</div>
</div>
<!-- Chat Screen -->
<div id="screen-chat" class="screen">
<div class="chat-header">
<button class="back" onclick="showContacts()">&lt;</button>
<div class="avatar" id="chat-avatar" style="width:40px;height:40px;font-size:14px"></div>
<div class="name" id="chat-name">Contact</div>
</div>
<div class="messages" id="chat-messages"></div>
<div class="chat-input">
<input type="text" id="msg-input" placeholder="Bericht..." onkeypress="if(event.key==='Enter')sendMessage()">
<button onclick="sendMessage()">&#9658;</button>
</div>
</div>
</div>
<script>
let API=location.origin;
let userId='',userName='',ws=null;
let currentContact=null;

function showScreen(s){document.querySelectorAll('.screen').forEach(c=>c.classList.remove('active'));document.getElementById('screen-'+s).classList.add('active')}
function showAuth(){showScreen('auth')}
function showLogin(){showScreen('login')}
function showContacts(){if(ws)ws.close();showScreen('contacts');loadContacts()}
function showChat(){showScreen('chat')}

async function register(){
const name=document.getElementById('reg-name').value.trim();
const phone=document.getElementById('reg-phone').value.trim();
const password=document.getElementById('reg-password').value.trim();
if(!name||!phone||!password){document.getElementById('auth-error').textContent='Vul alle velden in';return}
const r=await fetch(API+'/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,phone,password})});
const d=await r.json();
if(d.error){document.getElementById('auth-error').textContent=d.error;return}
userId=d.user_id;userName=name;localStorage.setItem('s4_uid',userId);localStorage.setItem('s4_name',name);localStorage.setItem('s4_phone',phone);
showContacts();connectWS();
}

async function login(){
const phone=document.getElementById('login-phone').value.trim();
const password=document.getElementById('login-password').value.trim();
const r=await fetch(API+'/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone,password})});
const d=await r.json();
if(d.error){document.getElementById('login-error').textContent=d.error;return}
userId=d.user_id;userName=d.name;localStorage.setItem('s4_uid',userId);localStorage.setItem('s4_name',d.name);localStorage.setItem('s4_phone',phone);
showContacts();connectWS();
}

function addContact(){showScreen('add')}

async function searchUser(){
const phone=document.getElementById('add-phone').value.trim()||document.getElementById('search-phone').value.trim();
if(!phone)return;
const r=await fetch(API+'/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone})});
const d=await r.json();
if(d.error){document.getElementById('search-result').innerHTML='<div class="error">'+d.error+'</div>';return}
document.getElementById('search-result').innerHTML='<div style="display:flex;align-items:center;gap:12px;padding:14px;background:var(--card);border-radius:12px;margin:10px 0"><div class="avatar">'+d.name.charAt(0)+'</div><div><div style="font-weight:600">'+d.name+'</div><div style="color:#888;font-size:13px">'+d.phone+'</div></div><button class="btn-primary" style="width:auto;padding:8px 20px;margin:0" onclick="addContactToList(\''+d.user_id+'\',\''+d.name+'\')">Toevoegen</button></div>';
}

async function addContactToList(cid,cname){
await fetch(API+'/api/contacts/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId,contact_id:cid})});
showContacts();
}

async function loadContacts(){
const r=await fetch(API+'/api/contacts/'+userId);
const d=await r.json();
const list=document.getElementById('contacts-list');
list.innerHTML='';
for(const c of d.contacts){
const div=document.createElement('div');
div.className='contact-item';
div.onclick=()=>openChat(c.id,c.name,c.avatar);
div.innerHTML='<div class="avatar">'+c.avatar+'</div><div class="contact-info"><div class="contact-name">'+c.name+'</div><div class="contact-last">'+(c.phone||'')+'</div></div><div class="presence-dot '+(c.id==='stay4s-ai'?'':'offline')+'"></div>';
list.appendChild(div);
}
}

async function openChat(contactId,contactName,avatar){
currentContact=contactId;
document.getElementById('chat-name').textContent=contactName;
document.getElementById('chat-avatar').textContent=avatar||contactName.charAt(0);
document.getElementById('chat-messages').innerHTML='';
showChat();
// Load history
const r=await fetch(API+'/api/messages/'+userId+'/'+contactId);
const d=await r.json();
for(const m of d.messages){
addMessage(m.content,m.sender===userId?'sent':(m.is_ai?'ai':'received'));
}
// Connect WebSocket
connectWS();
// Scroll to bottom
setTimeout(()=>{const el=document.getElementById('chat-messages');el.scrollTop=el.scrollHeight},100);
}

function connectWS(){
if(ws)ws.close();
const wsUrl=API.replace('http','ws')+'/ws/'+userId;
ws=new WebSocket(wsUrl);
ws.onmessage=function(e){
const msg=JSON.parse(e.data);
if(msg.type==='message'&&msg.sender===currentContact){
addMessage(msg.content,msg.is_ai?'ai':'received');
}else if(msg.type==='typing'&&msg.sender===currentContact){
showTyping();
}else if(msg.type==='presence'){
// Update presence
}
};
ws.onclose=function(){setTimeout(connectWS,3000)};
}

function addMessage(text,cls){
const div=document.createElement('div');
div.className='msg '+cls;
div.textContent=text;
document.getElementById('chat-messages').appendChild(div);
document.getElementById('chat-messages').scrollTop=document.getElementById('chat-messages').scrollHeight;
}

function showTyping(){
const existing=document.getElementById('typing-ind');
if(existing)return;
const div=document.createElement('div');
div.className='typing-indicator';
div.id='typing-ind';
div.innerHTML='<span></span><span></span><span></span>';
document.getElementById('chat-messages').appendChild(div);
document.getElementById('chat-messages').scrollTop=999999;
setTimeout(()=>{const e=document.getElementById('typing-ind');if(e)e.remove()},3000);
}

async function sendMessage(){
const input=document.getElementById('msg-input');
const text=input.value.trim();
if(!text||!currentContact)return;
input.value='';
addMessage(text,'sent');
// Send via REST (more reliable than WS on mobile)
const r=await fetch(API+'/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sender_id:userId,receiver_id:currentContact,content:text})});
const d=await r.json();
if(d.ai_response){
setTimeout(()=>{addMessage(d.ai_response,'ai');document.getElementById('chat-messages').scrollTop=999999},500);
}
}

// Auto-login on load
window.onload=function(){
const uid=localStorage.getItem('s4_uid');
const name=localStorage.getItem('s4_name');
if(uid&&name){userId=uid;userName=name;showContacts();connectWS()}else{showAuth()}
}
</script>
</body></html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8200)