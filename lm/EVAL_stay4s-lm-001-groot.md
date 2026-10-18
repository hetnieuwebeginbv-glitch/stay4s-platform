## stay4s-lm-001-groot (groot, 235,358,208 params)

- checkpoint: `/root/stay4s-llm/runs/stay4s-lm-001-groot/ckpt_best.pt` | iter 5500 | train-val_loss 3.3358
- **perplexity (val)**: 28.75  _(lager = beter; alleen vergelijkbaar bij gelijke tokenizer)_
- **cloze-accuratesse**: 0/32 = 0% (nl 0/16, en 0/16)
- **diversiteit**: distinct-1 0.504, distinct-2 0.787, repetitie-4gram 0.050

### Cloze-details

| taal | prompt | verwacht | model | ok |
|---|---|---|---|---|
| nl | De hoofdstad van Nederland is | Amsterdam | su.  De stad is een | ❌ |
| nl | Twee plus twee is | vier | s (of: tetragrammen) en | ❌ |
| nl | De zon komt op in het | oosten | t-principe.  De zon | ❌ |
| nl | Een jaar heeft twaalf | maanden | f als eerste.  De meeste moderne | ❌ |
| nl | Water kookt bij honderd graden | Celsius | n.  De meeste van deze stoffen | ❌ |
| nl | De koning van Nederland is | Willem | su.  De koning van de | ❌ |
| nl | Een week heeft zeven | dagen | n als eerste.  De meeste moderne | ❌ |
| nl | Parijs is de hoofdstad van | Frankrijk | n.  De stad ligt aan de | ❌ |
| nl | De aarde draait om de | zon | e (deze is de aarde) en | ❌ |
| nl | Een koe geeft | melk | t  De term koe is een | ❌ |
| nl | De Rijn is een | rivier | n (deze naam is ontleend aan het | ❌ |
| nl | Nederland ligt in | Europa | n's tijdzone.  De Nederlandse | ❌ |
| nl | Een minuut heeft zestig | seconden | g als eerste de betekenis van een woord. | ❌ |
| nl | De maan schijnt in de | nacht | e-periode.  De maan is | ❌ |
| nl | Amsterdam is de hoofdstad van | Nederland | n.  De stad is de hoofdstad | ❌ |
| nl | IJs is bevroren | water | n.  De naam komt van het | ❌ |
| en | The capital of France is | Paris | su.  The term "c | ❌ |
| en | Two plus two equals | four | s  The first two are the two | ❌ |
| en | The sun rises in the | east | e The sun rises in the middle of the | ❌ |
| en | A year has twelve | months | e A year, and the year has four | ❌ |
| en | Water boils at one hundred degrees | Celsius | s, and the first two of these, | ❌ |
| en | The king of the Netherlands is | Willem | s, and the king of the Netherlands is | ❌ |
| en | A week has seven | days | n, and the two sides have four consonants | ❌ |
| en | London is the capital of | England | f.  The term "harmonic | ❌ |
| en | The earth orbits the | sun | e The Earth's orbit, and the Earth | ❌ |
| en | A cow gives | milk | s  The term "A" is | ❌ |
| en | The Rhine is a | river | a of the Christian faith.  The | ❌ |
| en | The Netherlands is in | Europe | n The Netherlands is invisible The Netherlands is | ❌ |
| en | A minute has sixty | seconds | y (one of the most famous of which | ❌ |
| en | The moon shines at | night | t's death.  The story of | ❌ |
| en | Berlin is the capital of | Germany | f.  The term Bodhidharma is used | ❌ |
| en | Ice is frozen | water | n.  The term is also used | ❌ |

### Generatie-voorbeelden (temp 0.8, top_k 40)

- **Nederland is** → ` Nederland is). Het idee dat de mens zich in zijn leven van de mensheid heeft kunnen afbeelden was echter niet zozeer een idee dat het niet helemaal juist was t`
- **De geschiedenis van** → ` De geschiedenis van als eerste vrouw, vertaald door A.J.C. ten tijde van de Nederlandse vertaling van De dood van Abraham Lincoln.  Inleiding  De eerste twee d`
- **In de toekomst zal** → ` In de toekomst zal-concept (het verlies van de taal in de toekomst) de toekomst kunnen verbeteren.  Natuurwetenschap  Een aantal van de eerste Nobelprijswinnaa`
- **The future of** → ` The future of and Bodhidharma. Bodhidharma's "Feminine Philosophy" was widely read at the same time. After arriving in China, Bodhidharma was able to teach him`
- **Artificial intelligence will** → ` Artificial intelligence will (artificial intelligence) and compares the actions required by the police to be taken to ensure that the police can work properly `
- **In the Netherlands** → ` In the Netherlands (in the Netherlands) and the Netherlands Bodhidharma (in the Philippines) who have taught the earliest known book of the same language, the `
