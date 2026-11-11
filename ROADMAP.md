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
| 31b | USB low and full speed: NRZI, bit stuffing, PIDs, CRC5 and CRC16 checked against the published catalogue values; added to identification, control now 60 of 60 on six protocols (and a fresh 60 of 60) | completed 2026-11-09 |
| 31c | Codes in Nature: 19 entries in five new groups (chemical, light, sound and vibration, electric, honest signals), each with how the message is encoded, and a channel comparison | completed 2026-11-09 |
| 32 | Line Codes: Manchester, 4B5B with NRZI, 8b/10b, TMDS and Ethernet frames with CRC-32, checked against published reference values; identification 48 of 48 on two seeds | completed 2026-11-09 |
| 32b | Video Signals: VGA (five standard modes) and monochrome composite rebuilt from samples; control 36 of 36, mean match 0.945, 0 of 10 noise signals decoded | completed 2026-11-09 |
| 33 | Audio Signals: DTMF, Morse and APRS (AX.25 over AFSK), control 18 of 18 on two seeds, 0 of 8 noise decoded; NEC and RC5 infrared in the Logic Analyser (80 of 80, eight protocols) | completed 2026-11-09 |
| 33b | Aircraft (ADS-B): published worked examples matched; single-bit repair; every aircraft decoded at low noise, 0 false frames from noise. Barcodes: EAN-13 30 of 30 under damage, QR 23 of 30, no wrong EANs; codes read in the File Inspector | completed 2026-11-09 |
| 33c | Barcodes & QR page (user request): explanations of linear, stacked and matrix codes and their history; 14 symbologies made and read back (zxing-cpp), QR anatomy, EAN check digit; damage test orders levels H > Q > M > L; zxing, OpenCV and the own EAN reader cross-checked | completed 2026-11-09 |
| 34 | Wide columnar keys (width 8 to 16) by hill-climbing, both directions, on 34 Le Figaro ads of 80+ letters. Control 45 of 60 (80 letters: widths 8-10 12 of 12, width 16 1 of 6; 120 letters: width 14 5 of 6). No ad passed: best 23% French-word coverage against a 65% gate | completed 2026-11-09 |
| 35 | Transposition then substitution on the long Le Figaro ads: 8 routes at widths 2-20 (control 30 of 32 at 80-100 letters) and columnar keys of width 4-12 annealed jointly with the substitution (control 22 of 24; width 10 needs about 150 letters). 34 and 20 ads tested, none passed. Known candidates KP 6 Nov 1896 and 15 Jul 1896 recovered again by substitution alone | completed 2026-11-09 |
| 36 | Abbreviated-plain filter (341 of 344 printed solved ads, 0 substituted, 6 of 344 shuffled pass; 363 of 641 unsolved ads flagged plain, now excluded from cipher searches). V. T. A. 1877 pooled: English love letters with enciphered words under one homophonic key; held-out reading 58% dictionary words against 3% (max 8%) for shuffled keys, z=54; scrambled control 8%; planted control 96%. Third gate fails (names, run-together words), so a candidate, not a solve | completed 2026-11-09 |
| 37 | V. T. A. gate: with run-together words split into dictionary words of 3+ letters (nulls and controls scored alike) the held-out share is 78.5% against a bar of 77.9%, shuffled keys 14% (max 24%), scrambled control 28%: three gates pass narrowly, under a scoring chosen after the exact one failed. Flipping all 14 uncertain glyphs: 78.8%. Mixed plain-and-cipher search: only V. T. A. uses letters and digits; CH 30 Jul 1884 has one 29-letter block, not cracked | completed 2026-11-09 |
| 38 | V. T. A. blind solve with no readings: best of 7 quadgram runs (chosen by score) agrees with the context key on 80% of symbol uses; shuffled symbols 12% (score -5.23 vs -4.76); planted correspondence 96%. Blind word-level refinement did not help (78%) and inflates on shuffles (61% word share). Audit: 58 of 204 words not fully explained (names, vocabulary gaps, a recurring second value for f, 0, n, y) | completed 2026-11-09 |
| 39 | V. T. A. two-letter symbols: neighbouring second letters raise held-out coverage from 78.4% to 84.1%, but random non-neighbour letters do as well (84.3% mean, 86.8% max, p=0.59). Not supported; key unchanged | completed 2026-11-09 |
| 40 | Pooled blind substitution by writer, plain stretches cut first. Real control: solved MINA and KP pass, TR and Jean fail (key changes between ads). Unsolved: 1 of 28 writers passes (KP, the existing candidate, now through all three gates against a bar from printed ads) | completed 2026-11-09 |
| 41 | TR has no unsolved ads and Jean only short ones, so the round moved to writers with a documented system and unsolved ads. C. H. (Vigenere CEAD, no W, documented on 36 solved ads): with the key restarting at each block and one slip allowed, control 37 of 37; 3 of 7 blocks pass all three gates (31 Mar 1884 'priez pour moi', 5 Aug 1884 'je pars', 29 Jun 1886 'tachez eviter sans refuse[r]'), 30 Jul 1884 'ce que j'ai fait a notre e[n]fant' passes the null but misses the word bar narrowly; 1882 does not read. Candidates, checked by eye | completed 2026-11-09 |
| 42 | 63 documented systems (60 tables, 3 Vigenere keys) on 126 unsolved ads of their writers, no free parameters: own system ranks first in 15 ads against 3.4 expected (p=1.9e-6). Nine were already candidates; 4 new readings checked by eye (GEO 1890 'Il y a un an! Follement je t'attends. Tout a toi', ZZ 1881, P 1899, 930 1888); 2 do not read | completed 2026-11-09 |
| 43 | 18 ads ranked 2nd-10th, transcribed from scans: 7 letter ciphers, 4 abbreviated plain, 7 with digits. Two letter ads read under tables listed for other writers, best-of-63 null: 5 1 Jul 1882 'Aime-moi un peu, je t'aime et desire tant te baiser' (table 2217, ZZ's; p=0.003), J 16 Oct 1881 'A toi toujours' (2201; p=0.007). VE: all ads solved | completed 2026-11-10 |
| 44 | 60 tables on 391 unsolved letter ads, 20,000 best-of-all shuffles each: 23 pass Bonferroni, 34 the FDR; most already candidates; 9 new readings transcribed and read by eye (e.g. 57E 1896 'Imposs. acc. rupture ss. explic.', Fin 1888, SZTL 1896, unsigned 1881 under the ZZ table) plus the Valentin ad of Dec 1878, which reads in English with the V. T. A. key (p<0.0005) | completed 2026-11-10 |
| 45 | V. T. A. key on 464 letter-digit ads from OCR: none passes Bonferroni (control: only 6 of 17 V. T. A. ads pass from OCR). Transcribed, three Valentin ads (Oct 1878 to Jan 1879) read with the 1877 key ('Deep in snow. Thanks for letter, will write to...'; 'Will send letter Wednesday'). Table 2217 reads five ads of Oct 1881 to Dec 1882 (unsigned, ZZ, 5) as one correspondence to 'ma Berthe cherie' | completed 2026-11-10 |
| 46 | Date windows, one key each: table 2217 finds exactly the five known Berthe ads among 69 (next p=0.015); the V. T. A. key only the Dec 1878 ad among 62 from OCR. Top letter-digit ads are book codes (1891, 1894) and a letter-digit family of 1882-87 across seven signatures; its pooled blind solve beats shuffles but does not read (likely a nomenclator) | completed 2026-11-10 |
| 47 | The letter-digit family is the table 2119 correspondence (writer 42, bilingual): 7 of 8 transcribed ads pass (2119 first of 32 tables, p<=0.0045), 5 new members back to Mar 1882. OCR screen of 422 letter-digit ads under 2119: 27 pass Bonferroni, 25 without leads, 4 checked by eye (J 1883 'So sorry not seen you ... t'aime tant ma femme', N 1884 'No my dear wife, I don't forget you', 42 Dec 1881, 8 1887) | completed 2026-11-10 |
| 48 | All 21 remaining 2119 screen hits transcribed and read by eye (each p<=5e-4). Seven missing symbols inferred (P=U, H=W, A=G, O=L, D=K, Q=B, L=A): held-out gain 18.5% against at most 12.4% for random letters (p=0.005). Timeline of 47 ads, Dec 1881 to Jan 1887 | completed 2026-11-10 |
| 49 | Table 2119: the source table gives x for symbol 1; B reads better in 11 of 12 ads (sign test p=0.003). Rescreen of 408 OCR ads under the full key: 35 pass Bonferroni, 33 without leads; 4 checked by eye (42 9 Dec 1882 'Merci madame C. L., votre lettre not long enough ... je t'adore'; 7 9 Mar 1882 '... my dear loved wife, miss you so much') | completed 2026-11-10 |
| 50 | All 29 Round 49 machine readings transcribed and read by eye (each p<=5e-4). Table 2119 correspondence: 80 ads under 25 signatures, Dec 1881 to Jan 1887; it names madame C. L., Leon, Jul[es?], Heliot, a chalet, a cercle, the Mediterranee, a bal (Feb 1884), the writer's mother, father and a child | completed 2026-11-10 |
| 51 | L. C. 15 (22 ads, 1879-82) and L. R. G. (7 ads, 1879-80) transcribed. Both repeat far more than shuffled copies (36% and 45% of positions in repeated 5-grams, against at most 4% and 7%). LC15 1879-81 is not a simple homophonic substitution (planted control 98%, real text does not read); LC15 1881-82 is not one shared substitution (planted control 100%). LRG looks like a numeric codebook. No readings; book codes need their book | completed 2026-11-10 |
| 52 | L. R. G. reads: a blind homophonic solve (3 of 7 seeds converge) gives digits 1234567890 = TISANEROUL and letters for further common letters; planted control 98%, shuffles at most -4.78 and 15% words against -4.23 and 46%; word bar met narrowly; read by eye ('Tres inquiete, pas recu lettre depuis le huit ... ecris Arcachon'; 'Ma chere, lettre poste restante'). The 1879 numeric ads share no code with LRG; LC15 1881-82 ads are too short alone (controls 22-60%) | completed 2026-11-10 |
| 53 | The L. R. G. method on 14 other letter-digit signatures from OCR: none reads (all under 25% words; planted controls 97-99%). Six beat their shuffles (90, D, B, 7, Jane, E). Under the table 2119 key the pools of 7, D, 42 and E read in part (14-25%) | completed 2026-11-10 |
| 54 | 12 table-2119 residuals (7, D, 42, E) transcribed: all read (p<=5e-4); correspondence now 92 ads, names the wife 'ma douce Tilly'. Jane (Sep 1886) is a numeric homophonic with word breaks: blind solve reads '... ne peut [suffire] a rendre les elans de mon coeur, les baisers, les caresses ...'; control and null pass, word gate missed by 0.2 points. 90 is a dictionary code; B repeats letter-digit words | completed 2026-11-10 |
| 55 | B 1882-1886 (10 ads) read by a blind homophonic solve with word breaks: 4 of 7 seeds converge, score -4.01 against at most -4.71, 58% words against at most 10%, planted 98%: three gates pass ('Ecris vite, ton silence me desole. T'adore'; 'Serai samedi train Vesinet. T'aime follement'). B 1 Apr 1886 is a table 2119 ad. The 90 references need a 700+ page dictionary, not Landais. Jane refinement moved to 56 | completed 2026-11-10 |
| 56 | Word-aware refinement under a matched null (`figaro_wordrefine.py`): Jane 35% -> 56% whole words against at most 35% for shuffled copies through the same pipeline; refined planted control sets the bar at 39%, Jane reaches 41%: all three gates pass. B 41% -> 70% against at most 9% | completed 2026-11-10 |
| 57 | 13 further word-break series from OCR through blind solve plus matched refinement: none reads (coverage at most 21% against bars of 47-52%); 7 beat the matched null (17, 38, 42, PAUL, E, T, 13), structure only. Short-word series inflate even when shuffled (up to 74% refined words) | completed 2026-11-10 |
| 58 | Of the series that beat the matched null: 17 (1878) is a book code with page.word ranges; 38 (1881) a numbered codebook (~37,000 entries); PAUL and E are table 2119 ads hidden by OCR: 11 of 12 read at p<=5e-4 ('Our little girl ... how I love you'; 'Moth. says comes mardi ... must be back before end year'). Correspondence: 104 ads | completed 2026-11-10 |
| 59 | 19 T and 42 ads transcribed: all table 2119; 16 pass at p<=5e-4, 3 in part ('Back Friday ... love you all my heart, my wife'; 'Necess. know what he is about before he goes, to avoid be caught'). Key history: Dec 1881-Feb 1882 use 9 and i (as documented) where later ads use r and p (as inferred). Correspondence: 123 ads | completed 2026-11-10 |
| 60 | 38 codebook: elided numbers fall in vowel/h stretches of an alphabetical list 2 of 4 times (chance 27%, p=0.30), no support for alphabetical order. V 1896 jargon: 73% of 73 recurring code words fit stem + consonant + vowel (lar-, dri-, fra-, mi- with up to 12 variants) against at most 11% shuffled: a two-part nomenclator (descriptive; pattern chosen after inspection) | completed 2026-11-10 |
| 61 | V 1896, hypotheses fixed in advance: no stem's variants track publication weekday or day of month (best p=0.017 and 0.021 against a Bonferroni bar of 0.0036); time words almost never beside code words. Not a date code in this form | completed 2026-11-10 |
| 62 | Review queue triaged (`triage.py`, `docs/review_queue.md`): 191 leads; A 4 (V. T. A., L. R. G., Jane, B), B 122 (102 table 2119), C 54, D 11; one stale 2119 lead updated | completed 2026-11-10 |
| 63 | Non-Figaro codes with word breaks (1916 train station cryptogram, Ricky McCormick pages 1-2, Paul Rubin) through an English word-break pipeline with matched controls: none reads (planted controls 94-100%). The 1916 text, 17 enciphered words, is too short; McCormick and Rubin are not simple substitutions of English words | completed 2026-11-10 |
| 64 | Ricky McCormick, four letter-frequency models fixed in advance (plain, vowel-dropped, word initials, any simple substitution of English): all rejected (p<=0.001). Vowels 25% of letters, almost all E; 38% of groups end in -SE against 1% of English words (descriptive): SE looks like an added marker | completed 2026-11-10 |
| 65 | McCormick with -SE/-BE stripped: all four models still rejected (simple substitution closest, p=0.0045 against 0.0125); stems solved blind with word breaks do not beat shuffles or read (planted control 100%). Not a substitution of English | completed 2026-11-10 |
| 66 | Table 2402 family: 10 letter-digit ads of 1879-1889 (47, 74, '2 Fev.'), transcribed; all 10 read at p<=5e-4 with 2402 first of 32 tables; no symbols missing. Six dotted number lists once grouped with them are another system. Review tier: 2402 leads C -> B | completed 2026-11-10 |
| 67 | Dotted number lists against 63 fixed numeric systems (11 documented tables, shifted and reversed alphabets) with a best-of-all null: OPQ 1877 reads under documented table 2308 ('Demain jeudi Miromesnil, deux heures et demi', p=0.0015); LINETTE fragments under 2307 not significant; two lists use numbers above 26; one too short | completed 2026-11-10 |
| 68 | Triage rule refined (gate results from the whole history; weaknesses only from the latest round): A 6, B 132, C 42, D 11; duplicates none (310 codes). Next family chosen: tier-C documented-table ads (writer 25 of 1894 and 11 others) | completed 2026-11-10 |
| 69 | Ten tier-C ads under documented systems transcribed and retested with matched nulls: 9 of 10 pass (25 of 1894 under Vigenere CD; 'Jeannette' 1881 reversed under 2210; 5 of 1875 and two CHERY under numeric tables; LILI and Po under digit tables); OPQ Oct 1877 (mostly plain) does not. Four Caesar leads updated from the Round 44 sweep. Triage: A 6, B 145, C 29, D 11 | completed 2026-11-10 |
| 70 | Tier-C table 2119 ads: the twelve early leads (Dec 1883 to May 1886, read from OCR in Round 26) transcribed from the scans; all 12 read under the full key at p<=5e-4 against 2,000 shuffles (Bonferroni over 12), e.g. 30 Dec 1883 'mari pas content mais suis premier te souhaiter jour [de l']an'. Two older results recorded on their leads (72, 177). Four short ads stay in C (failed earlier tests). Triage: A 6, B 159, C 15, D 11; table 2119 B 116, C 4 | completed 2026-11-10 |
| 71 | Remaining tier-C families retested from the scans with matched nulls (`figaro_tierc2.py`, Bonferroni over 17): Berthe 3 of 3 under table 2217 (1 Jul 1882 newly transcribed); C. H. 3 of 3 (whole ad, 1,000 shuffles); the four abbreviated 2119 ads 4 of 4 with a pre-registered prefix statistic (control 12/12; other tables far lower). New: all six V. E. 3 ads (1889-92) read under the C. H. key CEAD with the key running on (pooled p=1e-3; 4 of 6 pass alone): 'Serai [le] 8, 14, 22, pas [le] 15', 'Lundi, pas avant 6 1/2'. AIM and OPQ stay in C. Triage: A 6, B 173, C 5, D 11 | completed 2026-11-10 |
| 72 | Documented Vigenere keys screened (`figaro_cead_screen.py`): CEAD on the 284 unsolved ads of 1885-95 (running or restarting key, phases 0-3, shuffled-copy null, Bonferroni over 284; planted control with 5% OCR noise 19 of 20): only the known C. H. and V. E. 3 ads pass. BCD, CEAD and CD on all 643 unsolved ads (Bonferroni over 1,929): only their documented writers pass (25 of 1894 under CD; C. H., V. E. 3 under CEAD). Negative: no new user of these keys | completed 2026-11-10 |
| 73 | Families solved blind, no key given (`figaro_blind_family.py`, the Round 56 pipeline): table 2402 (10 ads) and Berthe 2217 (5 ads) pass all three gates, blind keys matching the documented tables on 99.6% and 98.1% of occurrences, so 15 leads move to tier A. Table 2119 (121 ads): blind key matches 97.7%, beats shuffles 0.44 against 0.13, control 100%, but coverage 0.32 is under the word bar 0.54 (abbreviated, partly English), so it stays in B. Duplicate entry in figaro_families removed (Round 71's test change reverted to 5). Triage: A 21, B 157, C 5, D 11 | completed 2026-11-10 |
| 74 | Style-matched word gate for the 2119 family, committed before running (78fcb10, `figaro_style_gate.py`): planted control with the family's English runs and abbreviation rate gives a bar of 0.371 (was 0.54); the family's coverage 0.324 still misses it, so 2119 stays in tier B. Control milder than the family (stricter bar); not tuned after the run | completed 2026-11-10 |
| 75 | Scripts & Glyphs page (`codebreaker/writing/`, Tools menu): sign-by-sign reading of 9 deciphered scripts from recorded sources (Wikipedia tables in data/sources/scripts with sources.json, and Unicode 15 names): Egyptian 1,072 signs (26 uniliteral, 151 biliteral, 75 triliteral from the tables; the rest named as logograms or determinatives with Gardiner numbers), Linear B, runes (Elder Futhark table), Ogham, Phoenician, Gothic, Ugaritic, Old Persian, cuneiform sign names; Gardiner numbers accepted as input; palette with search; names spelled in one-sound signs (labelled a modern convention); plain letters handed to the Workbench. Coptic left out (its table needs its own parser); Runic and Ogham fonts are not installed (the browser falls back to Apple Symbols) | completed 2026-11-10 |
| 76 | Script ciphers (`ciphers/scripts.py`, Library family 'Scripts'): Runic (Elder Futhark), Ogham and Hieroglyph-alphabet encodings from the Round 75 sign tables, and a keyed Rune substitution with a relabel-and-anneal attack (demo 100%). Crack: a new keyless layer transliterates known-script text when its signs map one-to-one onto letters, otherwise relabels up to 26 kinds of unfamiliar symbol as letters; runic text decodes at once, a rune substitution is solved through the relabelled layer. The classifier excludes the Scripts family (its class list comes from the registry and the trained model has fixed outputs; script text goes through the script layer instead). Limitation: hieroglyph-alphabet text merges E/I and O/U/W, so the crack shows the transliteration but finds no reading ('partial'); merged-letter recovery filed as an avenue. Pigpen deferred: its key layout exists only as an image in the recorded source | completed 2026-11-10 |
| 77 | Glosses, not translations: word lists for Egyptian, Linear B and Old Norse, every output labelled a gloss; worked examples from recorded sources (e.g. the Rosetta Stone cartouches) | pending |
| 77b | Historical ciphers in other scripts: Library ciphers 'Twig runes' (Younger Futhark group and position as branches) and 'Futhark shift' (Rök stone), Ogham scales if a recorded source gives them; History entries (enigmatic hieroglyphs, Esna ram and crocodile hymns, Mesopotamian glaze tablet, Rök, Maeshowe, Auraicept ogham, Wujing Zongyao codebook) each checked against a saved Wikipedia page; a Scripts-page walkthrough of one-sign-many-values writing | pending |
| 78 | Glyph scanner: find signs in a photo or drawing (OpenCV contours, as in sudoku_vision), identify each against templates rendered from the installed Noto fonts (Egyptian 1,072, Linear B 211, cuneiform 922 signs) with a small GPU classifier trained on augmented renderings; output ranked top-5 candidates for the user to confirm, never a single silent answer. Controls: held-out augmented renderings, distorted and hand-drawn-style test sets; accuracy by script reported | pending |
| 79 | Pictogram identification: which script a set of signs belongs to (script classifier over all font-rendered scripts), a drawing pad for typing a sign by sketch, and the scanner's output fed into the Scripts page and the crack. Real photographs need a recorded labelled dataset (e.g. published hieroglyph image sets): ask the user before downloading | pending |
| 80 | Undeciphered scripts: Linear A read with Linear B sound values against shuffled-text and other-value controls, in the Lost-Script Lab; never claimed as a decipherment | pending |
| 81 | Music ciphers: Library ciphers for the French and German note-letter methods (encrypt to notes, decrypt, frequency attack), the BACH, DSCH and ABEGG signatures shown as notes, rendering on a stave and playback; history entries (Bach, Shostakovich, Schumann, Elgar's hidden theme) checked against saved sources; backmasking as a lesson in pareidolia with a shuffled-audio control | pending |
| 82 | Spectrogram steganography in the Sound Lab: hide a picture in sound and reveal it in the spectrogram; detection of images in spectrograms against noise controls | pending |
| 83 | Acrostic and null-cipher finder: first letters of lines, words, sentences or chapters (and every n-th letter), scored against shuffled-text controls with a Bonferroni bar; worked examples from recorded sources (Hypnerotomachia Poliphili); the 1944 D-Day crossword codewords as a lesson in coincidence, with a base-rate estimate | pending |
| 84 | First Contact lab: (a) 'Is it language?' Zipf slope, entropy at increasing orders, compressibility and repeated-motif structure for any symbol stream, against human languages, birdsong, DNA, random and shuffled controls; (b) an Arecibo-style decoder finding a picture's dimensions from a bit stream (prime factor layouts), with the 1974 message from a recorded source; (c) a message-design puzzle: build a message a stranger could decode, then let the decoder try it; notes on grounding meaning (playbacks, bilinguals, monolingual demonstration, embedding alignment as in Project CETI) | pending |

## Lessons learned
- An exotic alphabet is only relabelling: relabelling unknown symbols as letters lets every substitution attack run, but a lossy script spelling (merged letters) defeats language tests and needs its own word-level recovery (Round 76).
- Scripts that start worker processes must run from a file with a main guard on macOS; a heredoc script breaks the process pool.
- Sign values are data like ciphertexts: take them from a recorded table and test them, and refuse a value the tables cannot give (the Ptolemy cartouche's MdC mnemonics) rather than filling it from memory (Round 75).
- Pre-registering by commit works and costs one test run: the Round 74 gate was in git before its result existed, so the negative stands without argument.
- Do not run the test suite while the hunt runs: the Workbench crack test has a 45-second budget and failed once under load (passed 3 of 3 alone).
- A blind solve that recovers a documented key is the strongest check on a key-based reading: three families' blind keys matched their tables on 97.7-99.6% of occurrences (Round 73).
- When a test count changes after adding data, look for duplicates before updating the test: Round 71 raised a family test to 6 when one ad had been counted twice (Round 73).
- Size the null from the bar, not from habit: the first all-keys screen (bar 2.6e-5) used 20,000 shuffles, floor 5e-5, and could pass nothing; stage 2 now takes max(20,000, 2/bar) (Round 72, the same trap as Round 71).
- Check that a null can reach the bar: 200 shuffles give p >= 1/201, above a Bonferroni bar of 0.0045, so the first C. H. run could not pass whatever the ad said (Round 71).
- A documented key can travel between writers: V. E. 3 used the C. H. Vigenere key but let it run across words; test documented keys on other signatures, with and without restarts.
- Leads read from OCR keep a low tier until they are transcribed: Round 70's twelve early 2119 ads all passed once read from the scans, so a weak tier often measured the OCR, not the cipher.
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
- Process: never gate a commit on `pytest ... | tail`; the pipeline returns tail's status. Run pytest, keep its exit code, then commit.

## Added 2026-11-09: Round 31b
- Check a CRC implementation against published catalogue values (CRC-5/USB 0x19, CRC-16/USB 0xB4C8), not only against your own encoder: a matching pair of bugs would otherwise pass.
- Adding a protocol to identification can steal results from the others, so the whole control is rerun, on both seeds, after each addition.

## Added 2026-11-09: Round 32
- Reference values anchor each code: 8b/10b K28.5 0011111010, D21.5 1010101010 and D0.0 1001110100; TMDS control token 1101010100; CRC-32 0xCBF43926.
- These codes detect errors but do not correct them. With one flipped bit the code was still named in 37 of 40 streams, but exact messages are lost. A message-level control needs a correcting layer on top.
- A tidy-up broke the Ethernet check (alignment started two bytes before the delimiter while the parser looked for three); the control caught it at once, which is the point of rerunning it after every change.

## Added 2026-11-09: Round 32b
- The first video decoder "succeeded" on random noise (with confidence 0.0) and forced an unlisted mode onto the nearest standard. Success now needs regular line syncs and a mode that fits; otherwise the page reports the measurements and the closest mode.
- Ideas: decode NTSC and PAL colour from the subcarrier; take real captures from an oscilloscope CSV; time-domain reflectometry.

## Added 2026-11-09: Round 33
- A bit clock that resets on every tone change loses whole bits to noise near the decision boundary. Smoothing plus a half-way nudge from changes since the last sample fixed it; a nudge window centred on the sample point instead pulled the clock onto the next boundary and broke every packet.
- A "is there a signal" check must take the noise floor low in the distribution: a busy Morse message is tone most of the time, so the 20th percentile is already signal.
- Misses that decode nothing are acceptable failures; the CRC turned every damaged APRS frame into a refusal rather than a wrong message.

## Added 2026-11-09: Round 33b
- Published worked examples pin the decoder (KLM1023; 52.2572 N, 3.91937 E at 38,000 ft; 159.2 kt, 182.88 degrees, -832 ft/min); my own encoder was wrong (a missing 3-bit field) and only the round trip showed it.
- In EAN-13 the right-hand patterns are the left-hand ones inverted, so they share bar widths: one lookup table silently swallowed half the code. Side decides the table.
- OpenCV 5's barcode detector missed even clean EAN-13 images here, so a scanline reader written from the specification replaced it.

## Added 2026-11-09: Barcodes & QR page
- segno raises the error level by default when it fits in the same version (`boost_error`), so an "M" code can really be "Q". Pass `boost_error=False` whenever the level is the thing being measured.
- Scattered single-module noise defeats a QR code at about 1 to 3 per cent even at level H, because each speck spoils a different codeword and some hit the finders or format bits. A contiguous blot is the case error correction is designed for: L survived a 2 per cent blot, M 6, Q 10, H 18 (median of 8 placements).
- zxing-cpp reports UPC-A as EAN-13 with a leading zero and UPC-E in its expanded form; tests should compare digits, not formats.

## Added 2026-11-09: Round 34
- coverage() counts upper-case text only; a lower-case reading scores 0 and silently disabled the word gate on the first run. A test now pins it.
- In the reverse direction (columns written, rows read), the best key often gives the right text rotated or in reordered blocks. Score a control by shared 6-letter runs, not by position.
- Below about 80 letters, wide keys overfit: the wrong key scores above the true one. When every width is allowed, the widest wins on noise, so the null must be climbed over the same widths.
- New ideas: transposition followed by substitution; route transpositions at wide widths.

## Added 2026-11-09: Round 35
- Counting repeated letter pairs (which substitution leaves alone) does not find a columnar key at 100-250 letters: wrong keys score above the true one. Annealing the key and the substitution together does, from about 100 letters at width 8.
- Some routes are the identity on some widths (diagonals of a 2-wide grid). Every generated order is now checked against the identity, or a substitution-only solve is reported as a transposition.
- Abbreviated plain French (the B4 ads: pens, souf, bonh) has word coverage near 0.3 and slips past a plain-text filter set at 0.35. A high score is not a find until the raw text has been looked at.
- Re-finding known candidates from a different pipeline is a cheap end-to-end check.

## Added 2026-11-09: Round 36
- Some unsolved ads are not ciphers in the expected language: the V. T. A. ads are English with a few enciphered words, and searches that treated them as French ciphers could never work. Look at the scan before choosing a model.
- The printed form of a solved ad (the published reading minus bracketed expansions) is a free positive control for "abbreviated plain text".
- Shuffled French keeps letter frequencies, so a plain-text measure must beat shuffles, not only substitutions: 3-letter word beginnings let 78% of shuffles pass; whole words of 3+ and beginnings of 4+ letters let 2% pass.
- For a key read from context, the fair test is held out: build it without the ad being read. A scrambled-cipher control shows that attaching readings to strings does not produce the result by itself.
- In this typeface 1/l and o/0 differ by a few pixels; a "7" was a question mark. Record such readings as ambiguous.

## Added 2026-11-09: Round 37
- A scoring rule changed after a gate fails must be applied identically to every null and control, and the result reported with its margin and its history; here it passes by 0.6 points.
- Segmenting decoded words also raises the nulls (shuffled keys 3% to 14%, scrambled control 8% to 28%), which is why short words (1-2 letters) are not allowed in a split.
- The vocabulary must use the writer's alphabet: with v written as u, 'love' is only found as 'loue'.
- Uncertain glyphs matter less than feared: with one key across 18 ads, any single glyph moves the result by under one point.

## Added 2026-11-09: Round 38
- A blind solve is the cleanest independent check of readings made by eye: the solver never sees them, and agreement with them is measured afterwards.
- Choose the run by its own score, fixed in advance; across seeds the agreement ranged from 0% to 85%.
- Optimising a key for dictionary-word share inflates on shuffled symbols (61%), so word share is a check on a key found otherwise, never an objective by itself.
- An audit of what the key does not explain points to structure: the misses repeat the same second values.

## Added 2026-11-09: Round 39
- Any extra freedom raises coverage; the question is always whether the specific structure beats the same freedom placed at random. Here it did not.
- A greedy fit with a small minimum gain gave almost every symbol a second value, for neighbours and random letters alike: the threshold matters less than the control.

## Added 2026-11-09: Round 40
- A real-data positive control (solved writers through the same pipeline) shows where a method cannot work: TR and Jean change keys between ads, so pooling them fails even though each ad is easy.
- The coverage bar should come from text like the target: printed Le Figaro ads are abbreviated, so a planted control built from them sets a lower, fairer bar (about 45-55%) than full French prose.
- Cutting plain stretches before solving matters: many 'cipher' ads open or close in plain French.

## Added 2026-11-09: Round 41
- Read the source's notes before searching: the C. H. key was documented all along, and the ads stayed unread because the key restarts at each enciphered block and one letter was dropped in printing.
- A documented key is not fitted, so the only freedom is the phase and the slip; the null must search exactly that freedom on shuffled copies.
- The place of a dropped letter is uncertain by a position or two; judge recovery by letters right, not by the slip's position.

## Added 2026-11-09: Round 42
- Ranking a writer's documented system against every other documented system is a control that needs no simulation: by chance it ranks first 1 time in 63.
- Give every system the same freedom in that ranking; a Vigenere search with slips would otherwise beat fixed tables on noise.
- Readings found by an independent test often coincide with earlier candidates; that coincidence is itself evidence the earlier ones were right.

## Added 2026-11-10: Round 43
- A writer's listed table is not always the one used: 5 used ZZ's table, J a common one. When the search widens to all systems, the null must widen too (best of all systems on each shuffle).
- Transcribing before decoding keeps the eye honest; four of the 18 'cipher' ads were plain abbreviated French and seven used digits.

## Added 2026-11-10: Round 44
- A fast statistic (quadgram score, numba) makes a fair multiple-testing bar affordable: 20,000 best-of-all-tables shuffles per ad for 391 ads in under a minute.
- A key checked on material it was not built from is the strongest evidence: the 1877 V. T. A. key reads an 1878 ad by 'prof. Valentin'.
- Simple systems (Caesar shift, table 1001) still read many ads listed as undecrypted once plain stretches are cut and the scan is transcribed.

## Added 2026-11-10: Round 45
- Measure a screen's power on known material before trusting its silence: from OCR, the V. T. A. key recovers only 6 of its own 17 ads, so 'no new hits' from OCR says little.
- In these ads the large initial letter is often the first cipher letter ('P87y' = deep).
- One signature can hide several writers (5 covers numbers in 1875, table 2217 in 1882, letter-digit codes in 1883 and 1887), and one writer can use several signatures (ZZ, 5 and none for the Berthe letters).

## Added 2026-11-10: Round 46
- Searching a date window with one key is cheap and decisive: it confirmed the five Berthe ads and showed there is no sixth among 69 neighbours.
- A pooled blind solve that beats shuffles but reads as French-looking nonsense indicates repeated whole tokens, not a letter cipher; switch to codebook methods.

## Added 2026-11-10: Round 47
- Try the documented tables on a transcription before inventing a model: the 'codebook' was a documented table whose cells hold syllables and words.
- A blind letter-substitution solve that beats shuffles but does not read can mean the key maps symbols to multi-letter units.
- Once a key is known, a screen of OCR under that one key is powerful even where OCR is poor: 27 ads pass a Bonferroni bar over 422.

## Added 2026-11-10: Round 48
- Missing symbols in a documented key can be inferred fairly with the same held-out design as before: fit on the other ads, measure on the held-out one, and compare with the same fit restricted to random letters.
- Systematic oddities in the readings (X for B) point to errors in the parsed key, not in the ads.

## Added 2026-11-10: Round 49
- For a single-symbol correction, a per-ad sign test (does the alternative read better or worse in each ad?) is sharper than a random-letter control, which includes the right letter by chance about one time in nine.
- Keep spot-check transcriptions out of the data used to fit a key, so later fits stay honest.

## Added 2026-11-10: Round 50
- Screening under a key that has been corrected and completed keeps paying: the 2119 correspondence grew from 17 to 80 ads in four rounds.
- Keep mentions (names, places, events) as a by-product of reading; they are the way to date and identify a correspondence later, and they need no new statistics.

## Added 2026-11-10: Round 51
- A planted control of the same size is what turns 'it did not read' into a finding: the solver recovers 98-100% of planted texts of these sizes, so these series are not simple substitutions.
- Heavy repetition of long groups (a third or more of all positions) is the signature of a codebook or fixed formulas, not of a letter cipher.

## Added 2026-11-10: Round 52
- A series that looks like a codebook can still be a substitution: heavy repetition came from repeated words ('ecris Arcachon'). Test the simple model with a planted control before assuming the complex one.
- Seed agreement is a cheap extra check: three of seven blind runs reaching the same key is strong evidence the optimum is real.

## Added 2026-11-10: Round 69
- Results recorded in one round's output can fail to reach older leads: four Caesar-shift ads had passed the Round 44 sweep but their leads still showed the earlier weak note.

## Added 2026-11-10: Round 68
- Free-text evidence accumulates: classify by the whole history for what was shown, and by the latest statement for what was later found wrong, or old notes will hold strong results down (and new detail will hide old passes).

## Added 2026-11-10: Round 67
- A reading found earlier by inferring blank table cells was found again with no inference under another writer's documented table; independent routes to the same text are good evidence.

## Added 2026-11-10: Round 66
- A 'family' built from OCR can mix systems: six of the sixteen 2402 ads were dotted number lists. Look at the scans before testing the family as one.

## Added 2026-11-10: Round 65
- Removing an apparent marker brought the letters closer to English but not to readable English: a model can move toward a fit without fitting.

## Added 2026-11-10: Round 64
- Frequency models with a sampling null reject cleanly even on short texts (746 letters): all four plausible English models fail, which narrows the field without any decryption.

## Added 2026-11-10: Round 63
- The Le Figaro methods transfer, but the material decides: few non-Figaro unsolved texts keep word breaks, and those that do are too short or not substitutions.

## Added 2026-11-10: Round 62
- Evidence written in free text drifts: one lead kept an out-of-date note after its ad had been tested. A triage pass that checks consistency catches this.

## Added 2026-11-10: Round 61
- Fixing the hypotheses before looking turned two tempting p-values (0.017, 0.021) into the non-results they are under the correction.

## Added 2026-11-10: Round 60
- A pattern found by looking is a description, not a test; it earns a test only when a prediction is fixed before the data that checks it.
- Elision gives a free check on codebook order (after j' the word starts with a vowel or h), but needs more cases than four.

## Added 2026-11-10: Round 59
- A documented key can describe only the start of a correspondence: the database's table 2119 matches the 1881-82 ads, and the writer later changed two symbols. Inferred values that disagree with a documented table may be later usage, not errors.

## Added 2026-11-10: Round 58
- Looking at the scans before modelling saves rounds: two of the 'structure' series were not substitutions at all (a book code and a numbered codebook), and two were the known 2119 system under poor OCR.

## Added 2026-11-10: Round 57
- Word-level scores are easy to inflate on short words: shuffled short-word series reached 74% refined words. Only the matched null and a coverage bar from a refined planted control keep the test honest.

## Added 2026-11-10: Round 56
- A refinement is fair only if every comparison goes through it: shuffled copies and the planted control were refined the same way, and the bar was set from the refined planted text.
- Word-level scoring can trade one real word for another ('de' to 'se'); read the result, do not just count it.

## Added 2026-11-10: Round 55
- Printed word breaks plus repeated words make short homophonic series solvable: ten ads of 372 symbols passed all three gates.
- The shape of reference numbers can rule a codebook out before any lookup: entries 1-42 and pages up to 701 exclude a 605-page dictionary.

## Added 2026-11-10: Round 54
- Pooling OCR digits into one string destroys number boundaries: the Jane ads, numbers 1-74 with printed word breaks, only read once each number was a symbol.
- Ranking unassigned ads under a known key and transcribing the top ones keeps finding members: 12 of 12 read.

## Added 2026-11-10: Round 53
- A screen on OCR is only as good as the OCR: the same method that read L. R. G. from transcriptions reads nothing here, and planted controls cannot model OCR loss.
- Decoding failed pools with keys already known is cheap and points to hidden members of known families.

