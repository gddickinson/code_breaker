# Session log

## 2026-11-08: first build
Built the app: 61 ciphers, each with a worked example and an attack or misuse demonstration. Language models for six languages, offline translation for fr, de, it, es.

Mystery results (see Mystery Lab):
- Beale 2 verified against the Declaration. The Beale 1 alphabetical run was reproduced (14 letters; 0 of 2,000 shuffles matched). Seven key texts gave no signal for B1/B3. Homophonic attempts are inconclusive: the solver recovers only about 7% at that symbol density.
- D'Agapeyeff: grid structure confirmed. No signal in 90 language and regular-null combinations, and the control recovered 100%.
- Tamam Shud: fits English initials. A 7-letter Rubaiyat match (p about 0.25% against English-initial blocks) is an unconfirmed lead.
- Kryptos: K1-K3 solved by our tools. 270 of 288 periodic K4 models eliminated; periods 27-29 untestable from the clues.
- Voynich: conditional entropy 2.34 against 3.31-3.58 for six languages; rules out simple substitution of those languages under EVA.

Not done: Dorabella and the Zodiac ciphers (no verifiable transcription found), no Latin translation model, M-209 and Purple not implemented, no git repository created. The Mac mini was not used.

## 2026-11-08: second session (upgrade round 1)
Created the private GitHub repository. Added ROADMAP.md with upgrade rounds and lessons learned.

- Homophonic solver rewritten with incremental scoring: 9 of 9 keys, about 4 s.
- Benchmarks and data: Z408 read at 92%; Z340 period-19 structure recovered, letters not read. Dorabella attempted across three transcriptions. 36 further unsolved cryptograms swept.
- Verdict tightened after the sweep produced false "candidate signals": results must now also read as text.
- Machine simulators: Enigma, Lorenz, Jefferson, Alberti, scytale, grille, rail fence, plus Vigenere and Playfair traces. All cross-checked against the Python ciphers.
- GPU support added and benchmarked; it loses all three search loops, so they stay on CPU (`accel.best_route`).
- Leads database (`data/leads.db`): 117 codes, 48 with ciphertext, 9,629 avenues. `scripts/hunt.py --minutes N` works through them.
- Lost-script lab: Phaistos Disc, Linear A, Liber Primus. Cyberpunk theme and new charts.

No cipher has been solved. Next: Round 2 in ROADMAP.md.

## 2026-11-08: Round 2 started (30-minute timer running)
Homophonic temperature now scales with length. Z340 diagnostics show section A is exact and section B breaks near reading position 99. Resume at E4 in ROADMAP.md, then rerun the sweep, Dorabella and D'Agapeyeff under the new verdict.

Hunter's first readable result: the 1896 Le Figaro ad reads as coherent French when reversed and solved as a substitution. Reproduced from independent seeds and read by eye. Whether it was already solved is not yet known (E6).

## 2026-11-09: Round 2 complete
Hunts reached 1,017 attempts. Reran Zodiac, Dorabella, D'Agapeyeff, Tamam Shud and the sweep under the three-gate verdict: Sweep 16 no evidence, 12 inconclusive, 7 structure only. Dorabella is structure only. Z340: reading verified on 286 of 340 positions; solver 32% there. Le Figaro database located but needs a form submission (E6, waiting on the user). Next: Round 3.

## 2026-11-09: Round 3 complete
Beale forensics: neighbouring numbers correlate at 0.62 in B3 and 0.25 in B1, against 0.05 in the genuine B2. Alternative key rules give no signal. D'Agapeyeff is exactly 14x14; 138 reordering tests found nothing readable. Next: Round 4.

## 2026-11-09: Round 4 complete
K4: 58.9M two-layer settings, 0 survivors; autokey and Hill excluded; control found. Tamam Shud mnemonic search of six books found nothing. Next: Round 5.

## 2026-11-09: Round 5 complete
Voynich generator lab: noise floor 0.37, no candidate reaches it; verbose cipher matches H2 but not word length. Liber Primus: known pages 56 and 57 recovered as controls; other pages flat. Next: Round 6.

## 2026-11-09: Round 6 complete
CNN cipher-type classifier over 41 classes: top-1 62%, top-3 80%, family 86% on unseen keys and texts. Autobreak solved 21 of 24 hidden ciphers. GPU trained 5.5x faster than CPU. `data/models/classifier.pt` is not in git: rebuild with `scripts/train_classifier.py`. Next: Round 7.

## 2026-11-09: Round 7 complete
Added the Bletchingley pigeon message (statistically random, consistent with a one-time key) and the Rongorongo corpus (10.5% of 4-glyph runs recur across tablets, against 0.03% shuffled). Shugborough recorded as too short. Indus and Debosnys need transcribed data. Next: Round 8.

## 2026-11-09: Round 8 complete
Added a working bombe: from a 32-letter crib it found rotors, start and all 8 plug pairs with one stop in about 3 seconds. Added Quagmire I and II, Nicodemus, Fractionated Morse, Slidefair, Gromark, Alberti and the M-209 model (69 systems). Classifier retrained: 48 classes, top-1 58%, family 83%; Autobreak 21 of 24. Next: Round 9.

## 2026-11-09: Round 9 complete
Live annealer page (`#/machine/anneal`), checked to break a substitution under node. Lead Board now has a hunter feed, a verdict bar, an attempts-per-hour chart and a lead timeline. Next: Round 10, back to the hardest targets.

## 2026-11-09: Round 10 complete
Beale: an honest narrow-window encoder reproduces the B3 correlation, so the hoax inference is withdrawn. Voynich: two improved generators each match predictability and word length but fail vocabulary or Zipf. Hunter gains reverse-plus-column avenues. Classifier now multilingual. Z340: the search outscored the true text, so the language model is the limit. Next: Round 11.

## 2026-11-09: Round 11 complete
Z340: the 5-gram model ranks the true text above found decoys; long runs reach 44% on verified positions (top-scoring run 39%). Rongorongo alignment passes its control but finds nothing above the shuffled level. Short-passage Beale keys rejected as equivalent to document offsets. Next: Round 12.

## 2026-11-09: Round 12 complete
Correction to Round 11: the 5-gram model does not prefer the correct key on Z340. The best single key matches the published text on 90% of letters and scores -1687, below decoys at -1595. Longer searches plateau at 41-44%. D'Agapeyeff digit transpositions (372 tests) and Liber Primus running keys found nothing. Autobreak now has fallback attacks. Next: Round 13.

## 2026-11-09: Round 13 complete
GPU-trained GRU (final loss 1.34) and a word-segmentation scorer both rank the best achievable Z340 key above all 28 decoys, and handle 10% errors; quadgram and 5-gram models fail both. GRU-guided polishing did not improve accuracy (best 42%), so search needs to anneal under the better scorer. Next: Round 14.

## 2026-11-09: Round 14 complete
Word-model annealing failed its planted control and did not improve Z340, so its Z340 results were not used and that benchmark is parked. The three-gate verdict now accepts very high word coverage, for real ciphers with errors. Next: Round 15, changing target.

## 2026-11-09: Round 15 complete
Vigenere, Beaufort, Variant and Porta attacks on all 16 letter-only unsolved texts, forwards and reversed, in six languages: nothing readable. Added a VIC-style teaching model (70 systems) and retrained the classifier. Next: Round 16.

## 2026-11-09: Round 16 complete
Benchmark on 170 solved ciphers at the strict 55% coverage line: substitution 4 of 65, transposition 1 of 14, bigram 1 of 7, combined 0 of 84. Coverage undercounts partial reads. Rescanning about 5,000 stored attempts found no missed partial solve; other high-coverage readings are overfit word salad. Next: Round 17.

## 2026-11-09: Help page and history timeline (user request)
Added a Help page with an app guide, how to read verdicts and a 37-term glossary, and a 37-event History timeline with a page for each event linking to its ciphers, machines and case files. A test checks every internal link. Le Figaro: the user approved querying the database; index done (4,054 ads, 1,257 unsolved), images downloading; our 1896 ad was already solved there, so it is a re-solve and not a discovery.

## 2026-11-09: Latin translation (user request)
Integrated Helsinki-NLP/opus-mt-mul-en for Latin. Scored on Caesar Book I, first 18 chapters, against a published translation: word overlap 0.418 with the right chapter and 0.285 with a wrong one. A Latin-English community T5 scored 0.255 and 0.23 and repeats itself, so it was rejected. Output is labelled a rough draft.

## 2026-11-09: Le Figaro hunt
OCR usable on 73 of 1,257 unsolved ads. 12 were plain French, so an unchanged-text check was added. The ad of 15 July 1896 passes all three gates as a Caesar +1 candidate (signed Rysck). Ad KP of 6 November 1896 reads clearly but misses the word gate, so it is not counted as solved. Novelty unconfirmed; nothing has been emailed to the maintainer. Latin casing bug fixed.

## 2026-11-09: Le Figaro documented systems
Unfiltered OCR on all 1,317 images. Caesar (with and without W), Vigenere keys and reversals, applied to 613 unsolved ads with at least 20 letters. Control recovered 9 of 56 known ads. Six ads recorded as candidate readings after checking scans, including a second ad by Rysck. Novelty unconfirmed; nothing sent to the maintainer.

## 2026-11-09: Le Figaro documented tables
Parsed 60 substitution tables and their writers from the database. Control rose to 14 of 56 known ads. KP's ad decodes with the table listed only for KP, matching the blind solve. MH and H also matched tables linked to them. New candidates recorded as needs_review, several partly read. Nothing emailed.

## 2026-11-09: Open Codes and Solutions pages (user request)
Added `#/open`, listing 119 open entries with search and filters, and `#/solutions`, separating possible solutions by evidence tier from known solutions our tools reproduced. Data comes from the leads database, so both update as leads change.

## 2026-11-09: How It Works page (user request)
Added illustrated pages for frequency analysis, key-length detection and column rebuilding, and simulations of AES rounds, the ECB image leak, the avalanche effect, a Feistel network, modular key exchange, RSA arithmetic and a simplified Colossus. AES is checked against a FIPS vector and PyCryptodome; S-DES against the Python cipher.

## 2026-11-09: Round 17 complete
Added the Le Figaro systems that are not simple tables. No new readings, and the known-answer control stayed at 14 of 56. The larger search raised the shuffled threshold, so the H and 14 Aug 1879 R ads no longer clear it on this measure; their earlier evidence stands in the leads. The limit is OCR. Next: Round 18.

## 2026-11-09: Community, Puzzles, Maths, Publications, How Secrets Travel (user requests)
Added Community links (26 checked), Puzzles (3D Rubik's cube with Kociemba solver, sudoku), 14 maths topics with tested worked examples, a Publications table of 1,264 Crossref records, a page on steganography and transmission with a working image demo, and grouped navigation. `scripts/find_problems.py` adds new codes from Wikipedia categories and the AZdecrypt list, and added 11 new entries. A session timer runs it every 6 hours.

## 2026-11-09: Round 18 and user requests
Otsu thresholding plus a character whitelist recovered 16 of 56 known ads, against 14. Merged with earlier OCR across all ads: 641 tested, control 15 of 56, 13 flagged, including the KP ad automatically and a new ad by writer 5 (24 Dec 1882).
Added camera and photo reading for the cube and sudoku, Codes in Nature with a genetic-code translator and waggle dance model, seven more puzzles (Mastermind, Lights Out, sliding tiles, Hanoi, N-Queens, Knight's Tour, Nonogram) and Learn to Solve guides. Solvers and quoted algorithms are tested.

## 2026-11-09: Round 19 complete
Period detection from repeated pairs found all 6 planted transpositions, and 5 were solved at 93-99%. None of the 84 AZdecrypt combined benchmark ciphers reached readable coverage. The bigram solver failed its control (4-16%) at every setting tried, so it is parked. Next: Round 20.

## 2026-11-09: Guide illustrations (user request)
Every step of all 10 Learn to Solve guides now has a code-drawn illustration: isometric cube stages, worked sudoku examples, computed Lights Out boards, and diagrams for the other puzzles and ciphers.

## 2026-11-09: Round 20 and Theory section
Choosing OCR by language score ties the best control result, 16 of 56. Added a Theory section of 13 topics: entropy, Huffman and Shannon-Fano, randomness tests, LFSRs and Berlekamp-Massey, Monte Carlo, MCMC, belief propagation, hidden Markov models, variational inference, Shor's algorithm, differential cryptanalysis, Pollard's rho and an attack catalogue. Each algorithm is tested. Next: Round 21, using these methods on the Le Figaro OCR.

## 2026-11-09: Scan review, Recovering Data page, cube scanner
Checked the 7 new flagged Le Figaro ads by eye: 3 readable, 1 partly read, 1 unread, 2 rejected. Leads, facts and an avenue are recorded per ad. Added `#/recovery` with real scans, an interactive threshold, measured OCR comparison, image reconstruction with known answers, error spread and key-aware repair. The cube scanner now lets you choose the side to photograph, drag sides to swap them, rotate a side, and shows real read colours; checked with real mouse events in headless Chrome. A 5-minute hunt ran. Next: Round 21.

## 2026-11-09: Round 21
OCR fusion with a French letter HMM recovered 18 of 56 known ads, against 16 before. On unsolved ads it flagged 16, of which 3 are new; 2 of those are candidates after checking scans (7 Oct 1881 and 11 Sep 1894), and one is a plain heading. The letter-digit solver passed 40 of 40 planted controls but read no real ad among 467, so that family stays open. A spot check found 3 of 4 letter-digit ads are real mixed-symbol ciphers. AIM and irregular transpositions moved to Round 22.

## 2026-11-09: Round 22
A dictionary beam search over word breaks solved 29 of 30 planted letter-digit ads at 30 letters. Recovered 32 documented digit tables that the parser had been dropping. A key fitted from one ad matched documented table 2119 on 13 of 16 shared symbols. Four new candidates are recorded after checking scans. Held-out key fitting was weak and is reported as such. AIM and irregular transpositions moved to Round 23.

## 2026-11-09: Round 23
Swept 32 mixed and 11 numeric documented tables over all 1,257 unsolved ads. Added leads for the strong results; 9 were checked against scans and all are real ciphers, including the CHERY ad of 19 Oct 1889 and an ad naming rue Miromesnil. The rest are marked as machine readings. The solved-ad control produced no hits, so it validates nothing. Novelty unconfirmed. AIM and irregular transpositions moved to Round 24.

## 2026-11-09: Problem finder check
Ran `scripts/find_problems.py`. It added no codes (170 tracked before and after), so there were no duplicates or aliases to remove and no ciphertext was added.

## 2026-11-09: Round 24
Checked all 7 machine-only digit-table leads against their scans; all are real ciphers and their readings were improved by hand. Added a decoder for numbers mixed with clear letters, with a null that shuffles only the numbers (planted 40 of 40, junk 0). It found a second CHERY ad (8 Nov 1889). Two new leads; novelty unconfirmed. AIM and irregular transpositions moved to Round 25.

## 2026-11-09: Round 25
Tested the AIM dictionary code on the 1860 Landais Petit dictionnaire from archive.org. On four solved ads, 19 of 27 published words sit at their references, against a random mean of 0.09 and maximum 2. Both unsolved AIM ads are partly read and recorded as candidates. The dictionary source files are not committed. Irregular transpositions moved to Round 26.

## 2026-11-09: Round 26
Read the five remaining solved AIM scans, adding 25 known references. An automatic page-image entry counter failed its control (12 of 52 exact) and is parked. Counting by eye reproduced the 4 known positions checked. The 20 Jan 1882 ad now reads as a coherent message about frost and hunting, and the 16 Feb 1882 ad is further read. Both remain candidates. Blank-cell inference and irregular transpositions moved to Round 27.
The OCR-based dictionary control on the enlarged set is now 44 of 54 published words at their references (random mean 0.22, maximum 3).

## 2026-11-09: Round 27
Grouped ads by documented table and tested blank-cell inference: with known cells hidden it answered 69 of 121 and 55 were right. Proposed R=O for table 2119 (15 of 15 held-out folds). Checked four more family ads against scans, including a New Year greeting of 30 Dec 1883; six more are machine readings. Irregular transpositions moved to Round 28.

## 2026-11-09: Workbench crack and submissions (user requests)
Crack it now streams each stage: text inspection, plain-text and encoding checks, statistics, rule and neural guesses, worked traces (frequency, Caesar sweep, Vigenere columns, annealing), then every attack across six languages within a time budget. The best reading is tested against shuffled letters. Codes the Workbench cannot read can be sent to the hunter; the server refuses a code unless a crack finished without a readable result.

## 2026-11-09: Round 28
Checked six more family ads against scans, all real and improved by hand. Numeric families now exclude plain ads with figures. Irregular columnar and word-anagram searches on 402 unsolved ads found nothing, with the columnar control at 28 of 30. Next: Round 29.

## 2026-11-09: Workbench short-text fixes (user report)
A Base64 message was decoded correctly but outranked by a meaningless short Italian reading. Exact decodings that read as language now end the crack; decoded text that is not language is attacked in layers. Readings from methods whose key space is too large for the text length are marked as not trusted and cannot be reported as cracked.

## 2026-11-09: Hunter support for Workbench submissions (user request)
Submissions now have exact encodings removed (Base64, hex, binary, character codes, up to three layers), and the hunter works on the inner text, with the original kept. Each submission also gets a "crack" avenue that reruns the full Workbench pipeline with more time at each level (45 s, rising to a 150 s cap). Its readable results go to the Lead Board as needing review, labelled as weaker than the three-gate verdict.

## 2026-11-09: Round 29
Fixed the Workbench's only benchmark miss: Quagmire III now searches 6,000 alphabet keywords and recovered 30 of 30 random keys. An alphabet-swap refinement was tried and dropped. The 2119 (17 ads, 13 checked) and 2402 (16 ads, 10 checked) families are now dated correspondences on the Le Figaro case page. A dictionary test did not support symbol 1=B, so that stays an eye-reading. Wider transposition keys moved to Round 30, together with the user's signals and devices request.

## 2026-11-09: Live Devices (user request)
New Tools page, Live Devices. It lists everything attached (61 devices found: USB, 3 cameras, audio, displays, Bluetooth, serial ports, network) and monitors live streams read-only: serial ports with automatic format recognition (NMEA with checksums, JSON, CSV readings, AT commands, key-value, fixed binary packets, random or encrypted data), cameras and microphones analysed in the browser (brightness, colour, motion, sharpness, QR codes; spectrum, loudest frequency, DTMF keys), and network throughput per interface. Simulated serial devices allow testing without hardware. Checked in headless Chrome with fake media devices.

## 2026-11-09: Round 30
Added the Signal Workbench: rebuild raw camera and sensor frames from bytes, with generated examples (Kinect depth, webcam YUYV, RAW10, RGB565, Bayer, 16-bit). Automatic detection is right for format and width in 51 of 80 generated cases, with all 8 correct for 8-bit, RAW10, Kinect 11-bit, YUYV and RGB24, and weak for 16-bit, RAW12, RGB565 and Bayer, so the page shows that reliability and offers manual format, width, offset and Bayer controls. Live Devices monitors (serial, camera, microphone, network) now each have their own stop button, checked in Chrome. Device and signal routes moved to web/routes_devices.py to keep app.py under 500 lines.

## 2026-11-09: File Inspector (user request)
Incorporated the GUI-free core of the user's textview project (identification by magic bytes, format database, security scan, Blender header and document readers) as codebreaker/files/, with credit in each file. Changed one rule: a definite signature now wins over a misleading extension, which may only refine a container. Added web views for images, text and tables, archives, SQLite, NumPy, MATLAB, PDF and WAV, plus forensic views (entropy map, strings, embedded file signatures), and hand-off buttons to the Workbench and Signal Workbench. Readers needing pyarrow, h5py, cryptography or openpyxl are not included yet.

## 2026-11-09: Round 30b
Raw-frame detection now checks byte-lane fingerprints before smoothness, raising the control from 51 to 75 of 80. All formats are 8 of 8 except RGB565 (4) and Bayer (7). Test frames now carry realistic noise in packed low bits.

## 2026-11-09: File Inspector readers (user request)
Installed pyarrow, h5py, netCDF4, cryptography and openpyxl (pinned in requirements.txt) and added textview's Parquet, HDF5/NetCDF, spreadsheet and certificate readers without their Qt pickers. Each is tested on a real generated file.

## 2026-11-09: Sound Lab and birdsong (user request)
Added a Sound Lab and a Birdsong group in Codes in Nature. From the user's bird_sound_analyzer project it takes BirdNET species identification (now on the lightweight ai-edge-litert runtime, without TensorFlow) and adds YAMNet for 521 general sound classes. Songs are segmented into syllables, typed, and measured as a symbol sequence with entropy. Controls: synthetic songs with known grammar (all syllables found; types agree for about 85%); five Wikimedia Commons recordings (blackbird x2, robin x2, tawny owl), all named correctly first by BirdNET, with runner-ups sometimes above 0.6, so results are shown as candidates. The page can analyse examples, uploaded files or 10 seconds from the microphone.

## 2026-11-09: Round 31
Added a Logic Analyser (Tools): UART, SPI, I2C, CAN and 1-Wire decoders on sampled wires, with baud, parity, polarity, SPI mode, CAN bit rate and wiring found automatically and every decoder ranked by how strongly its checks pass. The control of 50 generated captures with glitches, and a fresh set of 50, both decode protocol and bytes 50 of 50. CSV exports from sigrok or Saleae can be opened. USB moved to Round 31b.

