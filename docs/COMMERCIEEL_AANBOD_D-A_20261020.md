# Stay4S Commerciele Route D+A — uitwerking (2026-10-20)
Besluit: gebruiker volgt Droid-advies. Eerst D (social-agent) voor snelle omzet,
dan A (klantenservice-agent) zodra xl live is.

===========================================================
## PAKKET D — Stay4S Social (NU verkoopbaar)
"Elke week 3 passende posts voor jouw zaak. Jij kiest, wij plannen."

- **Basis EUR 29/mnd**: 12 posts/maand voorgesteld (tekst + beeldrichting), 1 kanaal,
  maandelijkse planning, NL-taalmodel in eigen beheer
- **Plus EUR 59/mnd**: 20 posts, 3 kanalen (IG/FB/LinkedIn), automatisch plannen na akkoord,
  maandrapportage met bereik
- Setup: EUR 99 eenmalig (intake, toon-van-merk, templates)
- Doelgroep: zzp, horeca, kappers, garages, webshops <10 medewerkers
- Marge: draait op bestaande Pi (social-agent :8095), kost ons ~EUR 2/klant aan energie/compute

## PAKKET A — Stay4S Klantenservice (vanaf xl-release, ~deze week)
"Een Nederlandse medewerker op je site die nooit slaapt — jouw data blijft in Nederland."

- **Starter EUR 49/mnd**: chat-widget op je site, getraind op jouw FAQ/pagina''s (max 50 docs),
  500 gesprekken/maand, WhatsApp-kanaal inbegrepen
- **Pro EUR 99/mnd**: onbeperkt docs, 2.500 gesprekken, doorverwijzing naar mens bij onzekerheid,
  eigen toon/woordenlijst, rapportage
- Setup: EUR 250 eenmalig (inrichting + training op klantdata + testweek)
- Uniek: eigen NL-model (xl/Titaan), GEEN data naar OpenAI/US — AVG-proof verhaal
- Technisch: chat-widget (JS-snippet) -> gateway-v3 -> xl/Titaan via Ollama + retrieval op klantdocs

## Bundel
- D+A samen: EUR 69/mnd (Starter) / EUR 139/mnd (Plus+Pro) -> korting ~15%
- Jaarcontract: 12 voor 11

## Verkoopvolgorde (eerste 30 dagen)
1. Week 1: landingspagina live (stay4s.nl/aanbod), 10 warme prospects benaderen (eigen netwerk)
2. Week 2: 2 pilotklanten D gratis/halve prijs -> testimonials + screenshots
3. Week 3: A-pilot starten op xl-model zodra GGUF op Pi draait (wo/do)
4. Week 4: pilots omzetten naar betalend; case study op site

## Wat Droid bouwt (autonoom)
- [x] Commercieel plan + deze uitwerking
- [ ] Landingspagina /aanbod (tekst + opmaak klaar; livegang na GO)
- [ ] Chat-widget v0 (JS -> gateway-v3) voor A
- [ ] Offerte-template + onboarding-checklist
- [ ] Demo-pagina met live model (link naar lab.stay4s.nl als bewijs "wij bouwen zelf")

## Wat jij doet
- 10 namen warme prospects; Mollie live-key (betalingen); kvk/factuurgegevens voor offertes

## Cijfers snel
- 10 klanten D-Plus = EUR 590/mnd; 5 klanten A-Pro = EUR 495/mnd -> EUR 1.085/mnd runrate
- kosten: Pi (~EUR 15/mnd stroom) + Vast-trainingsbudget (apart) -> marge >90% op diensten
