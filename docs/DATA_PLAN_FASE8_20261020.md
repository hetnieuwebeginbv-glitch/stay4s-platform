# DATA-PLAN FASE 8 — meer NL-trainingsdata (2026-10-20, Droid)

## Huidige voorraad
- Fase-2b-corpus: 8,54B tokens (NL-wiki + eerdere bronnen), SHA 3ecc1a52..., op box1/2/3
- Doel: minimaal 3-5x groter, want 13k-iter-recept snoept ~8,5B en grotere runs willen meer

## Bronnen (geprioriteerd)

### 1. GPT-NL Public Corpus — TOPKANDIDAAT
- 36B voortbewerkte NL-tokens, 21 NL-collecties, **CC-BY (commercieel OK, bronvermelding)**
- HF: GPT-NL/GPT-NL_Public_Corpus
- Grootste permissief-gelicentieerde NL-corpus dat er is (april 2026)
- Actie: `datasets`-download op box1, dedupe tegen huidige corpus, tokenizen met bestaande 32k-tokenizer
- Let op: ook EN/code/DE/DA-subsets erin — alleen NL-collecties pakken

### 2. FineWeb-2 (nld_Latn)
- HF: HuggingFaceFW/fineweb-2, subset nld_Latn (Common Crawl NL, schoon)
- Tientallen GB ruwe NL-tekst; kwaliteitsfilter al toegepast door HF
- Actie: streaming subset -> parquet -> tokenizen

### 3. Delpher / KB open krantenarchief
- 2M gedigitaliseerde kranten 1618-1995, open data via kb.nl datasets
- Ouderwets taalgebruik + OCR-ruis -> laag gewicht (max 5-10% van mix), wel uniek NL-idioom
- Pas pakken als 1+2 binnen zijn

### 4. (optioneel) overheid: officielebekendmakingen.nl / open.overheid.nl
- Formeel NL, juridisch register — handig voor klantenservice-toon

## Recept
1. Download op box1 (snelle host-CPU), NIELS op zwakke hosts tokenizen
2. Dedupe: hash per document (sha1 van genormaliseerde tekst) tegen bestaande corpus-index
3. Tokenizen met /root/stay4s-llm/data/tokenizer/tokenizer.json (de 32k)
4. Schrijf train2.bin/val2.bin NAAST huidige bins; hash naar K:-manifest
5. Eerste mix: 70% nieuw NL + 30% bestaand (rehearsal tegen vergeten)
6. Eerst op Titaan-schaal (470M actief) A/B testen voor xl-schaal budget erin gaat

## Budget-impact
- Download+prep: alleen CPU/ijd op bestaande boxen, geen extra $
- Langere runs: bij 36B extra tokens kan xl-klasse run ~4 dagen @ $0,97/u = ~$95