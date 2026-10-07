#!/usr/bin/env python3
"""Stay4S Computer-Use Agent v2 -- Sterker dan Droid

Features:
1. Vision model (llama3.2-vision) voor schermanalyse
2. OCR text extractie (pytesseract + vision fallback)
3. Element detectie (knoppen, links, invoervelden)
4. Browser integratie (Playwright via Pi 5)
5. Opname/Afspeel modus (record/replay acties)
6. Veiligheidsbarrieres (blokkeert gevaarlijke acties)
7. Correctie leren (user corrigeert, AI leert)
8. Cross-service communicatie (alle 32+ Stay4S services)
9. Taak templates (voorgedefinieerde taken)
10. Multi-step planning (AI maakt plan voor uitvoeren)
"""
import os, json, base64, time, sqlite3, re, logging, requests
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stay4s-cu-v2")
app = FastAPI(title="Stay4S Computer-Use Agent v2", version="2.0")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://100.123.235.81:11434")
VISION_MODEL = os.environ.get("STAY4S_VISION_MODEL", "llama3.2-vision")
TEXT_MODEL = os.environ.get("STAY4S_MODEL", "stay4s-1b")

# Cloudflare Workers AI (fallback + primary for text)
CF_AI_TOKEN = os.environ.get("CF_AI_TOKEN", "YOUR_CF_API_TOKEN")
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "59513e1a305610f0fb192d73dba01dbd")
CF_MODEL = os.environ.get("CF_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
CF_VISION_MODEL = os.environ.get("CF_VISION_MODEL", "@cf/meta/llama-4-scout-17b-16e-instruct")
DB_PATH = "computer_use_v2.db"

PI5 = "http://100.123.235.81"
SERVICES = {
    "dashboard": f"{PI5}:8086", "agent_platform": f"{PI5}:8074",
    "browser_agent": f"{PI5}:8075", "sysadmin": f"{PI5}:8077",
    "rag": f"{PI5}:8087", "voice": f"{PI5}:8096",
    "gateway": f"{PI5}:8092", "hoofdagent": f"{PI5}:8093",
    "social": f"{PI5}:8095", "knowledge_graph": f"{PI5}:8097",
    "consciousness": f"{PI5}:8099", "scam_shield": f"{PI5}:8100",
    "bot_creator": f"{PI5}:8073", "whatsapp": f"{PI5}:8070",
    "commercial": f"{PI5}:8071", "api_keys": f"{PI5}:8072",
    "media_proxy": f"{PI5}:8076", "ai_browser": f"{PI5}:8078",
    "nextcloud": f"{PI5}:8085", "mcp_nexus": f"{PI5}:8090",
    "nexus_connectors": f"{PI5}:8094", "nexus_plugins": f"{PI5}:8105",
    "memory": f"{PI5}:8089", "open_webui": f"{PI5}:8088",
    "model_router": f"{PI5}:8091", "mesh": f"{PI5}:8098",
    "marketplace": f"{PI5}:8103", "billing": f"{PI5}:8104",
    "scheduler": f"{PI5}:8106", "notifier": f"{PI5}:8107",
    "monitor": f"{PI5}:8108", "data_pipeline": f"{PI5}:8109",
}

BLOCKED_PATTERNS = [
    r"del\s+/[sfq]", r"rm\s+-rf", r"format\s+[cde]", r"diskpart",
    r"reg\s+delete", r"shutdown", r"sysprep", r"cipher\s+/w",
    r"Remove-Item.*-Force", r"Clear-Disk", r"Reset-Computer",
]
SENSITIVE_KEYWORDS = ["wachtwoord", "password", "pincode", "creditcard", "iban", "bic", "ssn"]

def is_dangerous(action_data):
    action = action_data.get("action", "")
    text = action_data.get("text", "").lower()
    keys = action_data.get("keys", [])
    for kw in SENSITIVE_KEYWORDS:
        if kw in text:
            return True, f"Gevoelig: {kw}"
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Gevaarlijk: {pattern}"
    if action == "hotkey" and "alt+f4" in "+".join(keys).lower():
        return True, "Alt+F4"
    return False, ""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, plan TEXT, steps TEXT, status TEXT, created TEXT, completed TEXT, corrections TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS shortcuts (id INTEGER PRIMARY KEY AUTOINCREMENT, pattern TEXT, keys TEXT, action TEXT, context TEXT, count INTEGER DEFAULT 1, learned TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS corrections (id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, wrong_action TEXT, correct_action TEXT, context TEXT, learned TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS recordings (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, actions TEXT, created TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS templates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, steps TEXT, category TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS screen_history (id INTEGER PRIMARY KEY AUTOINCREMENT, screenshot TEXT, analysis TEXT, elements TEXT, timestamp TEXT)")
    templates = [
        ("Google Zoeken", "Zoek op Google", json.dumps([{"action":"hotkey","keys":["win","s"]},{"action":"type","text":"chrome"},{"action":"press","key":"enter"},{"action":"wait","seconds":2},{"action":"hotkey","keys":["ctrl","l"]},{"action":"type","text":"google.com"},{"action":"press","key":"enter"}]), "browser"),
        ("Email Sturen", "Open mail", json.dumps([{"action":"hotkey","keys":["win","s"]},{"action":"type","text":"outlook"},{"action":"press","key":"enter"},{"action":"wait","seconds":3},{"action":"hotkey","keys":["ctrl","n"]}]), "productivity"),
        ("Bestand Openen", "Open Verkenner", json.dumps([{"action":"hotkey","keys":["win","e"]},{"action":"wait","seconds":1},{"action":"hotkey","keys":["ctrl","l"]}]), "file"),
        ("Formulier Invullen", "Tab door formulier", json.dumps([{"action":"type","text":"NAAM"},{"action":"press","key":"tab"},{"action":"type","text":"EMAIL"},{"action":"press","key":"tab"}]), "productivity"),
        ("Screenshot", "Maak screenshot", json.dumps([{"action":"hotkey","keys":["win","shift","s"]},{"action":"wait","seconds":2}]), "utility"),
    ]
    for t in templates:
        c.execute("INSERT OR IGNORE INTO templates (name, description, steps, category) VALUES (?,?,?,?)", t)
    conn.commit(); conn.close()

init_db()

# Screen control
def take_screenshot():
    try:
        import pyautogui, io
        from PIL import Image
        img = pyautogui.screenshot()
        img = img.resize((640, 360))
        buf = io.BytesIO()
        img.save(buf, format="PNG", compress_level=6)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        logger.error(f"Screenshot: {e}")
        return None


def take_screenshot_small(max_width=640):
    """Kleine screenshot voor snelle Cloudflare AI vision calls"""
    try:
        import io
        from PIL import Image
        img = pyautogui.screenshot()
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except:
        return take_screenshot()

def get_screen_size():
    try:
        import pyautogui
        return pyautogui.size()
    except:
        return (1920, 1080)

def mouse_click(x, y, button="left"):
    try:
        import pyautogui
        pyautogui.click(x, y, button=button)
        return True
    except Exception as e:
        return str(e)

def keyboard_type(text):
    try:
        import pyautogui
        pyautogui.typewrite(text, interval=0.02)
        return True
    except:
        return False

def keyboard_hotkey(*keys):
    try:
        import pyautogui
        pyautogui.hotkey(*keys)
        return True
    except:
        return False

def keyboard_press(key):
    try:
        import pyautogui
        pyautogui.press(key)
        return True
    except:
        return False

def mouse_scroll(amount):
    try:
        import pyautogui
        pyautogui.scroll(amount)
        return True
    except:
        return False

def ocr_screen():
    try:
        import pyautogui
        import pytesseract
        from PIL import Image
        img = pyautogui.screenshot()
        text = pytesseract.image_to_string(img, lang="nld+eng")
        return text.strip()
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return None


def query_cloudflare_ai(prompt, image_b64=None, system="", model=None):
    """Query Cloudflare Workers AI - Llama 3.3 70B (veel sterker dan lokale 1B)"""
    try:
        use_model = CF_VISION_MODEL if image_b64 else CF_MODEL  # Always use Cloudflare models, not Ollama names
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if image_b64:
            # Vision model with image
            messages.append({"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]})
        else:
            messages.append({"role": "user", "content": prompt})
        
        payload = {"messages": messages, "max_tokens": 500, "temperature": 0.1}
        url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{use_model}"
        r = requests.post(url, json=payload, headers={
            "Authorization": f"Bearer {CF_AI_TOKEN}",
            "Content-Type": "application/json"
        }, timeout=30)
        
        if r.status_code == 200:
            data = r.json()
            if data.get("success") and data.get("result"):
                return data["result"].get("response", "").strip()
            elif data.get("result"):
                return data["result"].get("response", "").strip()
    except Exception as e:
        logger.error(f"Cloudflare AI: {e}")
    return None

def query_ollama(prompt, image_b64=None, system="", model=None):
    # Try Cloudflare Workers AI first (Llama 3.3 70B - veel sterker)
    cf_response = query_cloudflare_ai(prompt, image_b64, system, model)
    if cf_response and cf_response != "Error" and len(cf_response) > 5:
        logger.info("AI: Cloudflare Workers AI (Llama 3.3 70B)")
        return cf_response
    
    # Fallback to local Ollama
    try:
        use_model = model or TEXT_MODEL
        payload = {"model": use_model, "prompt": prompt, "system": system, "stream": False, "options": {"temperature": 0.1, "num_predict": 500}}
        if image_b64:
            payload["images"] = [image_b64]
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        if r.status_code == 200:
            resp = r.json().get("response", "").strip()
            if resp and len(resp) > 5:
                logger.info("AI: Ollama (local)")
                return resp
    except Exception as e:
        logger.error(f"Ollama: {e}")
    return "Error"

def analyze_screen_vision(task, screenshot_b64, ocr_text=None, history=None):
    system = f"""Jij bent Stay4S Computer-Use AI. Je ziet een screenshot (640x360).
{"OCR tekst: " + ocr_text[:500] if ocr_text else ""}
{"Eerdere acties: " + json.dumps(history[-3:]) if history else ""}
Taak: {task}
Bepaal de volgende actie als JSON:
- Klik: {{"action":"click","x":320,"y":180,"button":"left","description":"klik"}}
- Typ: {{"action":"type","text":"hallo","description":"typ"}}
- Sneltoets: {{"action":"hotkey","keys":["ctrl","c"],"description":"kopieer"}}
- Toets: {{"action":"press","key":"enter","description":"bevestig"}}
- Scroll: {{"action":"scroll","amount":-3,"description":"naar beneden"}}
- Wacht: {{"action":"wait","seconds":2,"description":"wacht"}}
- Klaar: {{"action":"done","summary":"voltooid","description":"klaar"}}
Geef ALLEEN JSON."""
    
    small_ss = take_screenshot_small(640)
    response = query_ollama("Volgende actie?", small_ss, system, model=VISION_MODEL)
    try:
        m = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if m:
            return json.loads(m.group())
    except:
        pass
    return {"action": "done", "summary": response[:200]}

def detect_elements(screenshot_b64):
    system = """Vind klikbare elementen. Geef JSON array:
[{"type":"button","text":"Opslaan","x":320,"y":50,"confidence":0.9}]
Geef ALLEEN JSON array."""
    response = query_ollama("Vind elementen", screenshot_b64, system, model=VISION_MODEL)
    try:
        m = re.search(r'\[.*?\]', response, re.DOTALL)
        if m:
            return json.loads(m.group())
    except:
        pass
    return []

def make_plan(task, screenshot_b64=None, ocr_text=None):
    system = f"""Maak een plan voor: {task}
{"Scherm: " + ocr_text[:300] if ocr_text else ""}
Geef JSON: {{"steps":["stap1","stap2","stap3"]}}"""
    response = query_ollama("Maak plan", screenshot_b64, system, model=TEXT_MODEL)
    try:
        m = re.search(r'\{.*?\}', response, re.DOTALL)
        if m:
            return json.loads(m.group()).get("steps", [])
    except:
        pass
    return [task]

def execute_action(action_data):
    dangerous, reason = is_dangerous(action_data)
    if dangerous:
        return {"blocked": True, "reason": reason}
    action = action_data.get("action", "done")
    if action == "click":
        x, y = action_data.get("x",0), action_data.get("y",0)
        sw, sh = get_screen_size()
        rx, ry = int(x*sw/640), int(y*sh/360)
        mouse_click(rx, ry, action_data.get("button","left"))
        return {"ok": True, "action": "click", "x": rx, "y": ry}
    elif action == "type":
        keyboard_type(action_data.get("text",""))
        return {"ok": True, "action": "type"}
    elif action == "hotkey":
        keys = action_data.get("keys",[])
        keyboard_hotkey(*keys)
        learn_shortcut("+".join(keys), "+".join(keys), action_data.get("description",""))
        return {"ok": True, "action": "hotkey", "keys": keys}
    elif action == "press":
        keyboard_press(action_data.get("key","enter"))
        return {"ok": True, "action": "press"}
    elif action == "scroll":
        mouse_scroll(action_data.get("amount",-3))
        return {"ok": True, "action": "scroll"}
    elif action == "wait":
        time.sleep(action_data.get("seconds",2))
        return {"ok": True, "action": "wait"}
    elif action == "done":
        return {"ok": True, "action": "done", "summary": action_data.get("summary","")}
    return {"error": "unknown"}

def learn_shortcut(pattern, keys, context=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, count FROM shortcuts WHERE pattern=?", (pattern,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE shortcuts SET count=count+1 WHERE id=?", (row[0],))
    else:
        c.execute("INSERT INTO shortcuts (pattern, keys, context, learned) VALUES (?,?,?,?)", (pattern, keys, context, datetime.now().isoformat()))
    conn.commit(); conn.close()

def learn_correction(task, wrong, correct, context=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO corrections (task, wrong_action, correct_action, context, learned) VALUES (?,?,?,?,?)", (task, json.dumps(wrong), json.dumps(correct), context, datetime.now().isoformat()))
    conn.commit(); conn.close()

def talk_to_service(name, endpoint, data=None):
    url = SERVICES.get(name)
    if not url: return {"error": f"Unknown: {name}"}
    try:
        full = f"{url}{endpoint}"
        if data:
            r = requests.post(full, json=data, timeout=10)
        else:
            r = requests.get(full, timeout=10)
        return r.json() if "json" in r.headers.get("content-type","") else {"status": r.status_code}
    except Exception as e:
        return {"error": str(e)}

def get_all_services_status():
    results = {}
    for name, url in SERVICES.items():
        try:
            r = requests.get(f"{url}/health", timeout=3)
            results[name] = {"online": r.status_code == 200}
        except:
            try:
                r = requests.get(url, timeout=3)
                results[name] = {"online": r.status_code < 500}
            except:
                results[name] = {"online": False}
    return results

recording = {"active": False, "actions": [], "name": ""}

class TaskRequest(BaseModel):
    task: str
    max_steps: int = 15
    auto_plan: bool = True

class ExecRequest(BaseModel):
    action: str
    x: int = 0
    y: int = 0
    text: str = ""
    key: str = ""
    keys: list = []
    button: str = "left"
    amount: int = -3
    description: str = ""

class CorrectionRequest(BaseModel):
    task: str
    wrong_action: dict
    correct_action: dict

class RecordRequest(BaseModel):
    name: str
    actions: list = []

class ServiceRequest(BaseModel):
    service: str
    endpoint: str = ""
    data: dict = None

@app.post("/api/task")
async def run_task(req: TaskRequest):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    screenshot = take_screenshot()
    ocr_text = ocr_screen() if screenshot else None
    plan = make_plan(req.task, screenshot, ocr_text) if req.auto_plan else [req.task]
    c.execute("INSERT INTO tasks (task, plan, steps, status, created, corrections) VALUES (?,?,?,?,?,?)",
              (req.task, json.dumps(plan), "[]", "running", datetime.now().isoformat(), "[]"))
    conn.commit()
    task_id = c.lastrowid
    conn.close()
    steps = []
    history = []
    for step in range(req.max_steps):
        screenshot = take_screenshot()
        if not screenshot:
            return {"error": "pyautgui niet geinstalleerd"}
        ocr_text = ocr_screen()
        action = analyze_screen_vision(req.task, screenshot, ocr_text, history)
        action["step"] = step + 1
        steps.append({"step": step+1, "action": action, "plan": plan[min(step, len(plan)-1)] if plan else ""})
        dangerous, reason = is_dangerous(action)
        if dangerous:
            steps[-1]["blocked"] = True
            steps[-1]["block_reason"] = reason
            break
        result = execute_action(action)
        steps[-1]["result"] = result
        history.append(action)
        if recording["active"]:
            recording["actions"].append(action)
        if action.get("action") == "done":
            break
        time.sleep(1)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tasks SET steps=?, status='completed', completed=? WHERE id=?",
              (json.dumps(steps), datetime.now().isoformat(), task_id))
    conn.commit(); conn.close()
    return {"task_id": task_id, "task": req.task, "plan": plan, "steps": steps, "total_steps": len(steps)}

@app.post("/api/screenshot")
async def screenshot():
    s = take_screenshot()
    return {"screenshot": s} if s else {"error": "no pyautogui"}

@app.get("/api/ocr")
async def get_ocr():
    return {"text": ocr_screen() or "niet beschikbaar"}

@app.post("/api/elements")
async def get_elements():
    s = take_screenshot()
    return {"elements": detect_elements(s)} if s else {"error": "no screenshot"}

@app.post("/api/exec")
async def exec_action(req: ExecRequest):
    ad = {"action": req.action, "x": req.x, "y": req.y, "text": req.text, "key": req.key, "keys": req.keys, "button": req.button, "description": req.description}
    dangerous, reason = is_dangerous(ad)
    if dangerous:
        return {"blocked": True, "reason": reason}
    if recording["active"]:
        recording["actions"].append(ad)
    return execute_action(ad)

@app.post("/api/plan")
async def get_plan(req: TaskRequest):
    screenshot = take_screenshot()
    ocr_text = ocr_screen() if screenshot else None
    return {"task": req.task, "plan": make_plan(req.task, screenshot, ocr_text)}

@app.post("/api/correction")
async def add_correction(req: CorrectionRequest):
    learn_correction(req.task, req.wrong_action, req.correct_action)
    return {"ok": True, "message": "Correctie opgeslagen"}

@app.get("/api/corrections")
async def list_corrections():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, task, wrong_action, correct_action, learned FROM corrections ORDER BY id DESC LIMIT 20")
    items = c.fetchall(); conn.close()
    return {"corrections": [{"id": i[0], "task": i[1], "wrong": i[2], "correct": i[3], "learned": i[4]} for i in items]}

@app.get("/api/shortcuts")
async def get_shortcuts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT pattern, keys, context, count, learned FROM shortcuts ORDER BY count DESC LIMIT 30")
    items = c.fetchall(); conn.close()
    return {"shortcuts": [{"pattern": s[0], "keys": s[1], "context": s[2], "count": s[3], "learned": s[4]} for s in items]}

@app.get("/api/tasks")
async def get_tasks():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, task, plan, status, created, completed FROM tasks ORDER BY id DESC LIMIT 20")
    items = c.fetchall(); conn.close()
    return {"tasks": [{"id": t[0], "task": t[1], "plan": t[2], "status": t[3], "created": t[4], "completed": t[5]} for t in items]}

@app.post("/api/record/start")
async def record_start(req: RecordRequest):
    recording["active"] = True
    recording["name"] = req.name
    recording["actions"] = []
    return {"ok": True, "message": f"Opname gestart: {req.name}"}

@app.post("/api/record/stop")
async def record_stop():
    recording["active"] = False
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO recordings (name, actions, created) VALUES (?,?,?)", (recording["name"], json.dumps(recording["actions"]), datetime.now().isoformat()))
    conn.commit(); conn.close()
    return {"ok": True, "name": recording["name"], "count": len(recording["actions"])}

@app.post("/api/record/play/{rid}")
async def record_play(rid: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, actions FROM recordings WHERE id=?", (rid,))
    row = c.fetchone(); conn.close()
    if not row: return {"error": "niet gevonden"}
    actions = json.loads(row[1])
    results = []
    for a in actions:
        results.append(execute_action(a))
        time.sleep(0.5)
    return {"name": row[0], "played": len(actions), "results": results}

@app.get("/api/recordings")
async def list_recordings():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, created FROM recordings ORDER BY id DESC")
    items = c.fetchall(); conn.close()
    return {"recordings": [{"id": r[0], "name": r[1], "created": r[2]} for r in items]}

@app.get("/api/templates")
async def get_templates():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, description, category FROM templates ORDER BY category")
    items = c.fetchall(); conn.close()
    return {"templates": [{"id": t[0], "name": t[1], "description": t[2], "category": t[3]} for t in items]}

@app.post("/api/templates/exec/{tid}")
async def exec_template(tid: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, steps FROM templates WHERE id=?", (tid,))
    row = c.fetchone(); conn.close()
    if not row: return {"error": "niet gevonden"}
    steps = json.loads(row[1])
    results = []
    for s in steps:
        results.append(execute_action(s))
        time.sleep(0.5)
    return {"template": row[0], "executed": len(steps), "results": results}

@app.get("/api/services")
async def list_services():
    return {"services": SERVICES, "count": len(SERVICES)}

@app.post("/api/service")
async def call_service(req: ServiceRequest):
    return talk_to_service(req.service, req.endpoint, req.data)

@app.get("/api/services/status")
async def services_status():
    return get_all_services_status()

@app.get("/health")
async def health():
    try:
        import pyautogui
        return {"status": "ok", "version": "2.0", "screen": str(get_screen_size()), "pyautogui": True, "vision": VISION_MODEL, "text": TEXT_MODEL, "services": len(SERVICES)}
    except ImportError:
        return {"status": "ok", "version": "2.0", "pyautogui": False}

@app.get("/")
async def root():
    ui_path = os.path.join(os.path.dirname(__file__), "computer_use_ui.html")
    if os.path.exists(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<html><body><h1>Stay4S Computer-Use v2</h1><p>UI file not found. Place computer_use_ui.html next to this script.</p></body></html>")

if __name__ == "__main__":
    print("Stay4S Computer-Use Agent v2 -- Sterker dan Droid")
    print(f"Vision: {VISION_MODEL} | Text: {TEXT_MODEL}")
    print(f"Ollama: {OLLAMA_URL} | Services: {len(SERVICES)}")
    print("Starting on port 8080...")
    uvicorn.run(app, host="0.0.0.0", port=8080)




