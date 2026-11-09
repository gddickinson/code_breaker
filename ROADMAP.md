# Code Breaker roadmap

**Resuming?** Read the tail of `SESSION_LOG.md`, then this file top to bottom, then `INTERFACE.md`.
Pick the row marked `in_progress`, or else the topmost `pending` row. Record numbers in **Results**.

Rule for every mystery claim: positive control + null comparison + count of hypotheses tried (`codebreaker/validation.py`).
Never type a ciphertext from memory; extract it from a recorded source and add an integrity test.

## Ledger
| ID | Task | Completion criteria | Status | Results |
|---|---|---|---|---|
| R0 | First build: 61 ciphers, web app, five case files | Tests pass | completed 2026-11-08 | See SESSION_LOG |
| R1 | Stronger homophonic solver and a solvability map | Reliable at 48 symbols on 8 of 8 keys; map of recoverable length vs symbols | in_progress | NEXT: tune `kernels.anneal_homophonic`, wire into `solve_symbols` |
| R2 | Zodiac benchmarks (Z408, Z340) and Dorabella data | Verified ciphertext or a documented failure; Z408 solved by our tools; Z340 period-19 signal shown | pending | |
| R3 | Beale forensics: derived key rules, human-number tests, the pamphlet as key | Each hypothesis has a control and a null; hoax evidence quantified | pending | |
| R4 | D'Agapeyeff: 14x14 routes, shifted coordinates, transposition + substitution | Every model has a positive control | pending | |
| R5 | Tamam Shud: mnemonic search of known texts with fuzzy letters | Null-calibrated search across large corpora | pending | |
| R6 | Kryptos K4: layered models, autokey, transposition + key elimination | Elimination counts by model family, with vacuous cases excluded | pending | |
| R7 | Voynich generator lab: which mechanism reproduces the statistics | Verbose cipher, self-citation, table/grille models scored against the measured profile | pending | |
| R8 | Autobreak: trained cipher-type classifier and solve-everything pipeline | Held-out accuracy reported; pipeline solves demo ciphers of unknown type | pending | |
| R9 | Breadth: more ACA and machine ciphers, each with an attack | Roster extended; catalogue page shows covered and missing types | pending | |
| R10 | Teaching: step-through visualiser for key ciphers | Letter-by-letter trace for at least Caesar, Vigenere, Playfair, Enigma | pending | |

## Emergent tasks
| ID | Note | Status |
|---|---|---|
| E2 | Sweep all 43 files in `data/sources/unsolved` (AZdecrypt 'Unsolved' set) with calibrated solvers | pending |
| E1 | Rubaiyat TSAMSTG match: check the edition of the Somerton copy for FitzGerald's introduction | pending (needs a person or a scan) |

## Decisions
- 2026-11-08: Offline translation through Argos; Latin has no model.
- 2026-11-08: The user asked for plan-and-implement across the ledger, so several rows are worked per session.
- 2026-11-08: Private GitHub repository created at the user's request. `data/models`, `.venv` and third-party code copies are ignored; a fresh clone needs `pip install -r requirements.txt` and `scripts/install_translation_models.py`.
