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
| 13 | Scorers judged against the achievable key on Z340: word-aware and neural (GPU) | completed 2026-11-09 |
| 14 | Word-guided annealing (negative, control failed); readable gate now accepts very high word coverage | completed 2026-11-09 |
| 15 | Vigenere-family sweep of all letter texts; VIC teaching model (Purple deferred: no verified wiring) | completed 2026-11-09 |
| 16 | Benchmark on 170 AZdecrypt ciphers; rescan of stored attempts (animated bombe deferred) | completed 2026-11-09 |
| 17 | Le Figaro non-table systems: mirror, alternate word Caesars, letter insertion, rail, five-column (no new readings) | completed 2026-11-09 |
| 18 | Le Figaro OCR cleanup tested on known answers; Otsu chosen | completed 2026-11-09 |
| 19 | Period-step search for combined ciphers (controls 5 of 6, benchmark 0 of 84); bigram solver (control failed, 4-16%, parked) | completed 2026-11-09 |
| 20 | Le Figaro OCR choice by language score (16 of 56, ties best) | completed 2026-11-09 |
| 21 | Le Figaro OCR fusion with a French HMM (control 18 of 56, up from 16; majority vote 16); letter-digit attack (planted 40 of 40, no real ad read) | completed 2026-11-09 |
| 22 | Letter-digit ads: dictionary beam (planted 87 of 90, including 29 of 30 at 30 letters), 32 documented digit tables recovered, shared key matches table 2119 | completed 2026-11-09 |
| 23 | Sweep of 32 mixed and 11 numeric documented tables over 1,257 unsolved ads; 9 of the best readings checked by eye | completed 2026-11-09 |
| 24 | All machine-only digit leads checked against scans; decoder for numbers with clear letters (planted 40 of 40, junk 0) | completed 2026-11-09 |
| 25 | AIM dictionary code on Landais 1860: 19 of 27 published words at their references (random mean 0.09); both unsolved ads partly read | completed 2026-11-09 |
| 26 | AIM: 25 more known references from solved scans; automatic entry counter parked (12 of 52 exact); key entries counted by eye; 20 Jan 1882 ad read | completed 2026-11-09 |
| 27 | Ads grouped by table (14 tables with families); blank-cell inference (hidden cells: 55 of 69 answered correct, 121 tested); R=O in table 2119 with 15 of 15 held-out folds | completed 2026-11-09 |
| 28 | Six family leads checked against scans; numeric families cleaned (hidden cells 51 of 65 answered correct); irregular columnar and word anagrams (control 28 of 30, no real reading) | completed 2026-11-09 |
| 29 | Quagmire III fixed (keyword list 1,500 to 6,000; 30 of 30 random keys); 2119 and 2402 correspondences on the case page; symbol 1=B not supported by a dictionary test | completed 2026-11-09 |
| 29b | Live Devices page: discovery, read-only serial, camera, microphone and network monitors with stream analysis (user request) | completed 2026-11-09 |
| 30 | Signal Workbench: raw frames in 9 formats; automatic detection 51 of 80 (8 of 8 for 8-bit, RAW10, Kinect 11-bit, YUYV, RGB24; weak for 16-bit, RAW12, RGB565, Bayer), with manual controls; Live Devices stop buttons | completed 2026-11-09 |
| 30b | Byte-lane fingerprints (small high byte, noisy packed lane, two-apart smoothness): detection 75 of 80, up from 51; all formats 8 of 8 except RGB565 4 and Bayer 7 | completed 2026-11-09 |
| 31 | Logic Analyser: UART, SPI, I2C, CAN and 1-Wire decoders with automatic protocol, speed, parity, polarity and wiring; 50 of 50 on the control and on a fresh set | completed 2026-11-09 |
| 31b | USB low and full speed from sampled D+/D-: NRZI, bit stuffing, PID, CRC5/16 | pending |
| 31c | Codes in Nature expansion: how other organisms transmit and encode information (user request) | next |
| 32 | Signals part 3: line codes and links: Manchester, 4B5B, 8b/10b, HDMI/DVI TMDS, Ethernet frames and CRC-32, VGA/composite video timing from samples | pending |
| 33 | Signals part 4: radio and audio: IR remotes (NEC, RC5), DTMF, AFSK/Bell 202 and APRS, ADS-B Mode S (PPM, CRC-24), Morse from audio; barcodes and QR from images | pending |
| 34 | Transposition keys wider than 7 by hill-climbing, with controls | pending |

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

- A scorer that handles the planted error case is what real historic ciphers need: quadgram methods reward clean-looking wrong text.
- A better scorer does not by itself help search: polishing from wrong starts stays in local optima.

- A failed planted control stops the line: the Z340 numbers from that method were not interpreted.
- When several rounds of effort on one benchmark give shrinking returns, park it and move on.

- With short texts and periods up to 20, solvers overfit: require coverage plus a control at that length.

- Word coverage alone is fooled by dense solvers on short texts: the control gate is doing necessary work.
- A benchmark of real solved ciphers shows limits synthetic tests hide.

- Look at the source: seven 'decryptions' were plain French ads that the solver mapped back to themselves.
- A database's 'unsolved' label can include text that was never enciphered.

- Use the historical record: writers' documented systems beat general statistics on short ads.

- Independent routes to one answer beat a single score: a blind solve and a writer's own table reached the same KP text.
- When a parser finds 1 of 60 tables, do not trust the run: check counts before reading results.

- Adding search options raises the chance level: two short readings (H and one R ad) now fall below the stricter shuffled threshold, so keep their earlier evidence separate.

- A finder that adds names needs deduplication against what is already tracked, or lists fill with aliases.
- Keyword searches return off-topic papers: filter and spot-check them.

- Merging two OCR versions by best coverage slightly lowered the control (15 against 16 for Otsu alone): picking the most readable output can favour a wrong reading.
- Improving the input beat adding more cipher systems.

- Planted single-step transpositions are much easier than real benchmark ciphers: a passing control does not mean the method generalises.
- Bigram search over 676 values per symbol overfits at 1,000 letters; penalising letter frequencies did not rescue it.

- Page scripts share a global scope: one repeated name silently removes a whole file, so a test now forbids clashes.

## Emergent tasks
| ID | Note | Status |
|---|---|---|
| E2 | Sweep all 43 files in `data/sources/unsolved` | completed, rerun needed with the new verdict (Round 3) |
| E3 | Solvability oddity at long lengths | completed 2026-11-08: start temperature now scales with sqrt(length/400); 1500 letters, 26 symbols went from 30% to 93% (`scripts/tune_temperature.py`) |
| E4 | Z340: section A exact; section B breaks at position 99. Word and GRU scorers rank the achievable key above decoys, but word-model annealing (`kernels_word.py`, `scripts/z340_word.py`) failed its planted 10%-noise control at temperatures 0.4 to 10, and lowered accuracy from its starts. PARKED: little return from more runs; revisit with a better search idea such as crib-seeded or population methods | parked |
| E6 | Le Figaro: 60 documented tables plus Caesar, Vigenere and reversal on 613 ads; control 14 of 56 known ads. 12 flagged; writers' own tables independently confirm KP, MH and H. Candidates recorded in leads. Novelty unconfirmed. NEXT: better OCR for short ads, vowel-insertion and dictionary-code systems; ask the user before emailing the maintainer | in_progress |
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

## Added 2026-11-09: scan review and Recovering Data
- Seven flagged ads checked against scans: 3 readable (5 on 1 Jul 1882, 78 on 13 Nov 1884, 25 on 20 Sep 1894), 1 partly read (23), 1 unread (N), 2 rejected as abbreviated plain French. Novelty unconfirmed.
- OCR on 7 hand-read ads: rapidocr on Otsu 91%, tesseract on base 89%, worst setting 74%. Small sample.
- Reconstruction on 40 synthetic lines: 23% damaged, 96% after flatten, straighten, denoise and Wiener; enlarging and thresholding afterwards lost 2 points.
- Lesson: the `cipher_words` filter silently drops tokens with digits. 367 of 1,317 OCR-read ads have 3+ letter-digit tokens in a line. NEXT: attack these as mixed alphabets, Round 21 or later.
- Lesson: key-aware repair fixed both errors in the 1894 ad, but on controls fully repaired only 49 of 120 and wrongly changed 10 of 120 clean fragments. It is a suggestion tool, not an automatic fix.
- Lesson: a word-list null with no positive control is meaningless. The first UNIQUEMENT test returned 0.0 because the word was not in the list.

## Added 2026-11-09: Round 21
- Fusion flagged 16 ads, 3 new. Two are real candidates (7 Oct 1881, 11 Sep 1894). The third is a plain section heading.
- Lesson: a planted control can be much easier than the real target. The digit solver passed 40 of 40 at 90 letters, yet real ads are near 30 letters and mix in plain French.
- Lesson: `plain_coverage` must run on digit-bearing ads as well. The top digit hits were ordinary French with figures.
- New idea: HMM fusion could use confidence values from the OCR engines instead of equal votes.
- OCR benchmark rerun on 9 hand-read ads: tesseract on base 90%, rapidocr on Otsu 89%. The ranking changed from the 7-ad run, so the top settings are ties.

## Added 2026-11-09: Round 22
- Word breaks beat letter statistics on short text: dictionary beam 29 of 30 at 30 letters, where quadgram fitting read nothing.
- A parser that keeps only `c.isalpha()` silently dropped 32 documented tables. Count what a parser drops by category, not only in total.
- Independent confirmation: a key fitted from one ad agrees with table 2119 on 13 of 16 shared symbols. Held-out fitting was weak (1 of 5 splits; planted control found members in 5 of 6), so the table match is the evidence.
- Only 4 solved digit ads had OCR and none read well: OCR on digit tokens is the bottleneck. Digit-only words are lost by the token filter.
- Candidates 7 Nov 1881, 9 Mar 1879, 27 Apr 1884, 5 Jun 1883 recorded. Novelty unconfirmed.

## Added 2026-11-09: Round 23
- The documented tables read many ads the statistics could not. Check documentation before building solvers.
- The solved-ad control produced no hits (0 of 60), so it validates nothing here. Evidence is the shuffled null, the writer listings and reading each scan by eye.
- OCR limits: 2F's TIMBRE came out as FIMBRE because v was read as y. Ads mixing numbers and clear letters defeat the number extractor; CHERY read fully only by hand.
- Table cells can be blank in the database. Readings can suggest the missing values (15=J in table 2308), which would be new evidence for the maintainer.

## Added 2026-11-09: Round 24
- When an ad has clear text, shuffle only the cipher part. Otherwise the null is unfairly low; FL ads with null 0.5 were correctly exposed as mostly plain.
- Machine readings improved a lot by eye: CO RQG became COURAGE. Tests must assert what the table actually gives: MMARDON and RETROVERAS are printed, while PARDON and RETROUVERAS are inferences. OCR errors in digit words remain the main loss.
- New idea: writers appear to reuse a table across many ads (47, 42, CHERY). Group ads by table and writer to make the reading of each easier.

## Added 2026-11-09: Round 25
- A named book makes a dictionary code testable: known solutions pin the edition, the leaf offset and the column rule before any unsolved ad is touched.
- OCR entry counts drift, so a tolerance is needed for lookup. Exact entries need the page image (163a.17 = Demi, 258a.17 = Gelee).
- Eight control misses: short words such as je and pas, and columns the OCR lost (575a, 163a).

## Added 2026-11-09: Round 26
- The flush-left counter failed its control (12 of 52 exact, 19 within one), so it is parked. Line segmentation and OCR of single lines were both unreliable.
- Counting by eye is slow but reproduced every known position tried, so it is the method for the few references that matter.
- Small letters between AIM references look like nulls: the same pattern appears in solved ads where the database only supplies editorial words.

## Added 2026-11-09: Round 27
- Hiding known cells gives a real positive control for table repair. The method abstains on 43% of cells, and accuracy on the rest is 80%.
- Numeric families include plain ads with figures, because clear letters count as read. Mixed-table families are cleaner.
- A family view surfaces more than a per-ad search: the 2119 family repeats mari, ma femme and ma cherie across 1883 to 1887.
- New idea: known homophones (symbol 1 as X and B in table 2119) should be modelled as alternatives, not errors.

## Added 2026-11-09: Round 28
- A clean negative: irregular columnar widths 3 to 7 and word anagrams found no reading on 402 ads. Longer keys remain untested.
- Plain abbreviated French scores high on anagram tests, because real words are their own anagrams; a coverage filter of 0.35 was not enough for short words.
- The Workbench benchmark missed only Quagmire III (48 of 49 recovered at 18 seconds; 38 called readable, none wrongly).
- Lesson (Workbench): ranking by word coverage alone rewards overfitting on short text. Evidence depends on how many keys were searched: exact decodings have none, and unicity distance limits the rest.

## Added 2026-11-09: Round 29
- Benchmark misses can come from test keys outside the attack's search space: the Quagmire keygen drew keywords from deeper in the list than the attack searched. A wider list fixed it at about 2.6 seconds per attack.
- Letter-swap refinement of a near-miss alphabet lowered accuracy (0.45 to 0.39), because a better letter score did not track the true alphabet. Parked.
- Dictionary tests cannot judge abbreviated words. The 1=B evidence in table 2119 rests on reading by eye.

## Added 2026-11-09: Signals and devices (user request)
Teach and solve the decoding of data from electronic equipment, in the spirit of the kinect_interface project (libfreenect frames: 640x480 RGB, 16-bit depth from 11-bit packed raw). Every decoder must be tested on generated signals with known content, and every example must be generated or recorded from a cited source. No live hardware capture at first: the app reads files and pasted data, with simulations to show each layer (physical signal, line code, framing, checksum, payload).
- Live capture limits on macOS: USB and HDMI traffic cannot be read without kernel access, and packet capture needs administrator rights, so the page uses device-level streams (serial, camera, microphone) and system counters. A Kinect could be read through libfreenect, which is installed.

## Added 2026-11-09: Round 30
- A single smoothness score favours formats that average bytes together, so wrong formats can look smoother than the true one. Per-lane checks fixed RGB24 and YUYV, but RAW12, 16-bit and Bayer need format-specific bit-field models.
- Find the row length in bytes before choosing a format: compare against lengths 60 bytes away, a multiple of every interleave, so channel layout cannot fake a row.
- A half-stride Bayer rule made the control worse (15 of 80) and was removed. Detection is shipped with its per-format reliability shown on the page, not one headline number.

## Added 2026-11-09: Round 30b
- Structural fingerprints beat a generic score: 12-bit data in 16 bits leaves one byte below 16, packed low bits form one noisy lane, and a Bayer mosaic is far smoother two pixels apart.
- Generated test data must have realistic noise. Zero low bits made RAW12 and 16-bit look unlike any real sensor, twice.

## Added 2026-11-09: Sound Lab
- BirdNET's confidence is not a probability of being right: runner-up species reached 0.83 on a correctly identified robin. Show several candidates.
- A null comparison caught a bug, not a weakness: the baseline function called the identifier, which called the baseline, so it recursed forever.
- Ideas: compare song sequences between individuals (dialects) by n-gram distance; whale and bat calls; a live microphone mode reusing the Live Devices monitor.

## Added 2026-11-09: Round 31
- Identification must weigh how hard each protocol's own checks are to pass by chance. UART's two framing bits per byte let it "decode" SPI and CAN lines; a CAN CRC-15 almost never passes by luck.
- A test that only checks the common case hides bugs: identification skipped chip-select lines because they change only twice, and UART assumed no parity. Both showed up only in the mixed control.
- A held-out set matters even for generated data: rules tuned on seed 9 were rechecked on seed 21 after every change.

