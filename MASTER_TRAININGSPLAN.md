# STAY4S — MASTER TRAININGSPLAN
> Alle trainingstactieken in de juiste volgorde. Eerst bestaande pijplijnen afmaken, cluster-ladder (16-8-6-4-3) als laatste grote stap.
> Regel: een fase start pas als de vorige groen is. Kostenposten > EUR 50 vereisen gebruikers-GO.
> Laatst bijgewerkt: 2026-10-18 (Droid) | Eigenaar uitvoering: Droid (Vast.ai), OpenCode (Pi/eval)

## Huidige staat (baseline)
- Ladder Stay4S-LM-001 (from-scratch, tokenizer 32k, NL/EN 50/50, 74M tokens):
  nano 23M=5.29 | mini 42M=4.19 | klein 70M=3.79 | middel 110M=3.66 | groot 235M=3.34 | reus 514M=LOOPT
- Scam-classifier v2 (DistilBERT 66M, 12k synthetisch): 10/10 op tests
- Data: ~/stay4s-llm/data (raw/cleaned/datasets), scripts in scripts/ + scripts/opschaling/
- Box: Vast.ai 56269957 (1x RTX 4090 48GB, $0.55/u) - HF/Google geblokkeerd, PyPI OK, Pi als download-relais

## FASE 0 — Reus afronden (LOOPT, klaar ~18-10 middag)
- Bewaken tot iter 6000, verwacht val ~3.0-3.1
- Acceptatie: ckpt_best.pt aanwezig, val < 3.34 (beter dan groot)

## FASE 1 — Ladder-evaluatie + productie-export (klein, ~1u, gratis)
- evaluate.py over alle 6 checkpoints: val loss + generatie-proef (NL prompt-set)
- export_gguf.py: beste model (waarschijnlijk groot of reus) -> GGUF -> scp naar Pi -> Ollama
- Acceptatie: ollama run stay4s-lm-001 werkt op Pi; antwoordt NL
- Dit bewijst de hele pijplijn van training naar productie

## FASE 2 — Data-opschaling (flessenhals eerst!) (~1-2 dagen CPU, ~$15)
- Doel: 74M -> 1B tokens NL/EN (fase 2a), later 5B+ (fase 2b vlak voor cluster)
- Bronnen via Pi (HF geblokkeerd op Vast): Wikipedia NL+EN dumps, OpenSubtitles NL, Gutenberg NL/EN, Tweakers/NOS-achtige open corpora
- Pi downloadt -> scp naar Vast -> bestaande clean/tokenize-pijplijn
- Acceptatie: datasets/train.bin >= 1B tokens, tokenizer ongewijzigd (32k)

## FASE 3 — Scam-Shield v3 met echte data (~halve dag)
- Feedback-loop in scam_shield.py: log (text, score, menselijke correctie) naar DB
- Klant-UI knop juist/onjuist (later, met OpenCode)
- Hertrain classifier v3 zodra >= 500 echte gelabelde berichten
- Acceptatie: v3 verslaat v2 op vaste testset (test_scam.py) + live precision > v2

## FASE 4 — Media-AI: beeld (quick win, ~4u GPU)
- Pi downloadt Stable Diffusion 1.5 (HF) -> scp naar Vast
- LoRA fine-tune: Stay4S-huisstijl (logo-achtig, kleuren #0f172a/#38bdf8) op 200-500 gegenereerde/curated beelden
- Koppelen aan media-proxy (8076) als lokale worker -> image_gpu: online
- Acceptatie: /api/image/generate levert Stay4S-stijl beeld; video blijft skeleton
- Commercieel: content-dienst (EUR 49-tier) krijgt beeld erbij

## FASE 5 — Multi-GPU-ready code (~1 dag, gratis)
- train.py -> DDP (torchrun), gradient-checkpointing optie, bf16
- Test op huidige box (1 GPU moet identiek blijven werken)
- Acceptatie: reproduceer middel-run (110M) met zelfde val loss +/- 0.05

## FASE 6 — Pre-train verfijning op 1B tokens (~1-2 dagen op huidige box, ~$25)
- groot (235M) en reus (514M) hervatten vanaf ckpt_last met 1B-token dataset
- Acceptatie: reus val < 2.8; zo niet: analyse voor cluster-fase

## FASE 7 — CLUSTER-LADDER (16-8-6-4-3) — LAATST, NA GO + BUDGET
- Pas als fase 1-6 groen. Vast.ai multi-GPU (8x 4090/5090, ~$3.5/u)
- Data: fase 2b (5B+ tokens) vooraf afronden
- Volgorde klein->groot: 1.5B -> 3B -> 4B -> (8B) -> (16B alleen als 8B zich bewijst)
- Raming: 1.5B ~2d | 3B ~4-5d | 4B ~6d | 8B ~2w | 16B ~4w (EUR 2500, aparte GO)
- Acceptatie per trede: beter dan kleinere trede + generatie-test NL
- Na elke trede: GGUF -> Pi, klaar voor core-v5/core-v6

## FASE 8 — Productie (doorlopend na fase 7)
- core-v5 (beste <=4B) als nieuw kernmodel op Pi (of RunPod serverless als te groot)
- serverless_deploy.py activeren voor zware modellen
- Monitoren: quality regressie-tests in eval-harness (OpenCode-lane)

## Risicos & mitigatie
- HF-blokkade Vast: alles via Pi-relais (bewezen met DistilBERT)
- Vast instance verdwijnt: checkpoints dagelijks syncen naar K: (nieuw cronjob fase 1)
- Kosten: per-fase GO; cluster pas na bewezen 1B-token resultaat
- Kwaliteit synthetische scam-data: alleen v1/v2 marketing "ondersteund door", nooit "100%"

## Dagelijkse bewaking (Droid)
- trainingslogs + checkpoints, storage_status.json monitor, K:-sync
