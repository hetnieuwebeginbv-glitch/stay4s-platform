## stay4s-lm-001-reus (reus, 514,531,840 params)

- checkpoint: `/root/stay4s-llm/runs/stay4s-lm-001-reus/ckpt_best.pt` | iter 6000 | train-val_loss 3.3441
- **perplexity (val)**: 28.10  _(lager = beter; alleen vergelijkbaar bij gelijke tokenizer)_
- **cloze-accuratesse**: 0/32 = 0% (nl 0/16, en 0/16)
- **diversiteit**: distinct-1 0.627, distinct-2 0.914, repetitie-4gram 0.011

### Cloze-details

| taal | prompt | verwacht | model | ok |
|---|---|---|---|---|
| nl | De hoofdstad van Nederland is | Amsterdam | s.  De naam Amway is afgeleid | ❌ |
| nl | Twee plus twee is | vier | s's first-person shooter. | ❌ |
| nl | De zon komt op in het | oosten | t-principe.  De naam | ❌ |
| nl | Een jaar heeft twaalf | maanden | f.  De eerste versie van het | ❌ |
| nl | Water kookt bij honderd graden | Celsius | n.  De naam komt van het | ❌ |
| nl | De koning van Nederland is | Willem | s.  De Nederlandse vertaling van de | ❌ |
| nl | Een week heeft zeven | dagen | n.  De eerste versie van de | ❌ |
| nl | Parijs is de hoofdstad van | Frankrijk | n.  Geschiedenis  De stad | ❌ |
| nl | De aarde draait om de | zon | e.  De naamgeving van de | ❌ |
| nl | Een koe geeft | melk | t een aantal extra mogelijkheden.  Een | ❌ |
| nl | De Rijn is een | rivier | niaans getal.  De naamgeving | ❌ |
| nl | Nederland ligt in | Europa | n.  In Nederland is Sofie | ❌ |
| nl | Een minuut heeft zestig | seconden | g.  De naam Sofie is | ❌ |
| nl | De maan schijnt in de | nacht | estijl te passen.  De naam | ❌ |
| nl | Amsterdam is de hoofdstad van | Nederland | n.  De stad ligt aan de | ❌ |
| nl | IJs is bevroren | water | n genoemd.  De naam komt van | ❌ |
| en | The capital of France is | Paris | s.  The term refers to the | ❌ |
| en | Two plus two equals | four | s 5 and 5.  The first | ❌ |
| en | The sun rises in the | east | e's heart, and the body is in | ❌ |
| en | A year has twelve | months | e A year.  The first Grothendieck | ❌ |
| en | Water boils at one hundred degrees | Celsius | s's time.  In the early | ❌ |
| en | The king of the Netherlands is | Willem | s.  The word Zubaydah is also | ❌ |
| en | A week has seven | days | n A week.  The first episode | ❌ |
| en | London is the capital of | England | f's economy.  The city is | ❌ |
| en | The earth orbits the | sun | e's body, and the body is in | ❌ |
| en | A cow gives | milk | s a "slow" to the " | ❌ |
| en | The Rhine is a | river | a-like substance that is a substance that | ❌ |
| en | The Netherlands is in | Europe | n's own right.  In the | ❌ |
| en | A minute has sixty | seconds | y A minute.  The first issue | ❌ |
| en | The moon shines at | night | t's birth.  The first episode | ❌ |
| en | Berlin is the capital of | Germany | f's economy.  The city is | ❌ |
| en | Ice is frozen | water | n, which is a very rare and highly | ❌ |

### Generatie-voorbeelden (temp 0.8, top_k 40)

- **Nederland is** → ` Nederland is-achtig en in elk geval in België en Nederland worden vergelijkbare functies gebruikt.  In Nederland worden processors gebruikt bij het ontwerp van`
- **De geschiedenis van** → ` De geschiedenis van, het door de schrijver Flor Van der Elst, die in 2000 in het Nederlands verscheen.  Bibliografie  Romans  Søbenhavn (1985) Stanning for the`
- **In de toekomst zal** → ` In de toekomst zal zich in een interview met LA hebben aangezet tot een filmproductie van de filmrechtenaar.  In de film De kus van professor Zico gaat Sakharo`
- **The future of** → ` The future of was the case of a Greek translation of the Greek into Latin, in the form of a Latin translation of the Greek into Greek. However, the first trans`
- **Artificial intelligence will** → ` Artificial intelligence will is in the form of a self-sustained idea of his own self-sustained self. Grothendieck's interest in mathematics at the time is seen`
- **In the Netherlands** → ` In the Netherlands is credited with introducing the name from the Dutch bassist Piet Visser, to the tune "Amsterdam" from his song "Amsterdam". In early 2007, `
