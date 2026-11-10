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

## 2026-11-09: Codes in Nature expansion (user request)
Added 19 entries in five new groups (chemical messages, light and colour, sound and vibration, electric signals, honest signals and trust), each with a line on how the information is encoded, and a table comparing channels by speed, range, strengths and weaknesses. Contested claims, such as trees signalling through fungal networks, are marked as disputed.

## 2026-11-09: Error correction (user request)
Added an Error correction group to Theory with four topics and simulations: detection (parity, Luhn, ISBN-10, CRC-8), Hamming(7,4) with syndromes, Reed-Solomon over GF(256) with Berlekamp-Massey, Chien search and Forney, and convolutional codes with Viterbi decoding compared against Shannon capacity. Tested: Hamming 128 of 128 single errors; Reed-Solomon 200 of 200 with 5 errors in 10 check bytes, with few silent miscorrections beyond that. Linked from the Logic Analyser's CRC checks and Codes in Nature's proofreading entry.
Process lesson: a commit chained after `pytest | tail` went through with a failing test, because the pipe's status is tail's. Commits now check pytest's own exit status.

## 2026-11-09: README (user request)
Wrote README.md (there was none) with 14 screenshots in docs/images, taken from the running app by a scripted headless Chrome: library, Workbench cracking a Vigenere, Enigma, the Le Figaro correspondence, Solutions, the Viterbi simulation, the Signal Workbench (Kinect depth), Logic Analyser (CAN), Sound Lab, File Inspector, Live Devices (simulated GPS only, so no personal device names appear), Recovering Data, the cube and Codes in Nature. Figures quoted come from the database and results files.

## 2026-11-09: Round 31b
The Logic Analyser decodes USB low and full speed from D+ and D-: idle state gives the speed, NRZI and bit stuffing are undone, and every packet's PID complement, CRC5 or CRC16 is checked. Both CRCs match the published catalogue check values. Standard SETUP requests are named on the page. The identification control now covers six protocols: 60 of 60 on the tuning seed and 60 of 60 on a fresh one.

## 2026-11-09: Round 32
Added Line Codes (Tools): Manchester, 4B5B with NRZI, 8b/10b with running disparity and comma alignment, HDMI/DVI TMDS with control-token alignment, and Ethernet frames with CRC-32. All match published reference values. An identifier names the code of a bitstream and decodes it: 48 of 48 on the control and on a fresh seed; with one bit error the code is still named in 37 of 40 streams. VGA and composite timing moved to Round 32b.

## 2026-11-09: Round 32b
Added Video Signals (Tools): sampled VGA in five standard modes (640x480, 720x400, 800x600, 1024x768, 1280x720) and monochrome composite video are rebuilt into pictures from their sync pulses. The control decodes 36 of 36 generated captures with a mean image correlation of 0.945, and none of 10 noise signals. Irregular sync and unlisted timings are refused with the measurements shown.

## 2026-11-09: Problem finder check
Ran `scripts/find_problems.py`. It added no codes (184 tracked before and after; Wikipedia categories returned 21 and 26 entries and AZdecrypt 43 files, all already tracked; the "Unsolved problems in cryptography" category still returns nothing). No duplicates or aliases to remove and no ciphertext added. The database's count of readable attempts rose from 1 to 2 only because the hunter repeated the known 1 July 1896 Le Figaro reading (the IGNOTA ad, already solved in the source database); nothing new.

## 2026-11-09: Round 33
Added Audio Signals (Tools): DTMF touch tones, Morse code and APRS packets (AX.25 over 1200 baud AFSK, CRC-16/X-25 matching its published check value) are identified and decoded from generated examples, uploaded recordings or the microphone. Control: 18 of 18 recordings on two seeds, 0 of 8 noise and tone recordings decoded. APRS decodes 20 of 20 packets at low and moderate noise and 18 of 20 at heavy noise. NEC and RC5 infrared remotes joined the Logic Analyser, whose eight-protocol control is 80 of 80 on both seeds. ADS-B and barcodes moved to Round 33b.

## 2026-11-09: Round 33b
Added Aircraft (ADS-B): Mode S messages are decoded for identity, altitude, position (even and odd CPR pairs) and velocity, matching the published worked examples exactly. A generated sky of aircraft is broadcast as pulse-position signals and decoded back; single-bit CRC repair is used. At low noise every aircraft is decoded completely; noise alone gave no false messages. Added EAN-13 and QR reading: EAN-13 30 of 30 with tilt, blur and noise and no wrong readings, QR 23 of 30; the File Inspector now lists codes found in pictures.

## 2026-11-09: Barcodes & QR page
Added a Barcodes & QR page (Tools), at the user's request: how linear (EAN/UPC, Code 39, Code 128, ITF, Codabar), stacked (PDF417) and matrix codes (QR, Micro QR, Data Matrix, Aztec, MaxiCode) work, with a history from the 1952 Woodland and Silver patent to the 1994 QR code. Tools: make any of 14 symbologies (zxing-cpp 3.1.1; QR drawn with segno 1.6.6) and read it back; read codes from a picture or the camera; a QR's parts coloured (finders, timing, alignment, format and version information, data); EAN-13 check-digit steps; and a damage test where a square blot of noise grows over the code at each error level (largest blot read in at least half of 8 trials: L 2%, M 6%, Q 10%, H 18%; the undamaged control reads). Cross-checks: zxing reads the app's own EAN images and the own reader reads zxing's; OpenCV reads segno and zxing QR codes; blank and noise images give nothing. The File Inspector now also lists Data Matrix, Aztec, PDF417 and linear codes found in pictures. New: `signals/symbology.py`, `web/routes_codes.py`, `barcodes.js`, `barcodes_info.js`, `tests/test_symbology.py` (20 tests).

## 2026-11-09: Round 34
Hunt (5 minutes): no new leads; the 55 needs_review leads are the Le Figaro candidates already checked by eye, waiting only on novelty confirmation. Added hill-climbing for columnar keys of width 8 to 16 (`kernels_t.py`, `mysteries/figaro_wide.py`), in both directions, with a planted-text control (45 of 60 recovered; reliable from 80 letters up to width 10, and to width 14 at 120 letters) and a null that climbs four shuffles of each ad over the same widths. On 34 unsolved ads of 80 letters or more, none passed: the best reading had 23% of its letters in French words against a 65% gate, and the widest width almost always won, as it does on noise. The result is in the Le Figaro case file. Facts and two new avenue ideas (transposition plus substitution; route transpositions) are in the database. Round 35 is next.

## 2026-11-09: Round 35
Hunt (5 minutes): no new leads; the needs_review list is still the 55 checked Le Figaro candidates. Added `mysteries/figaro_layered.py` and a joint key-and-substitution anneal in `kernels_t.py`. Routes (columns, snakes, diagonals, spirals; widths 2 to 20; both directions) followed by a substitution solve: control 30 of 32 planted texts at 80 and 100 letters; 34 ads tested, none passed. Columnar keys of width 4 to 12 annealed together with a substitution: control 22 of 24 at 100 and 150 letters; 20 ads of 100+ letters tested, none passed. The first run's best hits used a route that leaves letters in place; that route is now excluded. Those hits were the B4 ads (abbreviated plain French in the scan, already known as plain) and two existing candidates, KP 6 Nov 1896 and 15 Jul 1896, recovered again by substitution alone. A substitution-invariant pair-count climber failed its control and was removed. New avenue ideas: pool ads by signature; filter abbreviated plain French. Round 36 is next.

## 2026-11-09: Round 36
Hunt (5 minutes): no new leads before this round's own; the needs_review list held the 55 checked Le Figaro candidates. (a) `mysteries/figaro_plainness.py`: share of letters covered by French words and 4+ letter word beginnings. Control: 341 of 344 printed forms of solved ads pass, 0 substituted and 6 shuffled texts (the 99th percentile sets the cut). It flags 363 of 641 unsolved ads as largely plain (48 of 52 B4, all 25 FL); cipher searches now leave them out (34 long ads became 21). (b) Pooling by signature led to the V. T. A. ads of 1877: plain English love letters with some words (some French) enciphered in letters, digits and a cross. 19 scans transcribed by eye (`data/sources/figaro/vta_transcription.json`; 130 of 131 longer words also found in the OCR). `mysteries/figaro_vta.py` votes one homophonic key from 115 context readings and tests it held out: 58% of each ad's enciphered letters decode to dictionary words with a key built from the other ads, against 3% mean and 8% max for shuffled keys (z=54); 438 of 446 hand-read letters predicted; scrambled-cipher control 8%; planted control 96%. The address ad, which gave no readings, decodes to 'mont sainte genev[i]ve'. The third gate fails (58% against a 77% bar), so this is recorded as a candidate key (lead, needs_review), not a solve. Readings checked against the scans by eye; novelty unconfirmed and nothing sent to the database maintainer. Round 37 is next.

## 2026-11-09: Round 37
Hunt (5 minutes): no new leads beyond this session's own; the review list is the 55 Le Figaro candidates plus the V. T. A. key. `mysteries/figaro_vta_gate.py`: under segmented scoring (decoded words may split into dictionary words of 3+ letters; names marked by the plain context, such as the name after 'Mme', are left out) the held-out share is 78.5% against shuffled keys 14% (max 24%), scrambled control 28% and a bar of 77.9% (0.8 of the planted control's 97.4%); all three gates pass narrowly, z=27. This scoring was introduced after the exact scoring failed, so the V. T. A. key stays a readable candidate, not a solution, until the readings are checked independently. Reading each of 14 uncertain glyphs the other way moves the result by at most 0.6 points (all together 78.8%). A search of unsolved ads for plain text with enciphered words found only V. T. A. using letters and digits, plus CH 30 Jul 1884 with one 29-letter block (Workbench: not cracked; lead added). As the user asked, no note was sent to the database maintainer. Round 38 is next.

## 2026-11-09: Round 38
Hunt (5 minutes): no new leads; the review list is unchanged (55 Le Figaro candidates and the V. T. A. key). `mysteries/figaro_vta_blind.py` solves all 198 scored V. T. A. words blind, as one homophonic substitution with the quadgram annealer, never seeing the readings. The best of 7 seeds by score agrees with the context key on 80% of symbol uses and reads, among others, 'long time since I haven't felt your lips on my lips' and 'writing to ... again I wont read it but am dying with jealousy why to him not to me'. Controls: symbols shuffled, 12% agreement and a clearly worse score (-5.23 against -4.76); planted English and French correspondence, 96% of the true key. A blind word-level refinement did not improve agreement and reached 61% word share on shuffled symbols, so it is reported but not used as evidence. Audit (`figaro_vta.unexplained`): 58 of 204 enciphered words are not fully explained; besides names and vocabulary gaps, the misses repeat second values (f as y, 0 as c, n as a, y as o), recorded as the two-letter-symbol idea for Round 39. Still a readable candidate; no note sent, as the user asked.

## 2026-11-09: Round 39
Hunt (5 minutes): no new leads; the review list is unchanged. `mysteries/figaro_vta_pairs.py` tests whether some V. T. A. symbols cover two neighbouring letters, as the misses listed in Round 38 suggested. Second values fitted on the other ads and scored on each held-out ad raise coverage from 78.4% to 84.1%, but random non-neighbour second letters, fitted the same way in 40 draws, reach 84.3% on average (max 86.8%; p=0.59). No evidence for the structure; the key is unchanged and the misses are better read as misprints, abbreviations, names and vocabulary gaps. Next, Round 40 takes the blind pooled method to other writers.

## 2026-11-09: Round 40
Hunt (5 minutes): no new leads; the review list is unchanged. `mysteries/figaro_pooled.py` cuts plain stretches (runs of 6+ letters of French words or word beginnings) from each ad, pools each signature's remaining letters and solves them blind as one substitution (best of 7 seeds by score), with three shuffled copies and a planted control of printed solved ads under a random key. On solved writers, MINA and KP pass while TR and Jean fail because their keys change between ads. On 28 unsolved writers with 150+ cipher letters, only KP passes: its single unsolved ad (6 Nov 1896, already lead 22) now clears all three gates (score -4.32 against -5.40, control 96%, coverage 58% against a bar of 41%). No new writer reads under one simple substitution. Next, Round 41 looks for a key-change rule in TR and Jean.

## 2026-11-09: Round 41
Hunt (5 minutes): no new leads from the hunt. TR turned out to have no unsolved ads and Jean only four short ones, so the round moved to writers whose system the database documents. C. H. (Vigenere CEAD, alphabet without W, documented on 36 solved ads) has five ads listed as undecrypted. Their blocks, transcribed from the scans (`data/sources/figaro/ch_transcription.json`), read under the documented key when it restarts at each block, with at most one skipped key step (`mysteries/figaro_ch.py`). Control: 37 of 37 planted blocks with a dropped letter recovered. Null: the same search on 200 shuffles per block. Three blocks pass all three gates: 31 Mar 1884 '... prie, priez pour moi', 5 Aug 1884 'Je pars', 29 Jun 1886 'Tachez eviter sans refuse[r]' (with 'le huit'); 30 Jul 1884 '... ce que j'ai fait a notre e[n]fant' passes the null but falls just under the word bar (31% against 33%); the 1882 block does not read. Four leads added (needs_review), readings checked against the scans by eye; novelty unconfirmed and nothing sent to the maintainer.

## 2026-11-09: Round 42
Hunt (5 minutes): no new leads from the hunt. `mysteries/figaro_documented.py` parses the database's 60 substitution tables and its 3 Vigenere keys (BCD for 234 and X, CEAD for C. H. and VE, CD for 54) with their users, cuts each unsolved ad of those writers into enciphered blocks, and applies every system with no free parameter. The writer's own system ranks first of 63 in 15 of 126 ads, against 3.4 expected (p=1.9e-6). Nine of the 15 were already candidates (C. H., MH, H, KP, R, COCO). Four are new and were read by eye from the scans (`data/sources/figaro/documented_transcription.json`): GEO 19 Jun 1890 'Il y a un an! Follement je t'attends. Tout a toi'; ZZ 19 Nov 1881 'Ai lettre, merci, mais ecris ... t'adore ... Je baise tes levres, ma cherie'; P 14 Oct 1899 and 930 3 Aug 1888, heavily abbreviated. Only P passes every automatic gate (GEO misses the corrected null threshold narrowly; ZZ and 930 the word bar), so all four are leads to review. Nothing sent.

## 2026-11-10: Round 43
Hunt (5 minutes): no new leads from the hunt. The 18 ads whose own documented system ranked 2nd to 10th were transcribed from the scans before decoding (`data/sources/figaro/rerank_transcription.json`): 7 letter ciphers, 4 abbreviated plain French (missed by the plain filter), 7 using digits. `mysteries/figaro_rerank.py` re-ranks the letter ads and adds a null that takes the best of all 63 systems on each of 300 shuffled copies. Two read: the ad signed 5 of 1 Jul 1882, 'Aime-moi un peu, je t'aime et desire tant te baiser', under table 2217 (listed only for ZZ, whose 1881 ad also reads with it; p=0.003), and J of 16 Oct 1881, 'A toi toujours', under table 2201 (p=0.007). ArH 1884 gives '[p]ouv. aller mercre[di]' but is not significant. Writer VE has no unsolved ads. Two leads added (needs_review); nothing sent.

## 2026-11-10: Round 44
Hunt (5 minutes): no new leads from the hunt. `mysteries/figaro_table_sweep.py` applies all 60 documented tables to 391 unsolved letter ads (plain ads excluded), with each ad's best mean quadgram score compared against 20,000 shuffled copies that also take their best table. 23 ads pass Bonferroni and 34 the false-discovery rate; most were already candidates. Ten new ones were transcribed from the scans (`data/sources/figaro/sweep_transcription.json`) and read by eye, among them 57E 9 Sep 1896 'Imposs. acc. rupture ss. explic.', Fin 28 Oct 1888 'Sera imp. ns voir ap. din., tach. sortir 6 h ...', SZTL 23 Aug 1896 '... indecis sur programme, devoir impose le votre: l'amitie', an unsigned ad of 12 Oct 1881 under the ZZ table 'Soyez bonne, cherie, je [t']aime tant', and an address at St-Valery-en-Caux. The ad signed prof. Valentin, 26 Dec 1878, uses the V. T. A. symbols and reads in English with the 1877 key ('[k]eep in snow, thanks for letter, will write to ...'; 69% words against at most 50% for 2,000 shuffled keys), an independent check of that key. Ten leads added (needs_review); nothing sent.

## 2026-11-10: Problem finder check
Ran `scripts/find_problems.py`. It added no codes: the Wikipedia categories returned 21 and 26 entries, 'Unsolved problems in cryptography' still returns none, and AZdecrypt lists 43 unsolved files, all already tracked (each source was fetched directly to confirm the run had not failed silently). A duplicate check of the whole table found seven empty entries seeded from Wikipedia's List of ciphertexts that are aliases of tracked codes: d-agapeyeff-cipher (of dagapeyeff), tamam-shud-case (tamam-shud), pigeon-nurp-40-tw-194 (pigeon), cicada-3301 (liber-primus), zodiac-killer (the Zodiac codes), ricky-mccormick-s-encrypted-notes (the McCormick pages; the catalog's alias for it lacked the apostrophe and never matched) and james-hampton (w-james-hampton-artist). None held data, facts, leads or avenues; all seven were removed and their names added to the catalog's ALIASES so a re-seed maps them to the tracked codes. Tracked codes: 203 before, 196 after (the rise from 184 since the last check is the Le Figaro ads added in Rounds 36-44, which have no date duplicates). No ciphertext was added.

## 2026-11-10: Round 45
Hunt (5 minutes): no new leads from the hunt. `mysteries/figaro_vta_sweep.py` applies the 1877 V. T. A. key to 464 unsolved ads with letter-digit words in their OCR (200, then 20,000 shuffled keys); none passes Bonferroni, but neither do 11 of the 17 V. T. A. ads that built the key, so OCR loses too much. Transcribed by eye, three ads signed Valentin read with the 1877 key: 26 Dec 1878 'Deep in snow. Thanks for letter, will write to ...', 14 Jan 1879 '[F]ound three tidings[?]. Thanks. Will send letter Wednesday', 10 Oct 1878 partly (p=5e-5, 5e-5 and 2.5e-4 against 20,000 shuffled keys). `mysteries/figaro_families.py` groups transcribed readings by key and date: table 2217 reads five ads from 12 Oct 1881 to 24 Dec 1882 (unsigned, ZZ, 5) as one correspondence, the last 'Triste adieu si froid. T'aime quand meme, te desire follement, te baise partout, ma Berthe cherie'. Widely shared tables (the Caesar shift) are flagged as common and not read as correspondences. Two new leads, two improved; nothing sent.

## 2026-11-10: Round 46
Hunt (5 minutes): no new leads from the hunt. `mysteries/figaro_windows.py` searches each correspondence's dates with its own key only (20,000 shuffles, Bonferroni per window). Table 2217 finds exactly the five known Berthe ads among 69 unsolved ads of June 1881 to June 1883 (the next has p=0.015). The V. T. A. key, on OCR, finds only the Dec 1878 Valentin ad among 62 ads of 1878-79. The letter-digit ads ranked highest last round were read from the scans: two book codes of number pairs (1891 and 1894, 'BLANCHE') and a family of 1882 to 1887 signed 7, 5, H, R, P, M and 2 that shares whole tokens (fr5, t7ct, grp, 26886, 173d); its eight ads are transcribed in `data/sources/figaro/letter_digit_family.json`. A pooled blind homophonic solve beats shuffled symbols (-4.37 against -4.71) but does not read, which points to a codebook. No new readings; facts and two avenue ideas added.

## 2026-11-10: Round 47
Hunt (5 minutes): no new leads from the hunt. Applying the 32 documented digit tables to the Round 46 transcriptions showed that the 1882-87 letter-digit family is the table 2119 correspondence (documented for writer 42; with the earlier inference R=O). `mysteries/figaro_2119.py`: 7 of the 8 transcribed ads pass (table 2119 first of 32, p<=0.0045 against shuffled copies, Bonferroni over 8), and 5 are new members of the correspondence, the earliest 11 Mar 1882 ('to see my dear face again, cannot live more sans toi, ma femme adoree'). An OCR screen of 422 unsolved letter-digit ads under table 2119 alone, with 20,000 shuffles for the top 40, finds 27 at a Bonferroni level, 25 of them without leads; four transcribed and read by eye: J 25 Nov 1883 'So sorry not seen you. Pense toi tout jour, portr. dev. moi ... t'aime tant ma femme', N 8 Jun 1884 'No my dear wife, I don't forget you', 42 6 Dec 1881 '... do every minute ... so much love love you', 8 20 Jan 1887 'Moth. ill ...'. The other 21 are recorded as machine readings, not yet checked. 30 leads added; nothing sent.

## 2026-11-10: Round 48
Hunt (5 minutes): no new leads from the hunt. The 21 table-2119 screen hits left from Round 47 were transcribed from the scans (`data/sources/figaro/letter_digit_family.json`, 25 checked in all) and each reads under table 2119 at p<=5e-4 against 2,000 shuffled copies; all were read by eye, for example 7 20 Feb 1883 'So annoyed now we are going to be spied sharply ... try to know who it is ... tu ne sais pas comme je t'aime', D 5 Jan 1884 'A ta rentree, sache mon amour eternel, ma femme adoree', O 30 Nov 1885 'You fail me so much, I feel how I love you'. Seven symbols missing from the documented table were inferred (P=U, H=W, A=G, O=L, D=K, Q=B, L=A); fitted on the other ads, they raise each held-out ad's word share by 18.5% against 4.1% mean and 12.4% max for 200 random-letter fits (p=0.005). `figaro_2119.py` now builds the timeline: 47 ads from Dec 1881 to Jan 1887 (plus one 1876 outlier from the earlier family). The 21 leads were updated from machine readings to checked readings; nothing sent.

## 2026-11-10: Round 49
Hunt (5 minutes): no new leads from the hunt. In the database's table 2119 the symbol 1 is given as x; in the transcribed ads B reads better in 11 of the 12 where it matters and worse in 1 (sign test p=0.003), turning XACK, XESOIN and POSSIXLE into back, besoin and possible. `figaro_2119.py` now has `full_key()` (documented table, R=O, the seven inferred symbols, 1=B) and `rescreen()`: of 408 further OCR letter-digit ads, 35 pass at a Bonferroni level, 33 without leads. Four were transcribed and read by eye (kept apart from the fitting data): 7 9 Mar 1882 'Yes, always with you, my dear loved wife, miss you so much, my flowers not faded, kissed morning and night'; 42 9 Dec 1882 'Merci madame C. L., votre lettre not long enough. Veux savoir minute ce que fais. Te garde mon coeur tout entier, je t'adore'; I 28 Jan 1886 'Am now close to you ...'; I 25 Jan 1884 '... Love you my wife for ever'. 33 leads added (29 machine readings marked as not yet checked); nothing sent.

