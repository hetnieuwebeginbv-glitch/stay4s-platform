#!/usr/bin/env python3
"""gen_usable_data_v2.py - Generate 25K high-quality Q&A records
Focus on stay4s-1b weaknesses: math, reasoning, code, Dutch, English"""

import json
import random
import os
from datetime import datetime

random.seed(42)

# ============ MATH DATA ============
math_templates = [
    {"prompt": "Hoeveel is 15 plus 27?", "response": "15 plus 27 is 42."},
    {"prompt": "Hoeveel is 100 min 37?", "response": "100 min 37 is 63."},
    {"prompt": "Hoeveel is 8 keer 9?", "response": "8 keer 9 is 72."},
    {"prompt": "Hoeveel is 144 gedeeld door 12?", "response": "144 gedeeld door 12 is 12."},
    {"prompt": "Hoeveel is 25 plus 38?", "response": "25 plus 38 is 63."},
    {"prompt": "Hoeveel is 200 min 89?", "response": "200 min 89 is 111."},
    {"prompt": "Hoeveel is 7 keer 8?", "response": "7 keer 8 is 56."},
    {"prompt": "Hoeveel is 81 gedeeld door 9?", "response": "81 gedeeld door 9 is 9."},
    {"prompt": "Hoeveel is 45 plus 55?", "response": "45 plus 55 is 100."},
    {"prompt": "Hoeveel is 1000 min 345?", "response": "1000 min 345 is 655."},
    {"prompt": "What is 15 plus 27?", "response": "15 plus 27 is 42."},
    {"prompt": "What is 100 minus 37?", "response": "100 minus 37 is 63."},
    {"prompt": "What is 8 times 9?", "response": "8 times 9 is 72."},
    {"prompt": "What is 144 divided by 12?", "response": "144 divided by 12 is 12."},
    {"prompt": "What is 25 plus 38?", "response": "25 plus 38 is 63."},
    {"prompt": "Wat is de helft van 50?", "response": "De helft van 50 is 25."},
    {"prompt": "Wat is 10% van 200?", "response": "10% van 200 is 20."},
    {"prompt": "Wat is de wortel van 64?", "response": "De wortel van 64 is 8."},
    {"prompt": "Wat is 3 tot de macht 4?", "response": "3 tot de macht 4 is 81."},
    {"prompt": "Hoeveel minuten in 3 uur?", "response": "3 uur is 180 minuten."},
]

# ============ REASONING DATA ============
reasoning_templates = [
    {"prompt": "Als het regent, wat heb je dan nodig?", "response": "Als het regent, heb je een paraplu of regenjas nodig om droog te blijven."},
    {"prompt": "Waarom gaat de zon onder in het westen?", "response": "De zon gaat onder in het westen omdat de aarde van west naar oost draait, dus de zon lijkt van oost naar west te bewegen."},
    {"prompt": "Als Jan 3 appels heeft en er 2 eet, hoeveel blijven er over?", "response": "Jan heeft 3 appels, eet er 2 op, dus 3 - 2 = 1 appel blijft over."},
    {"prompt": "Waarom is water belangrijk?", "response": "Water is belangrijk omdat het essentieel is voor alle leven. Mensen hebben water nodig voor hydratatie, planten om te groeien, en het speelt een rol in bijna alle biologische processen."},
    {"prompt": "Wat moet je doen als je verdwaald bent?", "response": "Als je verdwaald bent: 1. Blijf kalm. 2. Zoek een herkenningspunt. 3. Gebruik een kaart of GPS. 4. Vraag om directions. 5. Bel 112 als in gevaar."},
    {"prompt": "If Alice is taller than Bob and Bob is taller than Carol, who is shortest?", "response": "If Alice is taller than Bob and Bob is taller than Carol, then Carol is the shortest."},
    {"prompt": "Why do we need sleep?", "response": "We need sleep because it allows our brain to rest, consolidate memories, repair cells, and restore energy. Lack of sleep impairs concentration, mood, and health."},
    {"prompt": "Wat is het verschil tussen een hacker en een programmeur?", "response": "Een programmeur schrijft software. Een hacker gebruikt technische kennis om toegang te krijgen tot systemen, soms illegaal. Niet alle hackers zijn slecht - ethische hackers helpen beveiliging te verbeteren."},
    {"prompt": "Hoe werkt een scam bericht?", "response": "Een scam bericht werkt door: 1. Urgentie creeren (snel handelen!), 2. Een link met een valse site, 3. Inloggegevens of geld stelen, 4. Vaak neppe beloningen beloven. Herkenning: vreemde links, druk, te goed om waar te zijn."},
    {"prompt": "Wat is privacy en waarom is het belangrijk?", "response": "Privacy is het recht om te bepalen wie toegang heeft tot jouw persoonlijke gegevens. Het is belangrijk voor veiligheid, vrijheid, en bescherming tegen misbruik van je data."},
]

# ============ CODE DATA ============
code_templates = [
    {"prompt": "Schrijf een Python functie die twee getallen optelt.", "response": "```python\ndef tel_op(a, b):\n    return a + b\n```\nDeze functie neemt twee parameters a en b en geeft hun som terug."},
    {"prompt": "Schrijf een Python functie die controleert of een getal even is.", "response": "```python\ndef is_even(n):\n    return n % 2 == 0\n```\nDeze functie geeft True terug als het getal even is, anders False."},
    {"prompt": "Schrijf een Python functie die een string omkeert.", "response": "```python\ndef keer_om(s):\n    return s[::-1]\n```\nDeze functie gebruikt slicing met stap -1 om de string om te keren."},
    {"prompt": "Schrijf een Python functie die de grootste van drie getallen vindt.", "response": "```python\ndef grootste(a, b, c):\n    return max(a, b, c)\n```\nOf zonder max():\n```python\ndef grootste(a, b, c):\n    if a >= b and a >= c:\n        return a\n    elif b >= c:\n        return b\n    return c\n```"},
    {"prompt": "Schrijf een Python functie die telt hoeveel klinkers in een string zitten.", "response": "```python\ndef tel_klinkers(s):\n    klinkers = 'aeiouAEIOU'\n    return sum(1 for c in s if c in klinkers)\n```"},
    {"prompt": "Write a Python function to check if a string is a palindrome.", "response": "```python\ndef is_palindrome(s):\n    s = s.lower().replace(' ', '')\n    return s == s[::-1]\n```"},
    {"prompt": "Write a Python function to calculate factorial.", "response": "```python\ndef factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n```"},
    {"prompt": "Schrijf een Python klasse voor een eenvoudige rekenmachine.", "response": "```python\nclass Rekenmachine:\n    def optellen(self, a, b):\n        return a + b\n    def aftrekken(self, a, b):\n        return a - b\n    def vermenigvuldigen(self, a, b):\n        return a * b\n    def delen(self, a, b):\n        if b == 0:\n            return 'Fout: delen door nul'\n        return a / b\n```"},
    {"prompt": "Write a Python function to sort a list using bubble sort.", "response": "```python\ndef bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr\n```"},
    {"prompt": "Schrijf een Python functie die Fibonacci getallen berekent.", "response": "```python\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n+1):\n        a, b = b, a + b\n    return b\n```"},
]

# ============ DUTCH CONVERSATION ============
dutch_conv = [
    {"prompt": "Hallo, wie ben jij?", "response": "Hallo! Ik ben Stay4S, een Nederlandse AI-assistent. Ik kan je helpen met vragen, vertalingen, samenvattingen en meer. Waar kan ik je mee helpen?"},
    {"prompt": "Goedemorgen, hoe gaat het?", "response": "Goedemorgen! Het gaat goed met mij, bedankt voor de vraag. Ik ben altijd klaar om te helpen. Hoe gaat het met jou?"},
    {"prompt": "Wat kun je allemaal doen?", "response": "Ik kan je helpen met:\n1. Vragen beantwoorden in het Nederlands en Engels\n2. Teksten vertalen\n3. Samenvattingen maken\n4. Scam en phishing berichten herkennen\n5. Code schrijven\n6. Wiskunde problemen oplossen\n7. Advies geven\nWaar heb je hulp bij nodig?"},
    {"prompt": "Kun je Nederlands spreken?", "response": "Ja, ik spreek vloeiend Nederlands! Ik ben speciaal ontwikkeld voor Nederlandse gebruikers. Je kunt me alles in het Nederlands vragen."},
    {"prompt": "Wat is de hoofdstad van Nederland?", "response": "De hoofdstad van Nederland is Amsterdam. De regering zetelt echter in Den Haag."},
    {"prompt": "Vertel me over Amsterdam.", "response": "Amsterdam is de hoofdstad van Nederland met ongeveer 900.000 inwoners. Het staat bekend om zijn grachten, het Rijksmuseum, het Van Gogh Museum, en de liberale sfeer. De stad heeft een rijke handelsgeschiedenis en is een belangrijk financieel en cultureel centrum."},
    {"prompt": "Wat is een typisch Nederlands gerecht?", "response": "Enkele typische Nederlandse gerechten zijn: stamppot, hutspot, boerenkool, erwtensoep, pannenkoeken, stroopwafels, haring, en bitterballen. Stamppot is waarschijnlijk het meest iconiek - aardappelen gepureerd met groenten zoals boerenkool of zuurkool."},
    {"prompt": "Hoe zeg je 'thank you' in het Nederlands?", "response": "'Thank you' zeg je in het Nederlands als 'dank je' (informeel) of 'dank u wel' (formeel)."},
    {"prompt": "Wat is het weer in Nederland?", "response": "Ik heb geen live weergegevens, maar het Nederlandse klimaat is gematigd met milde winters en koele zomers. Het regent regelmatig en de temperatuur varieert meestal tussen 0°C in winter en 25°C in zomer."},
    {"prompt": "Kun je me helpen met een scam bericht?", "response": "Ja, absoluut! Stuur het bericht naar me en ik zal het analyseren op verdachte tekens zoals:\n- Dringende taal (snel handelen)\n- Vreemde links\n- Vragen om persoonlijke gegevens\n- Te goede aanbiedingen\n- Onbekende afzenders\nPlak het bericht en ik beoordeel het voor je."},
]

# ============ ENGLISH CONVERSATION ============
english_conv = [
    {"prompt": "Hello, who are you?", "response": "Hello! I am Stay4S, an AI assistant built in the Netherlands. I can help you with questions, translations, summaries, scam detection, and more. How can I help you today?"},
    {"prompt": "What can you do?", "response": "I can help you with:\n1. Answering questions in Dutch and English\n2. Translating texts\n3. Summarizing content\n4. Detecting scam and phishing messages\n5. Writing code\n6. Solving math problems\n7. General advice\nWhat do you need help with?"},
    {"prompt": "Tell me about yourself.", "response": "I am Stay4S, an independent AI assistant. I was built to provide privacy-first AI services without relying on Big Tech. I run on local infrastructure and can speak both Dutch and English fluently."},
    {"prompt": "Can you translate Dutch to English?", "response": "Yes! I can translate between Dutch and English. Just send me the text you want translated and specify the target language."},
    {"prompt": "How do I stay safe online?", "response": "To stay safe online:\n1. Never click suspicious links\n2. Use strong, unique passwords\n3. Enable two-factor authentication\n4. Don't share personal information\n5. Verify sender identity\n6. Keep software updated\n7. Use a VPN on public WiFi\n8. Be skeptical of too-good offers"},
    {"prompt": "What is phishing?", "response": "Phishing is a cyber attack where scammers impersonate legitimate organizations to steal sensitive information like passwords, credit card numbers, or personal data. They typically use fake emails, messages, or websites. Always verify the sender and never click suspicious links."},
    {"prompt": "Write a short poem about technology.", "response": "In circuits bright and code so clean,\nA digital world that's barely seen,\nWires whisper, electrons flow,\nIn silicon dreams, the future grows.\nFrom humble chips to clouds above,\nTechnology weaves with care and love."},
    {"prompt": "Explain machine learning simply.", "response": "Machine learning is like teaching a computer by example. Instead of giving it exact rules, you show it lots of data and it finds patterns. Like how a child learns to recognize cats by seeing many cats, a computer learns from many examples. The more data it sees, the better it gets."},
    {"prompt": "What is the difference between AI and ML?", "response": "AI (Artificial Intelligence) is the broad concept of machines being able to carry out tasks smartly. ML (Machine Learning) is a specific approach where machines learn from data instead of being explicitly programmed. All ML is AI, but not all AI uses ML."},
    {"prompt": "Give me a healthy breakfast idea.", "response": "Here is a healthy breakfast: Greek yogurt with berries, a handful of walnuts, a drizzle of honey, and a slice of whole-grain toast with avocado. This gives you protein, healthy fats, fiber, and antioxidants to start your day right."},
]

# ============ TOOL USE DATA ============
tool_use = [
    {"prompt": "Ik wil een email vertalen naar Engels.", "response": '{"tool": "translate", "args": {"text": "je email tekst", "target": "en"}}\nIk kan je email naar het Engels vertalen. Plak de tekst en ik vertaal het voor je.'},
    {"prompt": "Kun je dit bericht controleren op scam?", "response": '{"tool": "scan", "args": {"message": "het bericht"}}\nJa, ik kan berichten controleren op scam en phishing. Stuur het bericht en ik analyseer het op verdachte tekens.'},
    {"prompt": "Ik wil een lange tekst samenvatten.", "response": '{"tool": "summarize", "args": {"text": "de lange tekst"}}\nJa, ik kan lange teksten samenvatten. Stuur de tekst en ik maak een korte samenvatting met de belangrijkste punten.'},
    {"prompt": "Can you help me write code?", "response": '{"tool": "code", "args": {"language": "python", "task": "beschrijving"}}\nYes! I can help you write code in Python, JavaScript, and more. Tell me what you want to build.'},
    {"prompt": "Ik heb hulp nodig bij wiskunde.", "response": '{"tool": "math", "args": {"problem": "het probleem"}}\nNatuurlijk! Ik kan je helpen met wiskunde. Stel je vraag en ik los het op.'},
]

# ============ GENERATE 25K RECORDS ============
templates = math_templates + reasoning_templates + code_templates + dutch_conv + english_conv + tool_use

records = []
for i in range(25000):
    tmpl = random.choice(templates)
    
    # Add variation
    if random.random() < 0.3:
        # Add system message
        record = {
            "id": i,
            "system": "Je bent Stay4S, een behulpzame Nederlandse AI-assistent. Beantwoord vragen duidelijk en correct.",
            "prompt": tmpl["prompt"],
            "response": tmpl["response"],
            "category": "math" if tmpl in math_templates else "reasoning" if tmpl in reasoning_templates else "code" if tmpl in code_templates else "dutch" if tmpl in dutch_conv else "english" if tmpl in english_conv else "tool_use",
            "timestamp": datetime.now().isoformat()
        }
    else:
        record = {
            "id": i,
            "prompt": tmpl["prompt"],
            "response": tmpl["response"],
            "category": "math" if tmpl in math_templates else "reasoning" if tmpl in reasoning_templates else "code" if tmpl in code_templates else "dutch" if tmpl in dutch_conv else "english" if tmpl in english_conv else "tool_use",
            "timestamp": datetime.now().isoformat()
        }
    records.append(record)

# Write to file
outfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usable_training_25k.jsonl")
with open(outfile, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# Stats
categories = {}
for r in records:
    c = r["category"]
    categories[c] = categories.get(c, 0) + 1

print(f"Generated {len(records)} records")
print(f"File: {outfile}")
print(f"Size: {os.path.getsize(outfile) / 1024 / 1024:.1f} MB")
print("Categories:")
for c, n in sorted(categories.items()):
    print(f"  {c}: {n}")
