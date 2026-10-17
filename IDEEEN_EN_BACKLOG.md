# STAY4S — IDEEEN & BACKLOG
> Eén parkeerplaats voor alle ideeën. Idee ≠ taak. Wordt pas een taak als de gebruiker zegt: "pak idee X".
> Laatst bijgewerkt: 2026-10-17 (Droid)

## Legenda
- Waarde: HOOG / MIDDEN / LAAG | Moeite: KLEIN / MIDDEN / GROOT
- Lane: Droid / OpenCode / gebruiker-fysiek

## Infrastructuur
| # | Idee | Waarde | Moeite | Lane | Opmerking |
|---|------|--------|--------|------|-----------|
| I-01 | Pi 5 booten van USB/NVMe ipv SD | MIDDEN | MIDDEN | Droid | geen SD-slijtage meer, sneller I/O; vereist downtime |
| I-02 | 2e Pi (8GB) als failover voor productie | HOOG | MIDDEN | Droid + gebruiker | eerst fysieke check (lampjes/kabel), dan SSH, dan kopie kritieke diensten |
| I-03 | Gevoede USB-hub / betere kabel dataschijf | HOOG | KLEIN | gebruiker-fysiek | structurele fix usb4-incident 17-10 |
| I-04 | Kritieke DB (commercial) ook op SD spiegelen | HOOG | KLEIN | Droid | cron-sync, beschermt tegen volgende schijf-crash |
| I-05 | HP Z400 als AOSP/ROM build-server | MIDDEN | MIDDEN | Droid | ROM-builds gratis ipv Vast-huur; eerst RAM/schijf checken |
| I-06 | Kali Linux als VM/live-USB op Z400 | LAAG | KLEIN | Droid | voor Scam-Shield B2B security-demo's |
| I-07 | mnt-usb3 fstab-regel: bevestigd verwijderd 17-10 | — | — | done | — |
| I-08 | Nieuwe 4TB externe schijf als Pi-dataopslag (vervangt stick-bos) | HOOG | MIDDEN | Droid + gebruiker | schijf komt 18-10; ext4, rsync-migratie usb4, fstab UUID, 5 min downtime |
| I-09 | K:-backups (7,8TB PC) spiegelen naar Pi 4TB (selectief) | MIDDEN | MIDDEN | Droid | echte redundantie: PC + Pi (+ evt. cloud) |
| I-10 | NVMe HAT + 500GB NVMe | HOOG | MIDDEN | gebruiker koopt, Droid installeert | PCIe direct ~800MB/s, booten van NVMe, geen USB-laag in kritiek pad; NVMe=OS/kritiek, 4TB=bulk/backup, SD=bootloader. LINKS: officiel pineboards.io - HatDrive! Top https://pineboards.io/products/hatdrive-top-nvme-2230-2242-gen-3-for-raspberry-pi-5 - Nano (past in officiele case) https://pineboards.io/products/hatdrive-nano-nvme-2230-2242-gen-3-for-raspberry-pi-5 - Bottom (grote 2280 SSD) https://pineboards.io/products/hatdrive-bottom-nvme-2280-gen-3-for-raspberry-pi-5 - docs docs.pineboards.io - NL-vriendelijk: welectron.com HatDrive! Top EUR22,90. SSD 2230/2242 500GB ~EUR45 (bv WD SN740) |

## Platform & Cloudflare (lane Droid, W3)
| # | Idee | Waarde | Moeite | Opmerking |
|---|------|--------|--------|-----------|
| P-01 | Subdomein-bundeling 45 -> 8 (redirects naar app.stay4s.com) | HOOG | MIDDEN | voorstel volgt via BESLUIT_SUBDOMEIN_BUNDELING; wacht op verkeerscijfers tunnel |
| P-02 | Security headers (CSP, X-Frame-Options etc.) | HOOG | KLEIN | T4; OpenCode had geen Transform Rules-rechten |
| P-03 | video.stay4s.com (530) herstellen | MIDDEN | KLEIN | T3: origin localhost:8201 checken + ingress |
| P-04 | Gateway 8130 publiek maken als api.stay4s.com (ipv LiteLLM direct) | HOOG | MIDDEN | echte 401 + tiers + billing erin; roadmap commercieel |
| P-05 | Mollie live-key + subscribe-flow (signup->betaling->key->mail) | HOOG | GROOT | commercieel blokker #1 |

## Modellen & Training
| # | Idee | Waarde | Moeite | Opmerking |
|---|------|--------|--------|-----------|
| M-01 | Stay4S-LM-001 ladder afmaken (groot loopt, reus daarna) | MIDDEN | loopt | Droid bewaakt Vast.ai |
| M-02 | GGUF-export beste checkpoint -> Ollama op Pi | HOOG | KLEIN | export_gguf.py ligt klaar |
| M-03 | Meer NL-data (Wikipedia/OpenSubtitles/Gutenberg) | MIDDEN | MIDDEN | collect_massive.py ligt klaar |
| M-04 | core-v5 trainen obv core-v4 (niet from-scratch) | HOOG | MIDDEN | docs: "bouw voort op core-v4" |
| M-05 | RunPod serverless deployment beste model | MIDDEN | MIDDEN | serverless_deploy.py klaar; RunPod-key is 401 - eerst herstellen |

## Product & Commercieel
| # | Idee | Waarde | Moeite | Opmerking |
|---|------|--------|--------|-----------|
| C-01 | API-landingspagina www.stay4s.com/api | HOOG | KLEIN | gateway heeft al landings-HTML |
| C-02 | Scam-Shield B2B (banken/verzekeringen) | HOOG | GROOT | sterkste commerciele pijler |
| C-03 | White-label aanbieding (EUR 999/mnd) | MIDDEN | MIDDEN | technisch al klaar |
| C-04 | Companion-app PWA (EUR 4,99/mnd) | MIDDEN | MIDDEN | compa.stay4s.com draait weer sinds 17-10 |
| C-05 | SMS-waarschuwingen scam-shield (via 4G-router?) | LAAG | MIDDEN | pas als SIM-modem echt bestaat |

## Proces & Documentatie
| # | Idee | Waarde | Moeite | Opmerking |
|---|------|--------|--------|-----------|
| D-01 | ECOSYSTEEM_REGISTER bijhouden (OpenCode schrijft) | HOOG | loopt | correcties via inboxen |
| D-02 | Dit ideeen-register tonen in dashboard + GitHub | MIDDEN | KLEIN | gedaan 17-10 |
| D-03 | Wekelijkse automatische backlog-review | LAAG | KLEIN | kan later via automatisering |



