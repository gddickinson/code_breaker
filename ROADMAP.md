# Code Breaker roadmap

**Resuming?** Read the tail of `SESSION_LOG.md`, then this file top to bottom, then `INTERFACE.md`.
Pick the row marked `in_progress`, or else the topmost `pending` row. Record numbers in **Results**.

Rule for every mystery claim: positive control + null comparison + count of hypotheses tried (`codebreaker/validation.py`).
Never type a ciphertext from memory; extract it from a recorded source and add an integrity test.

## Ledger
| ID | Task | Completion criteria | Status | Results |
|---|---|---|---|---|
| R0 | First build: 61 ciphers, web app, five case files | Tests pass | completed 2026-11-08 | See SESSION_LOG |
| R1 | Stronger homophonic solver and a solvability map | Reliable at 48 symbols on 8 of 8 keys; map of recoverable length vs symbols | completed 2026-11-08 | 9 of 9 keys at w=2, t0=3. Map in `data/results/solvability.json`. Beale density recovers under 15%; see E3 |
| R2 | Zodiac benchmarks (Z408, Z340) and Dorabella data | Verified ciphertext or a documented failure; Z408 solved by our tools; Z340 period-19 signal shown | completed 2026-11-08 | Z408 91.9%. Z340 period 19, 37 repeats vs shuffled max 34; after undoing, period 1 with 39. Letters not yet read (E4). Dorabella: 3 transcriptions, 0.7-2.2% pair disagreement |
| R3 | Beale forensics: derived key rules, human-number tests, the pamphlet as key | Each hypothesis has a control and a null; hoax evidence quantified | completed 2026-11-09 | Adjacent-number correlation: B2 0.05, B1 0.25, B3 0.62. Key rules: best z 2.5 of 48; planted control z 40 |
| R4 | D'Agapeyeff: 14x14 routes, shifted coordinates, transposition + substitution | Every model has a positive control | completed 2026-11-09 | 196 pairs = 14x14. 138 tests: 0 readable, 115 no evidence, 23 inconclusive |
| R5 | Tamam Shud: mnemonic search of known texts with fuzzy letters | Null-calibrated search across large corpora | completed 2026-11-09 | Six books, best p 0.12, none significant; planted control found |
| R6 | Kryptos K4: layered models, autokey, transposition + key elimination | Elimination counts by model family, with vacuous cases excluded | completed 2026-11-09 | 1,152 configs, 58.9M orders, 0 survivors; control found; autokey and Hill excluded |
| R7 | Voynich generator lab: which mechanism reproduces the statistics | Verbose cipher, self-citation, table/grille models scored against the measured profile | completed 2026-11-09 | Noise floor 0.37; best non-fitted 2.9. Verbose matches H2, not word length. Self-citation version is crude (E9) |
| R8 | Autobreak: trained cipher-type classifier and solve-everything pipeline | Held-out accuracy reported; pipeline solves demo ciphers of unknown type | completed 2026-11-09 | 41 classes: top-1 62%, top-3 80%, family 86%. Autobreak 21 of 24 hidden. GPU 5.5x faster than CPU for training |
| R9 | Breadth: more ACA and machine ciphers, each with an attack | Roster extended; catalogue page shows covered and missing types | completed 2026-11-09 | 69 systems; bombe recovers plugboard Enigma from a 32-letter crib; coverage page. Purple, SIGABA, Typex planned |
| R10 | Teaching: step-through visualiser for key ciphers | Letter-by-letter trace for at least Vigenere, Playfair, Enigma | completed 2026-11-08 | Traces match Python in `tests/test_simulations.py` |
| R11 | Machine simulations: interactive Enigma with moving rotors and current path; working models of other devices | Simulator output matches the backend Enigma; rotors, stepping and wiring visible | completed 2026-11-08 | Enigma, Lorenz, Jefferson, Alberti, scytale, grille, rail fence. Enigma matches Python on 700-letter cases |

## Upgrade rounds
Each round: read the leads database, pick the round's items, run a hunt, review anything flagged, log what was learned, add new ideas here, then commit and push. Learning from one round may reorder later ones.

| Round | Focus | Status |
|---|---|---|
| 1 | Foundation: solver, simulators, verdict gates, leads database, hunter, catalogue, cyberpunk UI | completed 2026-11-08 |
| 2 | Calibration: fix E3 and E4 (read Z340), rerun sweep, Dorabella and D'Agapeyeff under the new verdict | completed 2026-11-09 (E4 carried over) |
| 3 | R3 Beale forensics; R4 D'Agapeyeff routes and shifted coordinates | completed 2026-11-09 |
| 4 | R5 Tamam Shud mnemonic search; R6 Kryptos K4 layered eliminations | completed 2026-11-09 |
| 5 | R7 Voynich generator lab; Liber Primus attacks (known page keys as controls) | completed 2026-11-09 |
| 6 | R8 cipher-type classifier trained on the GPU; Autobreak pipeline | completed 2026-11-09 |
| 7 | Data hunt (completed 2026-11-09): Rongorongo, Indus, Shugborough, Bradwell pigeon, Debosnys, more Schmeh entries | completed 2026-11-09 |
| 8 | R9 breadth: M-209, more ACA types, bombe, coverage page (Purple and VIC deferred, listed on the coverage page) | completed 2026-11-09 |
| 9 | Graphics: animated attack visualiser, live hunter feed, lead timeline | completed 2026-11-09 |
| 10 | Return to the hardest targets: E8 Beale drift, E9 Voynich, E10 multilingual Autobreak, E7 reversal combos, E4 diagnosis (E11 and the E4 fix carried over) | completed 2026-11-09 |
| 11 | 5-gram scorer on Z340 (E4), E11 Rongorongo alignment, short-passage Beale keys | completed 2026-11-09 (neural scorer deferred: 5-grams fixed the ranking) |
| 12 | Longer Z340 search; D'Agapeyeff digit transposition; Liber Primus running keys; cheap Autobreak fallbacks | completed 2026-11-09 |
| 13 | Scorers judged against the achievable key on Z340: word-aware and neural (GPU), with error tolerance; then section B's break | next |

## Lessons learned
- Beating a shuffled copy proves only that the order is non-random. Results must also match a real solve of that size and contain real words.
- Short-text solvers overfit: the homophonic solver beat the true plaintext's score until a letter-frequency penalty was added.
- A null built from real initials is much stricter than shuffled letters.
- A "survivor" in an elimination can be vacuous: count how many constraints actually applied.
- On Apple Silicon, integer table-lookup search is faster on one CPU core than on the GPU.

- Temperature must scale with text length; a fixed schedule quietly fails on long messages.
- Ground-truth diagnostics on solved ciphers can localise a modelling error to an exact position.

- Simple transforms before substitution are worth trying everywhere: one reversal unlocked a real message.

- The stricter verdict correctly demoted Dorabella and seven sweep entries from 'signal' to 'structure only'.

- Compare a cipher against its solved sibling: Beale 2 made the correlation test interpretable.

- Plant a known answer in the exact shape of the real problem, so that zero survivors means something.

- A poor score for a crude copy of a published theory says nothing about the theory itself.

- Near-miss classification is fine when the next step can test several guesses cheaply.

- Do not type ciphertext from memory: the query for the pigeon message used a wrong letter that the published form corrected.

- Contradiction search is powerful: one wrong plug guess eliminates itself, which is why the bombe needs only a short crib.

- Test your own best explanation by building the rival: the honest Beale encoder overturned last round's reading.
- Before buying more search, compare the true answer's score with what the solver found.

- Check whether a new idea is even distinct: short Beale passages reduce to whole-document offsets, so that avenue was rejected.
- Judge a language model against the best answer a key can actually produce, not the idealised published text.

- Recheck favourable comparisons for fairness: the 5-gram 'win' on Z340 compared against an unreachable text.

## Emergent tasks
| ID | Note | Status |
|---|---|---|
| E2 | Sweep all 43 files in `data/sources/unsolved` | completed, rerun needed with the new verdict (Round 3) |
| E3 | Solvability oddity at long lengths | completed 2026-11-08: start temperature now scales with sqrt(length/400); 1500 letters, 26 symbols went from 30% to 93% (`scripts/tune_temperature.py`) |
| E4 | Z340: section A reading is exact; section B breaks at position 99. CORRECTION: the 5-gram model only ranks the published text above decoys; the best single key matches it on 90% of letters and scores -1687 against -1595 for decoys, so the model still prefers wrong text. Longer search plateaus at about 41-44%. NEXT: error-tolerant scoring, a word-aware or neural scorer judged against the best achievable key | in_progress |
| E6 | Le Figaro ad solved by the hunter (reversed substitution, French). The database is searched by a form at `apprendre-en-ligne.net/crypto/Figaro/annonces.php`; `codes.php` lists the systems used. BLOCKED: querying it submits a form, and bulk collection needs the user's approval. Never send a proposed solution by email without asking | waiting on user |
| E8 | Beale drift model | completed 2026-11-09: narrow-window honest encoder reaches r=0.68; hoax inference withdrawn. D'Agapeyeff digit transposition still an idea |
| E9 | Voynich: closer self-citation and independent-space verbose models added; each matches H2 and word length but fails on vocabulary or Zipf. Liber Primus running keys still pending | partial |
| E10 | Multilingual Autobreak with fallback attacks | completed 2026-11-09 |
| E11 | Rongorongo alignment: control passes, real pairs below the null. Needs a transcribed Indus corpus and Debosnys symbols | partial |
| E7 | Hunter idea: combine reversal with each other transform, and add n-gram scoring in French for newspaper ads | pending |
| E5 | GPU: search loops stay on CPU; neural training runs on MPS, 5.5x faster (`data/results/classifier.json`) | decision recorded |
| E1 | Rubaiyat TSAMSTG match: check the edition of the Somerton copy for FitzGerald's introduction | pending (needs a person or a scan) |

## Decisions
- 2026-11-09: Avenues without an implemented strategy get status `idea`; the hunter runs only `open` ones.
- 2026-11-08: Offline translation through Argos; Latin has no model.
- 2026-11-08: The user asked for plan-and-implement across the ledger, so several rows are worked per session.
- 2026-11-08: Private GitHub repository created at the user's request. `data/models`, `.venv` and third-party code copies are ignored; a fresh clone needs `pip install -r requirements.txt` and `scripts/install_translation_models.py`.
