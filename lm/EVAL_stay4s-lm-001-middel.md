## stay4s-lm-001-middel (middel, 110,025,216 params)

- checkpoint: `/root/stay4s-llm/runs/stay4s-lm-001-middel/ckpt_best.pt` | iter 6000 | train-val_loss 3.6579
- **perplexity (val)**: 40.49  _(lager = beter; alleen vergelijkbaar bij gelijke tokenizer)_
- **cloze-accuratesse**: 0/32 = 0% (nl 0/16, en 0/16)
- **diversiteit**: distinct-1 0.488, distinct-2 0.701, repetitie-4gram 0.217

### Cloze-details

| taal | prompt | verwacht | model | ok |
|---|---|---|---|---|
| nl | De hoofdstad van Nederland is | Amsterdam | s.  De stad is een van | ❌ |
| nl | Twee plus twee is | vier | s Drie plus twee plus twee plus twee plus | ❌ |
| nl | De zon komt op in het | oosten | t-systeem.  De zon is | ❌ |
| nl | Een jaar heeft twaalf | maanden | fpinnen.  In de jaren | ❌ |
| nl | Water kookt bij honderd graden | Celsius | n.  In de jaren zestig van | ❌ |
| nl | De koning van Nederland is | Willem | s.  In de jaren zestig van | ❌ |
| nl | Een week heeft zeven | dagen | n.  In de jaren negentig werd | ❌ |
| nl | Parijs is de hoofdstad van | Frankrijk | n.  Geschiedenis  De stad | ❌ |
| nl | De aarde draait om de | zon | e te vangen.  De Aarde is | ❌ |
| nl | Een koe geeft | melk | t  Zie ook   Lijst van mineralen | ❌ |
| nl | De Rijn is een | rivier | n-achtige stof.  De stof | ❌ |
| nl | Nederland ligt in | Europa | n.  In Nederland is het woord | ❌ |
| nl | Een minuut heeft zestig | seconden | gpellen nodig.  In de | ❌ |
| nl | De maan schijnt in de | nacht | e te zijn.  De Aarde is | ❌ |
| nl | Amsterdam is de hoofdstad van | Nederland | n.  Geschiedenis  De stad | ❌ |
| nl | IJs is bevroren | water | n.  In de jaren negentig van | ❌ |
| en | The capital of France is | Paris | s.  The city of Bordeaux is | ❌ |
| en | Two plus two equals | four | s  The term "cool" | ❌ |
| en | The sun rises in the | east | e.  The fauna of the genus | ❌ |
| en | A year has twelve | months | e, including the first three being the first | ❌ |
| en | Water boils at one hundred degrees | Celsius | s.  The first known use of | ❌ |
| en | The king of the Netherlands is | Willem | s.  The term "colon | ❌ |
| en | A week has seven | days | n, and the number of astronauts is estimated | ❌ |
| en | London is the capital of | England | f.  The city of Bitola is | ❌ |
| en | The earth orbits the | sun | e from the Earth's crust, and the | ❌ |
| en | A cow gives | milk | s a "mixed" and "m | ❌ |
| en | The Rhine is a | river | a-based company based in Munich, Germany | ❌ |
| en | The Netherlands is in | Europe | n The Netherlands, and in AmE The Netherlands | ❌ |
| en | A minute has sixty | seconds | yes, and the other two are the | ❌ |
| en | The moon shines at | night | t.  The story of the story | ❌ |
| en | Berlin is the capital of | Germany | f.  The city of Bitola is | ❌ |
| en | Ice is frozen | water | n.  In the United States, | ❌ |

### Generatie-voorbeelden (temp 0.8, top_k 40)

- **Nederland is** → ` Nederland is Ieper geworden. Hij heeft een hartaanval (van: ) op een paal met behulp van een zwembad. Hij is de enige Nederlandse die hem ooit niet meer kan be`
- **De geschiedenis van** → ` De geschiedenis van was een van de beroemdste en meest bekende schrijvers van Vlaanderen. In de periode rond 1790 werd hij door de Fransen gezien als een van d`
- **In de toekomst zal** → ` In de toekomst zal zich opspelen in de kunstwereld.  Bibliografie Kornische gedichten van de Engelse schrijver William Shakespeare The Last Night in the sun Th`
- **The future of** → ` The future of on the right to exist. The new method was to integrate the two components of the plant by creating and forming a new species. There was also a ne`
- **Artificial intelligence will** → ` Artificial intelligence will them before they can be used as an alternative to the same purpose. This allows for an easy reading machine to read a more detaile`
- **In the Netherlands** → ` In the Netherlands-Eller-Dessau (LLL) The following is a list of professional associations, organizations, and organizations  Locations  Board members  Coins o`
