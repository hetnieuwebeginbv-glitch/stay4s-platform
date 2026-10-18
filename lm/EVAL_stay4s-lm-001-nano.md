## stay4s-lm-001-nano (nano, 23,033,856 params)

- checkpoint: `/root/stay4s-llm/runs/stay4s-lm-001-nano/ckpt_best.pt` | iter 1500 | train-val_loss 5.2937
- **perplexity (val)**: 244.72  _(lager = beter; alleen vergelijkbaar bij gelijke tokenizer)_
- **cloze-accuratesse**: 0/32 = 0% (nl 0/16, en 0/16)
- **diversiteit**: distinct-1 0.451, distinct-2 0.748, repetitie-4gram 0.036

### Cloze-details

| taal | prompt | verwacht | model | ok |
|---|---|---|---|---|
| nl | De hoofdstad van Nederland is | Amsterdam | send van de stad.  Het | ❌ |
| nl | Twee plus twee is | vier | singsp.  De eerste uitvoering | ❌ |
| nl | De zon komt op in het | oosten | t van de zon.  De eerste | ❌ |
| nl | Een jaar heeft twaalf | maanden | fingsrecht van de eerste keer. | ❌ |
| nl | Water kookt bij honderd graden | Celsius | n.  De eerste helft van de | ❌ |
| nl | De koning van Nederland is | Willem | s.  Het jaar is het jaar | ❌ |
| nl | Een week heeft zeven | dagen | ningsrecht.  De eerste uitvoering | ❌ |
| nl | Parijs is de hoofdstad van | Frankrijk | ningsgebied van de stad. | ❌ |
| nl | De aarde draait om de | zon | e te maken.  De eerste helft | ❌ |
| nl | Een koe geeft | melk | t te maken.  De eerste uitvoering | ❌ |
| nl | De Rijn is een | rivier | n van de stad.  Het jaar | ❌ |
| nl | Nederland ligt in | Europa | ningsgebied.  Het jaar is | ❌ |
| nl | Een minuut heeft zestig | seconden | gingsrecht.  De eerste helft | ❌ |
| nl | De maan schijnt in de | nacht | e van de Aarde.  De eerste | ❌ |
| nl | Amsterdam is de hoofdstad van | Nederland | ningsgebied.  Het jaar is | ❌ |
| nl | IJs is bevroren | water | n.  Het is een aantal van | ❌ |
| en | The capital of France is | Paris | sled by the city of the city. | ❌ |
| en | Two plus two equals | four | sings of the city.  The | ❌ |
| en | The sun rises in the | east | e, and the river, the river, | ❌ |
| en | A year has twelve | months | eings of the city's largest city. | ❌ |
| en | Water boils at one hundred degrees | Celsius | s.  In the late 19th | ❌ |
| en | The king of the Netherlands is | Willem | sled by the Battle of the Battle of | ❌ |
| en | A week has seven | days | nings of the city's largest city. | ❌ |
| en | London is the capital of | England | fings of the city.  The | ❌ |
| en | The earth orbits the | sun | eings of the island.  The | ❌ |
| en | A cow gives | milk | s, and the most of the most of | ❌ |
| en | The Rhine is a | river | aous, which is a large number of | ❌ |
| en | The Netherlands is in | Europe | nings.  In de jaren negentig | ❌ |
| en | A minute has sixty | seconds | yies, and the most of the most | ❌ |
| en | The moon shines at | night | t, and the Sun.  The | ❌ |
| en | Berlin is the capital of | Germany | fings of the city.  The | ❌ |
| en | Ice is frozen | water | n.  De naam van de naam | ❌ |

### Generatie-voorbeelden (temp 0.8, top_k 40)

- **Nederland is** → ` Nederland is en het algemeen is met de eerste twee leden van de Staten-Generaal.  Europa   De provincie wordt het hoogste deel van een stad van de gemeente. De`
- **De geschiedenis van** → ` De geschiedenis van op de omgeving.  Externe links   Lijst van de Eerste Wereldoorlog: De Grote Schoor (Dartels, de Vlaamse (Tele) van Lerk (Molen)  Lijst van `
- **In de toekomst zal** → ` In de toekomst zal worden op het niet meespot. Hiertoe wordt de eerste keer van de eerste keer in een kabinetswegen, en de tweede keer zijn vier keer de volgen`
- **The future of** → ` The future ofins' of a national-gans' style.  In de late-century British Columbia, the American Civil War of the United Kingdom, the British National Navy laun`
- **Artificial intelligence will** → ` Artificial intelligence willies, and the latter means that the most significant number of the most likely is not true.  Vitropie  In the early 18th century, th`
- **In the Netherlands** → ` In the Netherlandsies, the area is a similar to the city of the town of the east of the city.  The most important city is a small part of the town of the city `
