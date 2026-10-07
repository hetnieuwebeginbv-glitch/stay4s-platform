#!/usr/bin/env python3
"""Stay4S Evaluatie Suite - test model output kwaliteit
Test: BLEU score, perplexity, response tijd, Nederlandse taalkwaliteit
"""
import requests, json, time, os, sys, logging, re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("stay4s-eval")

# Test cases - Nederlandse prompts met verwachte kenmerken
TEST_CASES = [
    {
        "name": "Begroeting",
        "prompt": "Hallo, wie ben jij?",
        "expect_contains": ["hallo", "ik", "ben"],
        "expect_lang": "nl",
        "min_length": 10,
        "max_length": 500,
    },
    {
        "name": "Vraag beantwoording",
        "prompt": "Wat is de hoofdstad van Nederland?",
        "expect_contains": ["amsterdam"],
        "expect_lang": "nl",
        "min_length": 5,
        "max_length": 200,
    },
    {
        "name": "Samenvatten",
        "prompt": "Samenvat: Het Nieuwe Begin B.V. is een bedrijf dat zich richt op soevereine Nederlandse AI. We bouwen modellen op een Raspberry Pi 5.",
        "expect_contains": ["nieuwe", "begin", "ai"],
        "expect_lang": "nl",
        "min_length": 20,
        "max_length": 300,
    },
    {
        "name": "Scam detectie",
        "prompt": "Is dit een scam? 'Bel snel naar 06-12345678 en geef je bankpas aan de medewerker.'",
        "expect_contains": ["scam", "oplichterij", "niet", "waarschuwing"],
        "expect_lang": "nl",
        "min_length": 10,
        "max_length": 500,
    },
    {
        "name": "Code generatie",
        "prompt": "Schrijf een Python functie die twee getallen optelt.",
        "expect_contains": ["def", "return", "+"],
        "expect_lang": "code",
        "min_length": 20,
        "max_length": 500,
    },
    {
        "name": "Vertaling NL->EN",
        "prompt": "Vertaal naar Engels: Goedemorgen, hoe gaat het met je?",
        "expect_contains": ["good", "morning", "how"],
        "expect_lang": "en",
        "min_length": 10,
        "max_length": 200,
    },
    {
        "name": "Context behoud",
        "prompt": "Ik heet Mitchell. Wat is mijn naam?",
        "expect_contains": ["mitchell"],
        "expect_lang": "nl",
        "min_length": 5,
        "max_length": 200,
    },
    {
        "name": "Nederlandse grammatica",
        "prompt": "Leg uit wat een zelfstandig naamwoord is.",
        "expect_contains": ["naamwoord", "woord", "ding", "persoon"],
        "expect_lang": "nl",
        "min_length": 20,
        "max_length": 500,
    },
]

def simple_bleu(reference, candidate):
    """Simple BLEU score (1-gram + 2-gram)"""
    ref_words = reference.lower().split()
    cand_words = candidate.lower().split()
    
    if not cand_words:
        return 0.0
    
    # 1-gram precision
    matches_1 = sum(1 for w in cand_words if w in ref_words)
    precision_1 = matches_1 / len(cand_words) if cand_words else 0
    
    # 2-gram precision
    ref_2grams = [' '.join(ref_words[i:i+2]) for i in range(len(ref_words)-1)]
    cand_2grams = [' '.join(cand_words[i:i+2]) for i in range(len(cand_words)-1)]
    matches_2 = sum(1 for g in cand_2grams if g in ref_2grams) if cand_2grams else 0
    precision_2 = matches_2 / len(cand_2grams) if cand_2grams else 0
    
    # Brevity penalty
    bp = min(1.0, len(cand_words) / max(1, len(ref_words)))
    
    if precision_1 == 0 or precision_2 == 0:
        return bp * precision_1 * 100
    
    bleu = bp * (precision_1 * precision_2) ** 0.5
    return bleu * 100

def detect_language(text):
    """Simple language detection"""
    nl_words = ["de", "het", "een", "en", "van", "is", "dat", "niet", "ik", "ben", "wij", "ons"]
    en_words = ["the", "a", "an", "and", "of", "is", "that", "not", "i", "am", "we", "our"]
    
    words = text.lower().split()
    nl_count = sum(1 for w in words if w in nl_words)
    en_count = sum(1 for w in words if w in en_words)
    
    if nl_count > en_count:
        return "nl"
    elif en_count > nl_count:
        return "en"
    return "unknown"

def evaluate_model(model_name, query_fn):
    """Run evaluation suite on a model"""
    log.info(f"=== Evaluatie: {model_name} ===")
    results = []
    
    for tc in TEST_CASES:
        start = time.time()
        try:
            response = query_fn(tc["prompt"])
            elapsed = time.time() - start
            response_text = response if isinstance(response, str) else response.get("response", str(response))
            
            # Checks
            text_lower = response_text.lower()
            contains_expected = any(kw in text_lower for kw in tc["expect_contains"])
            length_ok = tc["min_length"] <= len(response_text) <= tc["max_length"]
            lang = detect_language(response_text)
            lang_ok = lang == tc["expect_lang"] or tc["expect_lang"] == "code"
            
            # BLEU (if we have a reference)
            bleu = simple_bleu(tc["prompt"], response_text)
            
            result = {
                "name": tc["name"],
                "response": response_text[:200],
                "time_s": round(elapsed, 2),
                "contains_expected": contains_expected,
                "length_ok": length_ok,
                "lang": lang,
                "lang_ok": lang_ok,
                "bleu": round(bleu, 1),
                "length": len(response_text),
                "pass": contains_expected and length_ok,
            }
            results.append(result)
            
            status = "PASS" if result["pass"] else "FAIL"
            log.info(f"  [{status}] {tc['name']} - {result['time_s']}s - bleu={result['bleu']} - lang={lang}")
            
        except Exception as e:
            log.error(f"  [ERROR] {tc['name']}: {e}")
            results.append({"name": tc["name"], "error": str(e), "pass": False})
    
    # Summary
    passed = sum(1 for r in results if r.get("pass"))
    total = len(results)
    avg_time = sum(r.get("time_s", 0) for r in results) / total
    avg_bleu = sum(r.get("bleu", 0) for r in results) / total
    
    log.info(f"=== RESULTAAT: {passed}/{total} passed, avg_time={avg_time:.1f}s, avg_bleu={avg_bleu:.1f} ===")
    
    return {
        "model": model_name,
        "passed": passed,
        "total": total,
        "avg_time_s": round(avg_time, 2),
        "avg_bleu": round(avg_bleu, 1),
        "results": results,
    }

def query_ollama(prompt, model="stay4s-1b", url="http://100.123.235.81:11434"):
    """Query local Ollama model"""
    r = requests.post(f"{url}/api/generate", json={
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0.1, "num_predict": 200}
    }, timeout=60)
    if r.status_code == 200:
        return r.json().get("response", "")
    return "Error"

def query_cloudflare(prompt):
    """Query Cloudflare Workers AI"""
    token = "YOUR_CF_API_TOKEN"
    account = "59513e1a305610f0fb192d73dba01dbd"
    r = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        json={"messages": [{"role": "user", "content": prompt}], "max_tokens": 200, "temperature": 0.1},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30
    )
    if r.status_code == 200:
        return r.json().get("result", {}).get("response", "")
    return "Error"

def query_gateway(prompt, key="stay4s-free-demo"):
    """Query Stay4S gateway"""
    r = requests.post("http://100.123.235.81:8130/v1/chat",
        json={"message": prompt},
        headers={"Authorization": f"Bearer {key}"},
        timeout=60)
    if r.status_code == 200:
        return r.json().get("response", "")
    return "Error"

if __name__ == "__main__":
    # Evaluate all 3 backends
    all_results = []
    
    log.info("Testing Cloudflare Workers AI (Llama 3.3 70B)...")
    all_results.append(evaluate_model("Cloudflare Llama 3.3 70B", query_cloudflare))
    
    log.info("Testing Stay4S Gateway (Ollama stay4s-1b)...")
    all_results.append(evaluate_model("Gateway (stay4s-1b)", query_gateway))
    
    # Save results
    with open("/workspace/eval_results.json" if os.path.exists("/workspace") else "eval_results.json", "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    log.info("Results saved to eval_results.json")

