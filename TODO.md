# STAY4S — TO-DO LIJST
> Twee kolommen: wat alleen JIJ kunt doen (fysiek/accounts/beslissingen) en wat de AI doet.
> Ideeën staan in IDEEEN_EN_BACKLOG.md — dit zijn ACTIEVE taken.
> Laatst bijgewerkt: 2026-10-17 (Droid)

## JIJ (gebruiker)
| # | Taak | Waarom | Status |
|---|------|--------|--------|
| U-1 | 2e Pi fysiek checken: stroom aan? kabel of WiFi? lampjes? | hij is onzichtbaar op het netwerk; zonder dit kan niemand hem herstellen | open |
| U-2 | USB-kabel dataschijf (usb4) vervangen of stevig herplaatsen, evt. gevoede hub | oorzaak incident 17-10; anders gebeurt het weer | open — NA RUIL: zeg "kabel vervangen", Droid doet 10-min dmesg-bewaking + stresstest |
| U-3 | OpenCode herstellen: nieuwe API-key + tegoed | Droid installeerde key, gebruiker waardeerde tegoed op, end-to-end test OK ("WERKT") | **DONE 17-10** |
| U-4 | Beslissen: RunPod wel/niet gebruiken (key is 401) | blokkeert serverless model-hosting | open |
| U-5 | Mollie live-key regelen (mollie.com dashboard) | blokkeert echte betalingen / subscribe-flow | open |
| U-6 | Beslissen: mag Droid subdomain-bundeling 45->8 doorvoeren | wacht op jouw OK na voorstel | open |

## AI (Droid nu; OpenCode na herstel)
| # | Taak | Eigenaar | Status |
|---|------|----------|--------|
| A-1 | Groot-model (235M) training bewaken, daarna reus starten | Droid | LOOPT |
| A-2 | Na training: beste checkpoint -> GGUF -> Ollama op Pi | Droid | wacht op A-1 |
| A-3 | Voorstel subdomain-bundeling schrijven (BESLUIT_... in inbox) | Droid | open |
| A-4 | Security headers Cloudflare (CSP e.a.) | Droid | open (T4) |
| A-5 | video.stay4s.com (530) herstellen | Droid | open (T3) |
| A-6 | Spiegel DBs dagelijks naar SD + storage-monitor elke 5 min | Droid | **DONE 17-10** (db_mirror.sh 03:30 + storage_monitor.sh */5, quick_check op 3 DBs ok) |
| A-7 | Gateway 8130 publiek-voorstel (api. -> gateway ipv LiteLLM) | Droid | open |
| A-8 | WhatsApp /chat contract documenteren in API-docs | OpenCode/Droid | gedaan-in-rapport, docs open |
| A-9 | Sandbox-koppeling: terminal-dienst via stay4s-sandbox:1.0 | OpenCode | wacht op U-3 |
| A-10 | systemd hardening overige diensten (nexus-plugins was 9.6->1.7) | OpenCode | wacht op U-3 |

## Regels
- Idee? -> IDEEEN_EN_BACKLOG.md. Actieve taak? -> hier.
- Voltooide taken: status -> DONE met datum, niet weggooien (historie).
- Wijzigingen via de inbox-documenten; dit bestand is de enige bron.





