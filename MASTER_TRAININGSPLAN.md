# STAY4S — MASTER TRAININGSPLAN
> Alle trainingstactieken in de juiste volgorde. Eerst bestaande pijplijnen afmaken, cluster-ladder (16-8-6-4-3) als laatste grote stap.
> Regel: een fase start pas als de vorige groen is. Kostenposten > EUR 50 vereisen gebruikers-GO.
> Laatst bijgewerkt: 2026-10-18 avond (Droid) — F0/F1/F2a DONE, F6 loopt boven verwachting, F5-code klaar | Eigenaar uitvoering: Droid (Vast.ai), OpenCode (Pi/eval)

## Huidige staat (baseline)
- Ladder Stay4S-LM-001 (from-scratch, tokenizer 32k, NL/EN 50/50, 74M tokens):
  nano 23M=5.29 | mini 42M=4.19 | klein 70M=3.79 | middel 110M=3.66 | groot 235M=3.34 | reus 514M=3.3441 (DONE 18-10)
- Scam-classifier v2 (DistilBERT 66M, 12k synthetisch): 10/10 op tests
- Data: ~/stay4s-llm/data (raw/cleaned/datasets), scripts in scripts/ + scripts/opschaling/
- Box: Vast.ai 56269957 (1x RTX 4090 48GB, $0.55/u) - HF/Google geblokkeerd, PyPI OK, Pi als download-relais

## FASE 0 — Reus afronden (DONE 18-10, val 3.3441)
- Gedaan: iter 6000, val 3.3441 (onder groot 3.34 niveau, acceptatie gehaald)
- Acceptatie: ckpt_best.pt aanwezig, val < 3.34 (beter dan groot)

## FASE 1 — Ladder-evaluatie + productie-export (DONE 18-10, stay4s-reus praat op Pi)
- Gedaan: eval_harness over alle ladder-checkpoints: nano ppl 244.7 / middel 40.5 / groot 28.75 / reus 28.10 (cloze 0/32 = motiveert Fase 6)
- Gedaan: export_hf.py (ckpt->HF GPT2, logits-verified 2e-5) -> GGUF f16 + Q4_K_M -> Pi -> Ollama
- Bewijs: ollama stay4s-reus draait op Pi, 30 tok/s, vloeiend NL (feiten nog wankel zoals verwacht bij basismodel)
- Dit bewijst de hele pijplijn van training naar productie

## FASE 2 — Data-opschaling (2a DONE 18-10: 791M tokens NL92/EN8)
- Bereikt: 791.710.005 tokens (NL 730,8M=92% / EN 60,9M=8%) uit Wikipedia-dumps, via tokenize_corpus_v2.py (chunked); 74M backups bewaard. 2b (5B+) vlak voor cluster
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

## FASE 5 — Multi-GPU (DONE 18-10: DDP + resume bewezen op 2x 4090)
- Gedaan: train_ddp.py (torchrun/NCCL, per-rank seeds, no_sync accum, --init-from resume). NIEUWE VOLGORDE (Mitchell): F5 hardware-bewijs VOOR F7
- BEWEZEN op Vast 56618183 (2x RTX 4090 48GB): DDP 1,5x schaling (12.775->19.100 tok/s), beide GPU 99%, resume-onder-DDP correct (hervat iter 30, val 6.74->6.73). Host-note: blokkeert DNS-egress (UDP53) - offline wheels gebruiken
- Acceptatie: reproduceer middel-run (110M) met zelfde val loss +/- 0.05

## FASE 6 — Pre-train verfijning op 791M tokens (LOOPT, val 4.07->2.74, grens 2.8 al gepasseerd)
- reus hervat vanaf ckpt_best (iter 6000->18100, lr 3e-4, verse cosine). Tussenstand iter 7500: val 4.07 -> 2.7355 — acceptatiegrens 2.8 al GEPASSEERD. ETA 19-10 ~12:00
- Acceptatie: val < 2.8 (al bereikt bij iter 7000-7500). Daarna: groot ook op 791M? Beslissen na reus-resultaat

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
