# Code Breaker roadmap: ideas added per round (archive)

Moved from ROADMAP.md on 2026-11-11 to keep it under 500 lines. Each section lists the ideas a round added; pending ones are in ROADMAP.md's upgrade rounds.

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
