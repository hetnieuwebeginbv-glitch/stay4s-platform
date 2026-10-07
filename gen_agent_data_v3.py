#!/usr/bin/env python3
"""Stay4S Agent Training Data Generator v3 - 50K records"""
import json, random, os, time
from datetime import datetime

TOOLS = [
    {"name": "search_web", "desc": "Search the web for information", "params": ["query"]},
    {"name": "send_email", "desc": "Send an email to someone", "params": ["to", "subject", "body"]},
    {"name": "create_file", "desc": "Create a new file", "params": ["path", "content"]},
    {"name": "read_file", "desc": "Read a file", "params": ["path"]},
    {"name": "run_command", "desc": "Run a shell command", "params": ["command"]},
    {"name": "translate", "desc": "Translate text between languages", "params": ["text", "from", "to"]},
    {"name": "summarize", "desc": "Summarize a long text", "params": ["text"]},
    {"name": "scan_scam", "desc": "Scan a message for scam patterns", "params": ["message"]},
    {"name": "schedule_task", "desc": "Schedule a task for later", "params": ["task", "time"]},
    {"name": "generate_code", "desc": "Generate code from description", "params": ["language", "description"]},
    {"name": "analyze_sentiment", "desc": "Analyze sentiment of text", "params": ["text"]},
    {"name": "extract_entities", "desc": "Extract named entities from text", "params": ["text"]},
    {"name": "browse_url", "desc": "Browse a URL and extract content", "params": ["url"]},
    {"name": "compare_documents", "desc": "Compare two documents", "params": ["doc1", "doc2"]},
    {"name": "generate_report", "desc": "Generate a report from data", "params": ["data", "format"]},
]

DUTCH_TASKS = [
    "Zoek informatie over de nieuwste AI-regelgeving in Nederland",
    "Stuur een email naar de klant over de levering van morgen",
    "Maak een bestand aan met de meeting notulen",
    "Lees het rapport en geef een samenvatting",
    "Vertaal deze tekst van Engels naar Nederlands",
    "Scan dit bericht voor phishing pogingen",
    "Plan een afspraak voor volgende week dinsdag",
    "Genereer Python code voor een web scraper",
    "Analyseer het sentiment van deze klantenreview",
    "Haal alle bedrijfsnamen uit deze tekst",
    "Bekijk de website van de concurrent en haal prijzen op",
    "Vergelijk twee contracten en vind de verschillen",
    "Maak een rapport van de verkoopdata van Q3",
    "Zoek naar goedkope cloud providers in Europa",
    "Stuur een factuur naar de klant",
    "Maak een backup van de database",
    "Controleer de server status en rapporteer problemen",
    "Genereer een nieuwsbrief voor de abonnees",
    "Vertaal de website content naar Duits",
    "Scan een reeks emails voor scam patronen",
    "Plan een wekelijkse rapportage automatisering",
    "Genereer een API documentatie pagina",
    "Analyseer de sentiment trends over een maand",
    "Extract alle adressen uit een CSV bestand",
    "Bekijk de concurrent website en vergelijk features",
    "Maak een financieel overzicht rapport",
    "Zoek naar subsidies voor AI innovatie in Nederland",
    "Stuur een herinnering naar klanten met openstaande facturen",
    "Maak een klantenservice script voor WhatsApp",
    "Genereer een beveiligingsaudit rapport",
]

ENGLISH_TASKS = [
    "Search for the latest AI regulations in Europe",
    "Send an email to the customer about tomorrow's delivery",
    "Create a file with the meeting minutes",
    "Read the report and provide a summary",
    "Translate this text from Dutch to English",
    "Scan this message for phishing attempts",
    "Schedule an appointment for next Tuesday",
    "Generate Python code for a web scraper",
    "Analyze the sentiment of these customer reviews",
    "Extract all company names from this text",
    "Browse the competitor website and extract prices",
    "Compare two contracts and find differences",
    "Generate a report from Q3 sales data",
    "Search for affordable cloud providers in Europe",
    "Send an invoice to the customer",
    "Create a database backup",
    "Check server status and report issues",
    "Generate a newsletter for subscribers",
    "Translate website content to German",
    "Scan a batch of emails for scam patterns",
    "Schedule a weekly reporting automation",
    "Generate an API documentation page",
    "Analyze sentiment trends over a month",
    "Extract all addresses from a CSV file",
    "Browse competitor website and compare features",
    "Create a financial overview report",
    "Search for AI innovation grants in Netherlands",
    "Send a reminder to customers with outstanding invoices",
    "Create a customer service script for WhatsApp",
    "Generate a security audit report",
]

def gen_record(idx, lang):
    if lang == "nl":
        task = random.choice(DUTCH_TASKS)
        sys_msg = "Je bent Stay4S AI, een Nederlandse AI assistent. Je helpt de gebruiker door de juiste tools te kiezen en te gebruiken."
    else:
        task = random.choice(ENGLISH_TASKS)
        sys_msg = "You are Stay4S AI, a helpful AI assistant. You help the user by selecting and using the right tools."
    
    num_tools = random.randint(1, 4)
    selected = random.sample(TOOLS, min(num_tools, len(TOOLS)))
    
    tools_def = [{"type": "function", "function": {"name": t["name"], "description": t["desc"], "parameters": {"type": "object", "properties": {p: {"type": "string"} for p in t["params"]}, "required": t["params"]}}} for t in selected]
    
    # Generate assistant response with tool call
    tool = random.choice(selected)
    params = {}
    for p in tool["params"]:
        if p == "query": params[p] = task.lower().replace("zoek naar", "").replace("search for", "").strip()
        elif p == "to": params[p] = "klant@example.com" if lang == "nl" else "customer@example.com"
        elif p == "subject": params[p] = "Belangrijk bericht" if lang == "nl" else "Important message"
        elif p == "body": params[p] = task
        elif p == "path": params[p] = f"/tmp/file_{idx}.txt"
        elif p == "content": params[p] = f"Generated content for task {idx}"
        elif p == "command": params[p] = "ls -la /opt/stay4s/"
        elif p == "text": params[p] = task
        elif p == "from": params[p] = "nl" if lang == "nl" else "en"
        elif p == "to": params[p] = "en" if lang == "nl" else "nl"
        elif p == "message": params[p] = task
        elif p == "task": params[p] = task
        elif p == "time": params[p] = "tomorrow 10:00"
        elif p == "language": params[p] = random.choice(["python", "javascript", "kotlin", "bash"])
        elif p == "description": params[p] = task
        elif p == "url": params[p] = "https://example.com"
        elif p == "doc1": params[p] = "Document 1 content"
        elif p == "doc2": params[p] = "Document 2 content"
        elif p == "data": params[p] = '{"sales": 125000, "costs": 89000}'
        elif p == "format": params[p] = random.choice(["pdf", "html", "json", "csv"])
        else: params[p] = f"value_{idx}"
    
    assistant_tool_call = [{"id": f"call_{idx}", "type": "function", "function": {"name": tool["name"], "arguments": json.dumps(params)}}]
    
    # Tool result
    tool_result = json.dumps({"success": True, "result": f"Tool {tool['name']} executed successfully for: {task}"})
    
    # Final assistant response
    if lang == "nl":
        final = f"Ik heb de taak uitgevoerd met behulp van de {tool['name']} tool. Het resultaat is succesvol verwerkt."
    else:
        final = f"I have completed the task using the {tool['name']} tool. The result has been processed successfully."
    
    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": task},
        {"role": "assistant", "content": None, "tool_calls": assistant_tool_call},
        {"role": "tool", "tool_call_id": f"call_{idx}", "content": tool_result},
        {"role": "assistant", "content": final}
    ]
    
    return {"messages": messages, "tools": tools_def}

records = []
for i in range(50000):
    lang = "nl" if random.random() > 0.4 else "en"
    records.append(gen_record(i, lang))

outpath = "/mnt/usb4/training_data/agent_training_50k.jsonl"
os.makedirs(os.path.dirname(outpath), exist_ok=True)
with open(outpath, "w") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"Generated {len(records)} agent training records at {outpath}")
print(f"File size: {os.path.getsize(outpath) / 1024 / 1024:.1f} MB")
