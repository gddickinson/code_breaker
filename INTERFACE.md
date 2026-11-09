# Code Breaker: navigation map

`run.py` starts the FastAPI app on 127.0.0.1:8000.

## codebreaker/ core
| File | Purpose | Key names |
|---|---|---|
| `text.py` | Normalising letters and integers | `letters`, `to_ints`, `to_text`, `keyed_alphabet`, `similarity` |
| `languages.py` | Quadgram and frequency models for en, fr, de, it, es, la; cached in `data/models` | `model`, `score`, `detect`, `keywords`, `corpus_text` |
| `kernels.py` | Numba loops | `quad_score`, `anneal_mapping`, `climb_columnar`, `anneal_playfair`, `book_offset_scan`, `enigma_run`, `enigma_scan` |
| `analysis.py` | IC, entropy, Kasiski, cipher-type guess | `report`, `identify`, `ic` |
| `segment.py` | Restores word breaks | `segment` |
| `translate.py` | Offline translation via Argos; Latin via Helsinki opus-mt-mul-en, labelled a rough draft | `translate` |
| `validation.py` | False-positive controls; three-gate verdict | `null_test`, `positive_control`, `coverage`, `verdict` |
| `leads.py` / `litedb.py` | Leads database and its apsw wrapper (Anaconda's sqlite3 is broken here) | `connect`, `add_lead`, `add_avenue`, `summary` |
| `attacks/bombe.py` | Crib-based plugboard Enigma attack | `attack`, `demo` |
| `sudoku_vision.py` | Reads a sudoku grid from a photo | `read_grid`, `find_board` |
| `classifier.py` / `autobreak.py` | CNN cipher-type classifier (GPU) and the identify-and-solve pipeline | `classify`, `train`, `autobreak` |
| `lm.py` / `kernels_n.py` | GRU language model on the GPU, and 5-gram annealing | `train`, `scores`, `anneal5`, `table5` |
| `accel.py` | Optional GPU routes, chosen by benchmark | `device`, `best_route`, `book_scan`, `enigma_ic_scan`, `population_anneal` |

## codebreaker/ciphers/ (each `add(...)` fills `REGISTRY`)
`base.py` Cipher, Param, DEMO_PLAIN · `runner.py` attack_demo · `columns.py` columnar helpers ·
`monoalphabetic.py` · `polyalphabetic.py` · `polygraphic.py` (also fractionating) · `transposition.py` ·
`machines.py` (Enigma, Jefferson, Lorenz model, book, homophonic) · `aca.py` (Quagmires, Nicodemus, Fractionated Morse, Slidefair, Gromark, Alberti, M-209) · `modern_symmetric.py` · `modern_public.py`

## codebreaker/attacks/
`classical.py` general solvers, taking decrypt functions so that ciphers can import it · `modern.py` worked attacks on weak or misused cryptography

## codebreaker/mysteries/
`beale.py`, `dagapeyeff.py`, `tamam.py`, `kryptos.py`, `voynich.py`: each has `run()` returning JSON saved in `data/results/`.
`zodiac.py`, `dorabella.py`, `sweep.py`, `solvability.py`, `scriptlab.py`: further analyses. `corpus.py` loads symbols per code; `catalog.py` seeds the leads database; `hunter.py` runs avenues and records attempts.
`recovery.py` and `recovery_images.py`: measured OCR, error spread, key-aware repair and image reconstruction for the Recovery page (`scripts/run_recovery.py` regenerates them). `figaro_fusion.py` (OCR confusion networks and French HMM), `figaro_digits.py` (letter-digit alphabets). `figaro_digit_words.py` (dictionary beam for letter-digit ads), `figaro_digit_family.py` (shared keys and documented digit tables). `figaro_digit_sweep.py` (all documented digit and numeric tables over every ad). `figaro_numeric_mixed.py` (numbers with clear letters; number-only nulls). `casefiles.py` case metadata and `case()`; `casefile_sections.py` and `casefile_extra.py` turn results into displayed sections.

## codebreaker/web/
`app.py` routes under `/api`. `static/`: `core.js` (helpers, router), `library.js`, `tools.js` (workbench, translate, challenge), `mysteries.js`, `leads.js` (Lead Board), `charts.js` (SVG charts, background), `sim_engine.js` (pure simulation logic, node-testable), `sim_enigma.js`, `sim_mech.js`, `sim_trace.js`, `sim_bombe.js`, `sim_anneal.js`, `sim_how.js`, `sim_computer.js` (How It Works pages), `sim_crypto_engine.js` (pure AES, S-DES, Colossus logic), `puzzles_scan.js` (camera and photo reading), `puzzles_engine.js` and `puzzles_more.js` (extra puzzles), `tutorials.js`, `tutorials.json` and `guide_diagrams.js` (guides and their illustrations), `biology.js` and `biology.json` (codes in nature), `theory_engine.js` (pure algorithms), `theory.js`, `theory_sims2.js`, `theory.json` (Theory section), `registers.js` (open codes and solutions), `cube_engine.js` and `puzzles.js` (cube, sudoku), `math.js` and `math.json`, `channels.js` and `channels.json` (hidden and transmitted messages), `community.json`, `recovery.js` and `recovery/` (Recovering Data page, results and images), `help.js` (help, glossary, history pages), `history.json` (timeline data), `style.css`.

## scripts/, tests/, data/
`scripts/run_mysteries.py [names]` regenerates results. `scripts/extract_sources.py` extracts Beale numbers. `scripts/install_translation_models.py` installs Argos models. `scripts/check.py` runs all attack demos. `scripts/hunt.py --minutes N` seeds and runs the hunt. `scripts/benchmark_gpu.py` records GPU vs CPU. `scripts/train_classifier.py` trains the classifier. `scripts/find_problems.py` finds new codes. `scripts/harvest_publications.py` rebuilds publications. `scripts/check_community.py` rechecks links.
`tests/`: ciphers, source integrity, web API. `data/`: `corpora`, `sources`, `models`, `mysteries`, `results`.

Flow: `web.app` -> `ciphers.REGISTRY` -> `attacks` -> `kernels` + `languages`. `mysteries` use `validation` and save JSON that `casefiles` displays.
