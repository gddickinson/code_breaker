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
