# MASTER PROMPT — Stay4S websites (voor een Droid-sessie)
# Gemaakt: 2026-10-20 door Droid. Kopieer dit hele document als startprompt.

## JOUW OPDRACHT
Je gaat verder met de commerciële websites van Stay4S (stay4s.nl / stay4s.com).
Werk autonoom, maar raak NOOIT iets anders op de Pi aan dan hieronder genoemd.

## TERREIN — alleen dit mag je aanraken
- Service: stay4s-landing.service (draait als Miesdevries, venv /opt/stay4s/scam/venv (Python 3.13.5 — let op: pdf-wheels lopen achter op 3.13))
- Map: /opt/stay4s/landing/ (landing_server.py, account_ext.py, mollie_ext.py, index.html, paginas/)
- Data: /opt/stay4s/data/ (site_accounts.db, site_secret, mollie.env)
- Poort: 8161 (intern), publiek via Cloudflare-tunnel: stay4s.nl + stay4s.com -> :8161
- SSH: ssh -i C:\Users\Gebruiker\.ssh\stay4pi_ed25519 Miesdevries@192.168.8.120

VERBODEN TERREIN (OpenCode-lane): alle andere ~60 services op de Pi.
Bekende DODE poorten (tunnelroutes die nergens heen gaan): 8088, 8085, 8888, 8200.
Er zijn GEEN poortconflicten — OpenCode heeft proces->unit gemeten: elke poort heeft exact 1 luisteraar
(4000=litellm, 4155=niets, 8099=consciousness-api, 8100=scam-shield, 8130=gateway-v3, 8144=keys).
Units LIEGEN in hun beschrijving over hun poort (scam-api zegt 8100 maar luistert op 8160) — vertrouw alleen gemeten sockets.

## HUIDIGE STAAT (alles live + getest op 2026-10-20)
- index.html homepage (footer met alle links, KvK 42190967, btw NL870112156B01)
- paginas/: aanbod (met Mollie-betaalknoppen EUR29/49/69), privacy, voorwaarden, cookies, moderatie, disclaimer
- account_ext.py: registreren/inloggen/uitloggen/dashboard incl. "Mijn bestellingen"
  (pbkdf2-200k, HMAC-sessiecookie 14 dagen, sqlite site_accounts.db)
- mollie_ext.py: /api/pay/create, /webhook, /mode, /return, /status
  Key uit /opt/stay4s/data/mollie.env (MOLLIE_API_KEY=test_... actief; MOLLIE_LIVE_KEY=access_... al opgeslagen)
  TESTMODE tot Mollie-profiel pfl_hfyELRoEZh "verified" is; automation stay4s-mollie-livegang-check
  (lokaal, dagelijks 08:30) flipt automatisch naar live. Controleer met: curl -s https://stay4s.nl/api/pay/mode

## REGELS (leergeld, neem ze over)
1. Voor ELKE wijziging op de Pi: backup met suffix .bak-<reden>-<yyyymmdd>
2. python3 -m py_compile vóór systemctl restart stay4s-landing
3. Na restart: curl lokaal (127.0.0.1:8161) ÉN publiek (stay4s.nl) verifiëren
4. PowerShell vermangt inline JSON/quotes -> ALTIJD payload- of scriptbestand schrijven, scp, dan "bash -s"
5. Bestanden voor bash altijd LF: -replace "`r`n","`n"
6. pgrep/pkill met [x]-patroon (anders schiet je je eigen ssh-sessie dood)
7. Geen secrets in code/git; alleen in /opt/stay4s/data/*.env (chmod 600)
8. K:-mirror bijhouden: K:\stay4s\clusters\site\ (index.html, landing_server.py, account_ext.py, mollie_ext.py, paginas/) — index.html NIET vergeten
9. Stijl: donker thema (#0a0e14 bg, #11161f kaart, #1e2632 rand, #e6e9ef tekst, #9aa4b2 zacht, #4da3ff accent, #3fd68f groen), Nederlands, system-ui

## BACKLOG (geprioriteerd)
1. Contactformulier (/contact) -> opslaan in sqlite + mailnotificatie (of webhook naar Pi-notifier 8107? eerst checken of die leeft)
2. E-mailbevestiging na betaling (webhook -> mail). Kies iets simpels; geen zware deps in de venv
3. /faq pagina (SEO + Mollie-vertrouwen)
4. Blog/nieuws-sectie (SEO, "wij trainen eigen NL-modellen"-verhaal; link lab.stay4s.nl)
5. Klant-portaal uitbreiden: diensten-tab koppelen aan echte provisioning (handmatig achter de schermen is ok)
6. Facturen: na status "betaald" PDF-factuur genereren (KvK/btw staan al op de site)
7. Privacy-vriendelijke statistieken (geen Google; simpel eigen tellertje of GoatCounter)
8. status.stay4s.nl of /status: uptime van landing + lab + api (simpele self-check pagina)
9. Toegankelijkheid: lang-attributen staan goed; check contrast + focus-states

## TRAININGSCONTEXT (niet jouw taak, wel handig om te noemen op de site)
- 3 runs op Vast.ai: xl 1,53B (iter ~9k/13k), Titaan MoE 1,46B/470M-actief (beter dan xl), titaan-dicht 470M
- lab.stay4s.nl toont live training (watcher dekt nu alleen box1; multi-box is backlog van hoofd-Droid)
- Verhaallijn voor de site: "Nederlands model, eigen hardware, jouw data blijft hier"

## KLAAR-DEFINITIE PER FEATURE
Werkt lokaal + publiek, backup gemaakt, K:-mirror bijgewerkt, STATUS_NU.md aangevuld,
geen nieuwe secrets in code, geen andere Pi-services aangeraakt.