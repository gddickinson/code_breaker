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
| `crack.py` / `crack_steps.py` / `crack_worker.py` | Workbench crack: streamed stages, every attack across languages, shuffled-text verdict | `crack`, `plan`, `verdict` |
| `submissions.py` | Workbench submissions: saved text, encodings peeled, duplicate check, avenues (including a full "crack" avenue) for the hunter | `submit`, `peel`, `listing` |
| `kernels_t.py` | Numba hill-climbing for wide columnar keys, both directions, and joint key-plus-substitution annealing | `columnar_encrypt`, `climb_wide`, `anneal_joint` |
| `lm.py` / `kernels_n.py` | GRU language model on the GPU, and 5-gram annealing | `train`, `scores`, `anneal5`, `table5` |
| `accel.py` | Optional GPU routes, chosen by benchmark | `device`, `best_route`, `book_scan`, `enigma_ic_scan`, `population_anneal` |

## codebreaker/devices/ (Live Devices page)
`discover.py` finds USB, camera, audio, display, Bluetooth, serial and network devices from system_profiler, pyserial and psutil · `streams.py` read-only serial and network-rate streams · `analysis.py` structure of unknown byte streams (entropy, NMEA, JSON, CSV, AT, key-value, fixed binary packets) · `sim.py` simulated GPS, sensor and packet devices. Front end: `devices.js`, `devices_media.js` (camera and microphone analysed in the browser).

## codebreaker/signals/ (Signal Workbench page)
`raw_formats.py` camera and sensor pixel formats (8/16-bit, RAW10, RAW12, Kinect 11-bit, YUYV, RGB24, RGB565, Bayer) as encoders and decoders · `raw_detect.py` row length from byte differences, then the smoothest format; generated scenes and the control · `service.py` previews, examples and per-format reliability. Front end `signals.js`. Logic Analyser: `logic_synth.py` (generated UART, SPI, I2C, CAN, 1-Wire captures), `logic_decode.py` (UART with baud, parity and polarity found; SPI with mode; I2C), `logic_bus.py` (CAN with unstuffing and CRC-15; 1-Wire), `logic_usb.py` (USB low and full speed: NRZI, bit stuffing, PIDs, CRC5 and CRC16), line codes: `eightb10b.py`, `tmds.py`, `linecode.py` (Manchester, NRZI, 4B5B, Ethernet frames with CRC-32), `linecode_service.py` (identification and control); front end `linecodes.js`, video: `video.py` (VESA/CEA mode table, VGA and composite generators and decoders, refusal of irregular sync or unmatched timing), `video_service.py`; front end `video.js`, audio codes: `audio_codes.py` (DTMF with Goertzel, Morse with hysteresis and adaptive unit), `ax25.py` (APRS: AX.25, HDLC, NRZI, Bell 202 AFSK, CRC-16/X-25, soft bit clock), `audio_service.py`; front end `audio_codes.js`; aircraft `modes.py` (Mode S CRC-24 with single-bit repair, identity, altitude, CPR position, velocity, pulse-position signal) and `adsb_service.py` (traffic scenes, tracker, control), front end `adsb.js`; `barcodes.py` (EAN-13 drawing and scanline reading with check digits, QR through OpenCV, other symbologies through zxing-cpp), also used by the File Inspector; `symbology.py` (Barcodes & QR page: 14 symbologies made and read with zxing-cpp, QR anatomy and error levels with segno, EAN check-digit steps, blot damage test by error level; routes `web/routes_codes.py`, front end `barcodes.js` and `barcodes_info.js`); infrared `ir.py` (NEC, RC5) in the Logic Analyser, `logic_service.py` (protocol identification weighted by check strength, CSV import, control); front end `logic.js`. Device and signal routes are in `web/routes_devices.py`.

## codebreaker/files/ (File Inspector page)
Adapted from the textview project: `file_inspector.py` (magic bytes, extension hints, encoding, hex preview; magic now wins over a misleading extension), `format_db.py` (data/files/file_formats.json), `security_scanner.py`, `blend_inspector.py`, `document_extract.py`. New: `readers.py` (image, text, table, archive, SQLite via apsw, NumPy, MATLAB, PDF, WAV views; pickle is never loaded), `readers_data.py` (Parquet/Feather/Arrow, HDF5/NetCDF, Excel/ODS, certificates and keys through textview's `parquet_loader`, `hdf5_loader`, `spreadsheet_loader`, `cert_loader`), `carve.py` (entropy map, strings, embedded signatures), `service.py`. Routes in `web/routes_files.py`; front end `files.js`.

## codebreaker/sound/ (Sound Lab page; birdsong in Codes in Nature)
`audio.py` decode and resample · `song.py` spectrogram, syllable segmentation, syllable types, the song as a sequence with entropy · `identify.py` BirdNET 2.4 on ai-edge-litert (the approach of the user's bird_sound_analyzer project) and YAMNet (data/models/yamnet, not committed), each with a noise baseline · `synth.py` songs with a known grammar for controls · `service.py`. Reference recordings: data/sources/sounds/sources.json (Wikimedia Commons, CC BY-SA; audio not committed). Routes `web/routes_sounds.py`; front end `sounds.js`.

## codebreaker/ciphers/ (each `add(...)` fills `REGISTRY`)
`base.py` Cipher, Param, DEMO_PLAIN · `runner.py` attack_demo · `columns.py` columnar helpers ·
`monoalphabetic.py` · `polyalphabetic.py` · `polygraphic.py` (also fractionating) · `transposition.py` ·
`machines.py` (Enigma, Jefferson, Lorenz model, book, homophonic) · `aca.py` (Quagmires, Nicodemus, Fractionated Morse, Slidefair, Gromark, Alberti, M-209) · `modern_symmetric.py` · `modern_public.py`

## codebreaker/attacks/
`classical.py` general solvers, taking decrypt functions so that ciphers can import it · `modern.py` worked attacks on weak or misused cryptography

## codebreaker/mysteries/
`beale.py`, `dagapeyeff.py`, `tamam.py`, `kryptos.py`, `voynich.py`: each has `run()` returning JSON saved in `data/results/`.
`zodiac.py`, `dorabella.py`, `sweep.py`, `solvability.py`, `scriptlab.py`: further analyses. `corpus.py` loads symbols per code; `catalog.py` seeds the leads database; `hunter.py` runs avenues and records attempts.
`recovery.py` and `recovery_images.py`: measured OCR, error spread, key-aware repair and image reconstruction for the Recovery page (`scripts/run_recovery.py` regenerates them). `figaro_fusion.py` (OCR confusion networks and French HMM), `figaro_digits.py` (letter-digit alphabets). `figaro_digit_words.py` (dictionary beam for letter-digit ads), `figaro_digit_family.py` (shared keys and documented digit tables). `figaro_digit_sweep.py` (all documented digit and numeric tables over every ad). `figaro_numeric_mixed.py` (numbers with clear letters; number-only nulls). `aim_dictionary.py` (AIM dictionary code on Landais 1860; source files in data/sources/aim are not committed). `aim_pages.py` (flush-left entry counter on page images, parked: failed its control). `figaro_table_cells.py` (ads grouped by table; blank-cell inference). `figaro_transposition.py` (irregular columnar grids and word anagrams). `figaro_wide.py` (columnar keys of width 8 to 16 by hill-climbing with `kernels_t.py`, both directions, controls and shuffled nulls). `figaro_layered.py` (routes and columnar keys followed by substitution; joint anneal). `figaro_plainness.py` (abbreviated plain French filter). `figaro_vta.py` (V. T. A. 1877: pooled homophonic key, held-out test, controls; transcription in data/sources/figaro/vta_transcription.json). `figaro_correspondence.py` (table families as dated correspondences; alternate symbol test). `casefiles.py` case metadata and `case()`; `casefile_sections.py` and `casefile_extra.py` turn results into displayed sections.

## codebreaker/web/
`app.py` routes under `/api`. `static/`: `core.js` (helpers, router), `library.js`, `tools.js` (workbench, translate, challenge), `mysteries.js`, `leads.js` (Lead Board), `charts.js` (SVG charts, background), `sim_engine.js` (pure simulation logic, node-testable), `sim_enigma.js`, `sim_mech.js`, `sim_trace.js`, `sim_bombe.js`, `sim_anneal.js`, `sim_how.js`, `sim_computer.js` (How It Works pages), `sim_crypto_engine.js` (pure AES, S-DES, Colossus logic), `puzzles_scan.js` (camera and photo reading), `puzzles_engine.js` and `puzzles_more.js` (extra puzzles), `tutorials.js`, `tutorials.json` and `guide_diagrams.js` (guides and their illustrations), `biology.js` and `biology.json` (codes in nature), `theory_engine.js` (pure algorithms), `ecc_engine.js` and `ecc_sims.js` (error correction: parity, CRC, Luhn, ISBN, Hamming(7,4), Reed-Solomon over GF(256), convolutional codes with Viterbi, BER against Shannon capacity), `theory.js`, `theory_sims2.js`, `theory.json` (Theory section), `registers.js` (open codes and solutions), `cube_engine.js` and `puzzles.js` (cube, sudoku), `math.js` and `math.json`, `channels.js` and `channels.json` (hidden and transmitted messages), `community.json`, `workbench_crack.js` (live crack steps, submissions), `recovery.js` and `recovery/` (Recovering Data page, results and images), `help.js` (help, glossary, history pages), `history.json` (timeline data), `style.css`.

## scripts/, tests/, data/
`scripts/run_mysteries.py [names]` regenerates results. `scripts/extract_sources.py` extracts Beale numbers. `scripts/install_translation_models.py` installs Argos models. `scripts/check.py` runs all attack demos. `scripts/hunt.py --minutes N` seeds and runs the hunt. `scripts/benchmark_gpu.py` records GPU vs CPU. `scripts/train_classifier.py` trains the classifier. `scripts/find_problems.py` finds new codes. `scripts/harvest_publications.py` rebuilds publications. `scripts/check_community.py` rechecks links.
`tests/`: ciphers, source integrity, web API. `data/`: `corpora`, `sources`, `models`, `mysteries`, `results`.

Flow: `web.app` -> `ciphers.REGISTRY` -> `attacks` -> `kernels` + `languages`. `mysteries` use `validation` and save JSON that `casefiles` displays.
