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
| R3 | Beale forensics: derived key rules, human-number tests, the pamphlet as key | Each hypothesis has a control and a null; hoax evidence quantified | pending | |
| R4 | D'Agapeyeff: 14x14 routes, shifted coordinates, transposition + substitution | Every model has a positive control | pending | |
| R5 | Tamam Shud: mnemonic search of known texts with fuzzy letters | Null-calibrated search across large corpora | pending | |
| R6 | Kryptos K4: layered models, autokey, transposition + key elimination | Elimination counts by model family, with vacuous cases excluded | pending | |
| R7 | Voynich generator lab: which mechanism reproduces the statistics | Verbose cipher, self-citation, table/grille models scored against the measured profile | pending | |
| R8 | Autobreak: trained cipher-type classifier and solve-everything pipeline | Held-out accuracy reported; pipeline solves demo ciphers of unknown type | pending | |
| R9 | Breadth: more ACA and machine ciphers, each with an attack | Roster extended; catalogue page shows covered and missing types | pending | |
| R10 | Teaching: step-through visualiser for key ciphers | Letter-by-letter trace for at least Vigenere, Playfair, Enigma | completed 2026-11-08 | Traces match Python in `tests/test_simulations.py` |
| R11 | Machine simulations: interactive Enigma with moving rotors and current path; working models of other devices | Simulator output matches the backend Enigma; rotors, stepping and wiring visible | completed 2026-11-08 | Enigma, Lorenz, Jefferson, Alberti, scytale, grille, rail fence. Enigma matches Python on 700-letter cases |

## Upgrade rounds
Each round: read the leads database, pick the round's items, run a hunt, review anything flagged, log what was learned, add new ideas here, then commit and push. Learning from one round may reorder later ones.

| Round | Focus | Status |
|---|---|---|
| 1 | Foundation: solver, simulators, verdict gates, leads database, hunter, catalogue, cyberpunk UI | completed 2026-11-08 |
| 2 | Calibration: fix E3 and E4 (read Z340), rerun sweep, Dorabella and D'Agapeyeff under the new verdict | completed 2026-11-09 (E4 carried over) |
| 3 | R3 Beale forensics; R4 D'Agapeyeff routes and shifted coordinates | in_progress next |
| 4 | R5 Tamam Shud mnemonic search; R6 Kryptos K4 layered eliminations | pending |
| 5 | R7 Voynich generator lab; Liber Primus attacks (known page keys as controls) | pending |
| 6 | R8 cipher-type classifier trained on the GPU; Autobreak pipeline | pending |
| 7 | Data hunt: Rongorongo, Indus, Shugborough, Bradwell pigeon, Debosnys, more Schmeh entries | pending |
| 8 | R9 breadth: M-209, Purple, VIC, more ACA types; a bombe simulation; catalogue page | pending |
| 9 | Graphics: animated attack visualisers, live hunter feed, lead timeline | pending |

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

## Emergent tasks
| ID | Note | Status |
|---|---|---|
| E2 | Sweep all 43 files in `data/sources/unsolved` | completed, rerun needed with the new verdict (Round 3) |
| E3 | Solvability oddity at long lengths | completed 2026-11-08: start temperature now scales with sqrt(length/400); 1500 letters, 26 symbols went from 30% to 93% (`scripts/tune_temperature.py`) |
| E4 | Z340: section A reading is exact (100% consistent with the published solution). Section B is right until about reading position 99 of 153, then breaks; last two rows are 88% consistent | in_progress. Single-cut phase changes, regular walks and row swaps were all tested and fail (`scripts/diagnose_z340b.py`). On the 286 verified positions the solver reaches 32%, so it needs a stronger language model or more search as well. NEXT: 5-gram scoring and many more CPU hours on this benchmark |
| E6 | Le Figaro ad solved by the hunter (reversed substitution, French). The database is searched by a form at `apprendre-en-ligne.net/crypto/Figaro/annonces.php`; `codes.php` lists the systems used. BLOCKED: querying it submits a form, and bulk collection needs the user's approval. Never send a proposed solution by email without asking | waiting on user |
| E7 | Hunter idea: combine reversal with each other transform, and add n-gram scoring in French for newspaper ads | pending |
| E5 | GPU: all three search loops are slower on MPS than one CPU core (`data/results/gpu_benchmark.json`); use GPU for neural work | decision recorded |
| E1 | Rubaiyat TSAMSTG match: check the edition of the Somerton copy for FitzGerald's introduction | pending (needs a person or a scan) |

## Decisions
- 2026-11-08: Offline translation through Argos; Latin has no model.
- 2026-11-08: The user asked for plan-and-implement across the ledger, so several rows are worked per session.
- 2026-11-08: Private GitHub repository created at the user's request. `data/models`, `.venv` and third-party code copies are ignored; a fresh clone needs `pip install -r requirements.txt` and `scripts/install_translation_models.py`.
