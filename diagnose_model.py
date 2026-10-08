import json, urllib.request, time

def test_model(model, prompt, timeout=30):
    data = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
    try:
        start = time.time()
        resp = urllib.request.urlopen(req, timeout=timeout)
        elapsed = time.time() - start
        d = json.loads(resp.read())
        return d.get("response", "NONE"), elapsed
    except Exception as e:
        return f"ERROR: {e}", 0

tests = [
    ("Math 1", "Hoeveel is 15 plus 27? Geef alleen het getal."),
    ("Math 2", "Wat is 8 keer 7?"),
    ("Reasoning", "Als het regent, wat heb je dan nodig?"),
    ("Dutch", "Schrijf een korte zin over Amsterdam."),
    ("English", "What is the capital of France?"),
    ("Code", "Schrijf een Python functie die twee getallen optelt."),
    ("Identity", "Wie ben jij?"),
    ("Scam", "Is dit bericht een scam: Klik hier voor gratis geld!"),
]

print("=== STAY4S-1B MODEL DIAGNOSE ===")
print(f"Testing 8 questions...\n")

results = []
for name, prompt in tests:
    resp, t = test_model("stay4s-1b", prompt)
    status = "OK" if t > 0 and len(resp) > 5 and "ERROR" not in resp else "FAIL"
    print(f"[{status}] {name} ({t:.1f}s): {resp[:120]}")
    results.append((name, status, resp, t))
    print()

# Summary
ok = sum(1 for _, s, _, _ in results if s == "OK")
fail = sum(1 for _, s, _, _ in results if s == "FAIL")
avg_time = sum(t for _, _, _, t in results if t > 0) / max(1, sum(1 for _, _, _, t in results if t > 0))
print(f"=== SAMENVATTING ===")
print(f"Pass: {ok}/{len(tests)}")
print(f"Fail: {fail}/{len(tests)}")
print(f"Gem. tijd: {avg_time:.1f}s")
print(f"Conclusie: Model is {'BRUIKBAAR' if ok >= 6 else 'NOG IN TROUBLE'}")

# Also test stay4s-1b-dream
print(f"\n=== STAY4S-1B-DREAM TEST ===")
resp2, t2 = test_model("stay4s-1b-dream", "Wie ben jij?")
print(f"Dream ({t2:.1f}s): {resp2[:150]}")
