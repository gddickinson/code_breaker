"""Turns saved mystery results into the sections shown in the Mystery Lab."""


def _t(cols, rows):
    return {"cols": cols, "rows": rows}


def beale_sections(r):
    an1, an3, ctl = r["anomaly_b1"], r["anomaly_b3"], r["anomaly_b2_control"]
    out = [{"heading": "Control: Beale 2 opens", "paragraphs": ["Numbering the Declaration's words and taking first letters reproduces the published solution. This confirms both the transcription and our decoder. Small errors remain because Beale's word count differed slightly from the modern text."],
            "mono": [{"label": "Beale 2 decoded by our tools", "text": r["b2_decoded"]}]},
           {"heading": "The ciphers at a glance", "table": _t(["Cipher", "Numbers", "Distinct", "Largest", "Mean", "At most 100"], [[k, v["count"], v["distinct"], v["max"], v["mean"], v["share_at_most_100"]] for k, v in r["stats"].items()])},
           {"heading": "The alphabetical anomaly", "paragraphs": ["Applying the Declaration to Beale 1 gives gibberish, except for a famous stretch of letters in almost perfect alphabetical order, first reported by Jim Gillogly in 1980. We tested how long a non-decreasing run appears when the same numbers are put in random order.",
                                                                 "A long improbable run suggests that the numbers were made with reference to this document, possibly by someone working down its text. It does not read as a message, and it is often cited as evidence of a hoax. An empirical p of 0.0005 means none of the 2,000 shuffles matched it."],
            "table": _t(["Cipher", "Longest run", "Letters", "Shuffled mean", "Shuffled max", "Empirical p"], [[n, a["longest_run"], a["text"], a["null_mean"], a["null_max"], a["p_empirical"]] for n, a in (("B1", an1), ("B3", an3), ("B2 (control)", ctl))])}]
    rows = [[n, s["key_text"], s["offsets_tested"], s["best_score"], s["null_mean"], s["z"]] for n in ("B1", "B3") for s in r["hypotheses"][n]["key_scan"]]
    ctl_row = r["key_scan_control_b2"][0]
    out.append({"heading": "Attempt: candidate key texts", "paragraphs": ["We slid each period text under the numbers at every starting word, including the Bible, Shakespeare, the Federalist Papers and the Constitution. Each result is compared with the best score from shuffled numbers.", f"Control: Beale 2 against the Declaration reaches z = {ctl_row['z']}, so a correct key would stand out. Offsets tested are limited by the size of each text."],
                "table": _t(["Cipher", "Key text", "Offsets", "Best score", "Shuffled mean", "z"], rows)})
    for n in ("B1", "B3"):
        h = r["hypotheses"][n]["homophonic"]
        out.append({"heading": f"Attempt: {n} as a homophonic cipher", "verdict": h["verdict"], "paragraphs": [f"Control accuracy on known English with the same length and symbol count: {h['positive_control']['accuracies']}. Real score {h['null_test']['score']}, scrambled mean {h['null_test']['null_mean']}."],
                    "mono": [{"label": "Best machine reading (expected to be meaningless)", "text": h["null_test"]["plaintext"]}]})
    return out


def dagapeyeff_sections(r):
    s = r["stats"]
    top = r["hypotheses"][:10]
    return [{"heading": "Structure", "paragraphs": [f"Read as pairs from the first digit, the first members come from {s['first_digit_set_frame0']} and the second members from {s['second_digit_set_frame0']}. That split is a strong sign of a grid cipher such as Polybius. The single 0 comes from the group 63630, and it may be an error in the original.",
                                                    f"Pair index of coincidence is {s['pair_ic_frame0']} in this alignment, close to natural language (0.066), and only {s['pairs_frame0_distinct']} distinct pairs appear. We removed the final three 0s as padding."],
             "table": _t(["Digits", "Distinct pairs", "Pair IC", "Pair IC, shifted by one"], [[s["digits"], s["pairs_frame0_distinct"], s["pair_ic_frame0"], s["pair_ic_frame1"]]])},
            {"heading": "Attempt", "verdict": r["verdict"], "paragraphs": [f"We tested {r['tests']} combinations of language and regular null-pattern, as d'Agapeyeff's book discusses nulls. The solver recovered {r['positive_control']['mean']:.0%} of known English enciphered the same way, so a plain English Polybius of this size would have been read. It wasn't.", "What this excludes is narrow: a single-square substitution with these regular null patterns, in these six languages. Transposition before substitution, irregular nulls or a mistake by the author remain open."],
             "table": _t(["Pattern", "Language", "z", "Score", "Scrambled mean", "p"], [[h["pattern"], h["language"], h["z"], h["score"], h["null_mean"], h["p"]] for h in top])},
            {"mono": [{"label": f"Best machine reading ({top[0]['pattern']}, {top[0]['language']}): not a solution", "text": top[0]["plaintext"]}]}]


def tamam_sections(r):
    c, m = r["calibration"], r["rubaiyat"]
    return [{"heading": "The text", "mono": [{"label": "As written (line 2 is crossed out in the original)", "text": "\n".join(r["lines"])}], "paragraphs": [f"The analysis uses the {r['length']} uncrossed letters. The first letter could be W or M."]},
            {"heading": "Finding: it looks like English initials", "paragraphs": [f"Compared with running text, the letters fit English word-initial statistics better by {c['observed_gap']} log-likelihood units. Simulated initials give {c['gap_mean_if_initials']} ± {c['gap_sd_if_initials']} and running English text gives {c['gap_mean_if_running_text']} ± {c['gap_sd_if_running_text']}. Of simulated running-text samples, {c['fraction_running_text_at_least_observed']:.2%} reached the observed gap.", "This independently supports the University of Adelaide projects. English is also the best of six languages. If the code is initials, no algorithm can recover the words without more information, as the mapping from initials to sentences is massively ambiguous."],
             "table": _t(["Language", "Fit as initials", "Fit as running text", "Initials minus running"], [[d["language"], d["initial_letter_loglik"], d["running_text_loglik"], d["initial_minus_running"]] for d in r["distribution"]])},
            {"heading": "A curious lead in the Rubaiyat", "paragraphs": [f"Searching the whole book for runs of word initials, the longest match is {m['length']} letters: {m['letters']}, from the line {m['line'] if 'line' in m else 'ITTMTSAMSTGAB'}. In the book those words are \"{m['book_words']}\", within: \"{m['context']}\".",
                                                                         f"A match this long occurred in {m['english_at_least']:.2%} of trials using blocks of real English initials, and in {m['shuffled_at_least']:.2%} of trials with shuffled letters. It is improbable by chance, but this was one of several tests in this case. The neighbouring letters do not continue the match, the phrase has no evident meaning, and it comes from FitzGerald's introduction, which we cannot confirm was in the Somerton copy.", "Treat it as a lead for a person to check against that edition, not as a decipherment."]},
            {"heading": "Attempt: substitution", "verdict": r["verdict"], "paragraphs": ["With 44 letters, many plausible keys exist. These readings show why short ciphers produce confident-looking nonsense."],
             "table": _t(["Language", "z", "Best reading (not a solution)"], [[h["language"], h["z"], h["plaintext"]] for h in r["hypotheses"]])}]


def kryptos_sections(r):
    e = r["k4_elimination"]
    return [{"heading": "Control: K1, K2 and K3 fall to our tools", "paragraphs": ["K1 and K2 use a Quagmire III cipher with the KRYPTOS alphabet and keys PALIMPSEST and ABSCISSA. K3 is found by searching double grid rotations. The sculpture's own misspellings are preserved."],
             "mono": [{"label": "K1", "text": r["k1"]}, {"label": "K2", "text": r["k2"]}, {"label": f"K3 (grid widths {r['k3_params'][:2]})", "text": r["k3"]}]},
            {"heading": "K4: testing periodic models against the clues", "paragraphs": [r["k4_status"], "Sanborn has published 24 plaintext letters: EASTNORTHEAST at positions 22 to 34 and BERLINCLOCK at 64 to 74. If a repeating key were used, two clues falling on the same key position must imply the same key letter. That gives a strict test with no statistics involved.", f"Of {e['models_total']} models (standard or KRYPTOS alphabet, three cipher variants, periods 1 to 48), {e['eliminated']} are ruled out and {len(e['survivors_with_real_constraints'])} survive a real test. Periods {e['untestable_periods']} cannot be tested: no two clue letters share a key position there.", "So K4 is not any simple periodic cipher of these kinds with a period that the clues can reach, matching the community's long-held view that it needs an extra layer."],
             "mono": [{"label": "K4 ciphertext", "text": r["k4"]}]}]


def voynich_sections(r):
    langs = r["languages"]
    rows = [["Voynich (EVA)", r["eva"]["h1"], r["eva"]["h2"], r["eva"]["mean_word_length"], r["eva"]["zipf_slope"], r["eva"]["adjacent_word_repeat_rate"]],
            ["Voynich (merged glyphs)", r["glyph_merged"]["h1"], r["glyph_merged"]["h2"], r["glyph_merged"]["mean_word_length"], r["glyph_merged"]["zipf_slope"], r["glyph_merged"]["adjacent_word_repeat_rate"]]]
    rows += [[k, v["h1"], v["h2"], v["mean_word_length"], v["zipf_slope"], v["adjacent_word_repeat_rate"]] for k, v in langs.items()]
    low = max(v["h2"] for v in langs.values()), min(v["h2"] for v in langs.values())
    return [{"heading": "Why this is not a decryption attempt", "paragraphs": ["We don't know the alphabet, the language or even whether the text carries meaning. Statistics can still rule explanations in or out."], "table": _t(["Words", "Vocabulary", "Lines", "Folios"], [[r["eva"]["word_count"], r["eva"]["vocabulary"], r["lines"], r["folios"]]])},
            {"heading": "Finding: unusually predictable", "paragraphs": [f"Each character is far more predictable from the one before it than in any comparison language: conditional entropy {r['eva']['h2']} bits, against {low[1]} to {low[0]} for our six languages. Treating common EVA groups as single glyphs only raises it to {r['glyph_merged']['h2']}. Fully shuffled text has {r['shuffled_h2']}.", "A simple letter-for-letter substitution preserves conditional entropy, so this rules out simple substitution of ordinary text in these six languages, under this transliteration. Different glyph divisions, abbreviation systems or word-structure rules could explain it."],
             "table": _t(["Text", "H1", "H2", "Word length", "Zipf slope", "Adjacent repeats"], rows)},
            {"heading": "Two dialects", "paragraphs": ["Prescott Currier noticed two statistical 'languages' in the manuscript. Word frequencies show it plainly."], "table": _t(["Word", "Currier A per 1000", "Currier B per 1000"], [[d["word"], d["A_per_1000"], d["B_per_1000"]] for d in r["a_b_diff"]])},
            {"heading": "Solver trial", "paragraphs": ["We forced 1,200 words onto each language with a substitution solver. Real order scores above shuffled order simply because the text has structure. None of the outputs read as language, which is what the entropy result predicts."], "table": _t(["Language", "Score", "Shuffled", "Output excerpt (not a solution)"], [[t["language"], t["score"], t["shuffled_score"], t["excerpt"]] for t in r["solver_trial"]])}]
