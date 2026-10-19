## stay4s-lm-002-reus-wiki (reus, 514,531,840 params)

- checkpoint: `runs/stay4s-lm-002-reus-wiki/ckpt_best.pt` | iter 14500 | train-val_loss 2.5597
- **perplexity (val)**: 14.97  _(lager = beter; alleen vergelijkbaar bij gelijke tokenizer)_
- **cloze-accuratesse**: 5/32 = 16% (nl 4/16, en 1/16)
- **diversiteit**: distinct-1 0.741, distinct-2 0.933, repetitie-4gram 0.000

### Cloze-details

| taal | prompt | verwacht | model | ok |
|---|---|---|---|---|
| nl | De hoofdstad van Nederland is | Amsterdam | s Amsterdam. | ✅ |
| nl | Twee plus twee is | vier | s | ❌ |
| nl | De zon komt op in het | oosten | t sterrenbeeld Eridanus. | ❌ |
| nl | Een jaar heeft twaalf | maanden | f een zoon, die in de jaren | ❌ |
| nl | Water kookt bij honderd graden | Celsius | n De watertemperatuur van de bodem is | ❌ |
| nl | De koning van Nederland is | Willem | s Koning van België. | ❌ |
| nl | Een week heeft zeven | dagen | n een ster. | ❌ |
| nl | Parijs is de hoofdstad van | Frankrijk | n Frankrijk. De stad ligt in het | ✅ |
| nl | De aarde draait om de | zon | e Aarde om de zon. | ✅ |
| nl | Een koe geeft | melk | t Een koe geeft de volgende informatie | ❌ |
| nl | De Rijn is een | rivier | n rivier in de Duitse deelstaat Rijnland | ✅ |
| nl | Nederland ligt in | Europa | n de regio's Noord-Holland en | ❌ |
| nl | Een minuut heeft zestig | seconden | g een minuut voorsprong op de nummer | ❌ |
| nl | De maan schijnt in de | nacht | e baan van de maan te zijn gekomen | ❌ |
| nl | Amsterdam is de hoofdstad van | Nederland | n Suriname. De stad ligt aan de | ❌ |
| nl | IJs is bevroren | water | n De ijsvlo is een van | ❌ |
| en | The capital of France is | Paris | s Aiguillon. | ❌ |
| en | Two plus two equals | four | s | ❌ |
| en | The sun rises in the | east | e The sun is the sun's bright | ❌ |
| en | A year has twelve | months | e A year has eight. | ❌ |
| en | Water boils at one hundred degrees | Celsius | s The water boils at one hundred | ❌ |
| en | The king of the Netherlands is | Willem | s King of the Netherlands. | ❌ |
| en | A week has seven | days | n A week has three. A week | ❌ |
| en | London is the capital of | England | f London. It is the capital of | ❌ |
| en | The earth orbits the | sun | e Earth's surface. It is about | ❌ |
| en | A cow gives | milk | s A cow gives | ❌ |
| en | The Rhine is a | river | a river in the German state of Baden | ✅ |
| en | The Netherlands is in | Europe | n History. | ❌ |
| en | A minute has sixty | seconds | y A minute has fourty-two | ❌ |
| en | The moon shines at | night | t The moon shines at the center | ❌ |
| en | Berlin is the capital of | Germany | f Berlin. It is the capital of | ❌ |
| en | Ice is frozen | water | n | ❌ |

### Generatie-voorbeelden (temp 0.8, top_k 40)

- **Nederland is** → ` Nederland is Bijzondere aandacht is er voor een relatief groot aantal mensen die in de media hebben gereageerd op de Nederlandse taal en cultuur. In de Verenig`
- **De geschiedenis van** → ` De geschiedenis van De club is verbonden aan de voetbalafdeling van FC Tilburg. De club is opgericht op 24 juni 1945. Op 8 juni 2003 is de naam gewijzigd in FC`
- **In de toekomst zal** → ` In de toekomst zal Het album zal zich richten op "Evolve". Het album zal de terugkeer naar de muziekindustrie in de jaren 00 tot en met 1680 zijn. Omgekeerd za`
- **The future of** → ` The future of The most recent expansion of the world is the "Woman of Europe", which was made in 1949 by the Soviet Union. The US would be able to create a wor`
- **Artificial intelligence will** → ` Artificial intelligence will be in the middle of an argument ("causing one's own knowledge") and may cause a situation, or a state, to be an issue that is not `
- **In the Netherlands** → ` In the Netherlands Aalsmeer · `
