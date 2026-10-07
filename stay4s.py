"""
Stay4S Python SDK - 1 file, requests-based
pip install requests (enige dependency)

Gebruik:
    from stay4s import Stay4S
    api = Stay4S("jouw-api-key")
    antwoord = api.chat("Hallo, wie ben jij?")
    scan = api.scan("Bel snel naar 06-12345678 en geef je bankpas")
    vertaling = api.translate("Hello world", target="en")
"""

import requests, json

class Stay4S:
    def __init__(self, api_key, base_url="http://api.stay4s.com/v1", api_key_demo="stay4s-free-demo"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    def chat(self, message, system="", history=None):
        r = requests.post(f"{self.base_url}/chat", headers=self.headers, json={
            "message": message, "system": system, "history": history or []
        }, timeout=60)
        r.raise_for_status()
        return r.json()
    
    def scan(self, text):
        r = requests.post(f"{self.base_url}/scan", headers=self.headers, json={
            "text": text
        }, timeout=30)
        r.raise_for_status()
        return r.json()
    
    def translate(self, text, source="nl", target="en"):
        r = requests.post(f"{self.base_url}/translate", headers=self.headers, json={
            "text": text, "source_lang": source, "target_lang": target
        }, timeout=30)
        r.raise_for_status()
        return r.json()
    
    def summarize(self, text, format="bullet"):
        r = requests.post(f"{self.base_url}/summarize", headers=self.headers, json={
            "text": text, "format": format
        }, timeout=30)
        r.raise_for_status()
        return r.json()
    
    def search(self, query, limit=5):
        r = requests.post(f"{self.base_url}/search", headers=self.headers, json={
            "query": query, "limit": limit
        }, timeout=30)
        r.raise_for_status()
        return r.json()
    
    def code(self, prompt, language="python"):
        r = requests.post(f"{self.base_url}/code", headers=self.headers, json={
            "prompt": prompt, "language": language
        }, timeout=60)
        r.raise_for_status()
        return r.json()
    
    def email(self, topic, tone="formeel", recipient=""):
        r = requests.post(f"{self.base_url}/email", headers=self.headers, json={
            "topic": topic, "tone": tone, "recipient": recipient
        }, timeout=30)
        r.raise_for_status()
        return r.json()
    
    def content(self, topic, type="blog", length="medium"):
        r = requests.post(f"{self.base_url}/content", headers=self.headers, json={
            "topic": topic, "type": type, "length": length
        }, timeout=30)
        r.raise_for_status()
        return r.json()
    
    def agents(self, task, agent="default"):
        r = requests.post(f"{self.base_url}/agents", headers=self.headers, json={
            "task": task, "agent": agent
        }, timeout=120)
        r.raise_for_status()
        return r.json()
    
    def usage(self):
        r = requests.get(f"{self.base_url}/usage", headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()
    
    def health(self):
        r = requests.get(f"{self.base_url}/health", timeout=5)
        return r.json()

# Voorbeeld gebruik
if __name__ == "__main__":
    api = Stay4S("demo-key", "http://100.123.235.81:8130/v1")
    print("Health:", api.health())

