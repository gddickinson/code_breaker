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
| `translate.py` | Offline translation via Argos (no Latin model) | `translate` |
| `validation.py` | False-positive controls; three-gate verdict | `null_test`, `positive_control`, `coverage`, `verdict` |
| `leads.py` / `litedb.py` | Leads database and its apsw wrapper (Anaconda's sqlite3 is broken here) | `connect`, `add_lead`, `add_avenue`, `summary` |
| `accel.py` | Optional GPU routes, chosen by benchmark | `device`, `best_route`, `book_scan`, `enigma_ic_scan`, `population_anneal` |

## codebreaker/ciphers/ (each `add(...)` fills `REGISTRY`)
`base.py` Cipher, Param, DEMO_PLAIN · `runner.py` attack_demo · `columns.py` columnar helpers ·
`monoalphabetic.py` · `polyalphabetic.py` · `polygraphic.py` (also fractionating) · `transposition.py` ·
`machines.py` (Enigma, Jefferson, Lorenz model, book, homophonic) · `modern_symmetric.py` · `modern_public.py`

## codebreaker/attacks/
`classical.py` general solvers, taking decrypt functions so that ciphers can import it · `modern.py` worked attacks on weak or misused cryptography

## codebreaker/mysteries/
`beale.py`, `dagapeyeff.py`, `tamam.py`, `kryptos.py`, `voynich.py`: each has `run()` returning JSON saved in `data/results/`.
`zodiac.py`, `dorabella.py`, `sweep.py`, `solvability.py`, `scriptlab.py`: further analyses. `corpus.py` loads symbols per code; `catalog.py` seeds the leads database; `hunter.py` runs avenues and records attempts.
`casefiles.py` case metadata and `case()`; `casefile_sections.py` and `casefile_extra.py` turn results into displayed sections.

## codebreaker/web/
`app.py` routes under `/api`. `static/`: `core.js` (helpers, router), `library.js`, `tools.js` (workbench, translate, challenge), `mysteries.js`, `leads.js` (Lead Board), `charts.js` (SVG charts, background), `sim_engine.js` (pure simulation logic, node-testable), `sim_enigma.js`, `sim_mech.js`, `sim_trace.js`, `style.css`.

## scripts/, tests/, data/
`scripts/run_mysteries.py [names]` regenerates results. `scripts/extract_sources.py` extracts Beale numbers. `scripts/install_translation_models.py` installs Argos models. `scripts/check.py` runs all attack demos. `scripts/hunt.py --minutes N` seeds and runs the hunt. `scripts/benchmark_gpu.py` records GPU vs CPU.
`tests/`: ciphers, source integrity, web API. `data/`: `corpora`, `sources`, `models`, `mysteries`, `results`.

Flow: `web.app` -> `ciphers.REGISTRY` -> `attacks` -> `kernels` + `languages`. `mysteries` use `validation` and save JSON that `casefiles` displays.
