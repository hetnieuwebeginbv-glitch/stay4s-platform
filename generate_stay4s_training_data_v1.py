#!/usr/bin/env python3
"""Generate a deterministic, synthetic 5,000-record Stay4S instruction dataset.

Output JSONL schema per line:
{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}

Records are synthetic examples, not sourced factual claims. Review/evaluate before training.
"""
from __future__ import annotations
import argparse, json, random
from pathlib import Path

SEED = 4052026
COUNTS = {"math": 2000, "reasoning": 1000, "code": 1000, "dutch": 500, "tool_use": 500}

def record(user: str, assistant: str) -> dict:
    return {"messages": [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]}

def build_records(seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    out: list[dict] = []
    # 2,000 math: exact arithmetic and transparent steps.
    for i in range(COUNTS["math"]):
        a, b = rng.randint(2, 999), rng.randint(2, 999)
        op = ("+", "-", "*", "//", "%")[i % 5]
        if op == "+": answer, expr = a + b, f"{a} + {b}"
        elif op == "-":
            if b > a: a, b = b, a
            answer, expr = a - b, f"{a} - {b}"
        elif op == "*": answer, expr = a * b, f"{a} × {b}"
        elif op == "//": answer, expr = a // b, f"{a} // {b}"
        else: answer, expr = a % b, f"{a} mod {b}"
        out.append(record(f"Bereken {expr}. Laat kort zien hoe je rekent.", f"{expr} = {answer}. Ik voer de bewerking uit en controleer het resultaat: {answer}."))
    # 1,000 reasoning: small, fully specified constraints; avoid external facts.
    for i in range(COUNTS["reasoning"]):
        x = rng.randint(1, 40); y = rng.randint(1, 40); z = x + y
        out.append(record(
            f"Een voorraad heeft {x} rode en {y} blauwe onderdelen. Er komen 3 onderdelen van elke kleur bij. Hoeveel zijn er dan in totaal? Leg uit.",
            f"Rood: {x}+3={x+3}. Blauw: {y}+3={y+3}. Totaal: {x+3}+{y+3}={z+6}. Er zijn dus {z+6} onderdelen."
        ))
    # 1,000 code: simple, safe programming exercises with expected behavior.
    langs = [
        ("Python", "Schrijf een functie die een lijst getallen optelt.", "def sum_numbers(values):\n    return sum(values)"),
        ("JavaScript", "Schrijf een functie die een lijst getallen optelt.", "function sumNumbers(values) {\n  return values.reduce((sum, value) => sum + value, 0);\n}"),
        ("Kotlin", "Schrijf een functie die een lijst Int-waarden optelt.", "fun sumNumbers(values: List<Int>): Int = values.sum()"),
        ("SQL", "Geef een query die aantallen per status telt voor tabel jobs.", "SELECT status, COUNT(*) AS total\nFROM jobs\nGROUP BY status;"),
        ("Python", "Schrijf een functie die controleert of een tekst leeg is na strip().", "def is_blank(value: str) -> bool:\n    return not value.strip()"),
    ]
    for i in range(COUNTS["code"]):
        lang, task, solution = langs[i % len(langs)]
        out.append(record(f"{task} Taal: {lang}. Geef alleen een eenvoudige implementatie en licht randgevallen kort toe.", solution + "\n\nControleer lege invoer en het verwachte retourtype."))
    # 500 Dutch language/help examples.
    dutch = [
        ("Leg uit wat tweefactorauthenticatie is.", "Tweefactorauthenticatie gebruikt twee verschillende bewijzen van identiteit, bijvoorbeeld een wachtwoord en een authenticator-app. Deel verificatiecodes nooit met anderen."),
        ("Herschrijf deze zin zakelijk: 'Ik heb het nog niet gedaan, komt later.'", "Ik heb dit nog niet afgerond en kom hier op een later moment op terug."),
        ("Hoe controleer ik een verdachte betaal-link?", "Open de link niet meteen. Controleer de volledige domeinnaam via een onafhankelijk kanaal, deel geen codes en neem bij twijfel rechtstreeks contact op met de organisatie."),
        ("Maak een korte checklist voor een veilige backup.", "1. Maak een versleutelde kopie. 2. Bewaar een tweede kopie op een andere locatie. 3. Beperk toegang. 4. Test herstel. 5. Documenteer datum en resultaat."),
        ("Leg API uit in eenvoudige Nederlandse taal.", "Een API is een afgesproken manier waarop software onderdelen gegevens of opdrachten met elkaar laat uitwisselen."),
    ]
    for i in range(COUNTS["dutch"]):
        q, a = dutch[i % len(dutch)]
        out.append(record(q, a))
    # 500 tool-use records: assistant emits a proposed tool call, not a claim it executed it.
    tools = [
        ("search_docs", {"query": "deployment health checks"}),
        ("get_service_status", {"service": "gateway"}),
        ("create_ticket", {"title": "Review API timeout", "priority": "P2"}),
        ("run_tests", {"suite": "gateway-contract", "mode": "read_only"}),
        ("get_model_info", {"model": "nomic-embed-text"}),
    ]
    for i in range(COUNTS["tool_use"]):
        name, args = tools[i % len(tools)]
        out.append(record(
            f"Welke tool-call past bij deze taak: {name.replace('_', ' ')}? Geef een JSON-object met tool en arguments; beweer niet dat de tool al is uitgevoerd.",
            json.dumps({"tool": name, "arguments": args, "execution_status": "not_executed"}, ensure_ascii=False, separators=(",", ":"))
        ))
    rng.shuffle(out)
    return out

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="stay4s_training_5000.jsonl")
    parser.add_argument("--manifest", default="stay4s_training_5000.manifest.json")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    rows = build_records(args.seed)
    if len(rows) != sum(COUNTS.values()) or any(set(x) != {"messages"} or len(x["messages"]) != 2 for x in rows):
        raise SystemExit("Dataset schema/count validation failed.")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest = {"dataset": out.name, "records": len(rows), "categories": COUNTS, "seed": args.seed, "format": "jsonl/messages(user,assistant)", "synthetic": True, "review_before_training": True}
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))

if __name__ == "__main__":
    main()
