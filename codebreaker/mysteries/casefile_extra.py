"""Case-file sections for Zodiac, Dorabella, the sweep, solvability and lost scripts."""


def _t(cols, rows):
    return {"cols": cols, "rows": rows}


def zodiac_sections(r):
    a, z = r["z340"], r["z408"]
    raw, after = a["period_scan_raw"], a["period_scan_after_untransposing"]
    bars = [{"label": f"Period {p}", "value": v, "hit": p == str(raw["best_period"])} for p, v in raw["by_period"].items() if int(p) <= 30]
    return [{"heading": "Benchmark: Z408 falls", "paragraphs": [f"Our solver recovers {z['accuracy']:.0%} of the letters of Z408 with no help, across {z['symbols']} symbols. The transcription came from David Oranchak's AZdecrypt collection."], "mono": [{"label": "Z408 as read by our solver", "text": z["plaintext"]}]},
            {"heading": "Z340: the period-19 signature", "paragraphs": [f"Repeated symbol pairs at a fixed distance reveal transposition. Z340 peaks at period {raw['best_period']} with {raw['repeats']} repeats, against a shuffled maximum of {raw['null_max']}.", f"After undoing the known diagonal reading, the peak moves to period {after['best_period']} with {after['repeats']} repeats, where a substitution should have it."], "bars": {"title": "Repeated symbol pairs by period in Z340", "items": bars, "unit": "repeats"}},
            {"heading": "Z340: not yet read by us", "paragraphs": [f"The structure is recovered but the letters are not. Accuracy against the published solution is {a['untransposed_accuracy']:.0%}. The solvability map says a text of this size should solve at about 99%, so a detail of the transposition is probably still wrong. This is scheduled work, and we are not claiming a solve.", f"Calibration using the published solution shows the reading order is right for {a.get('partial_positions', 0)} of 340 positions, with a break after position 99 of the second block. On those positions alone the solver recovers {a.get('partial_accuracy', 0):.0%}."], "mono": [{"label": "Solver output on the verified positions", "text": a.get("partial_plaintext", "")}]},
            {"heading": "Z13 and Z32", "table": _t(["Cipher", "Text", "Distinct symbols", "With the Z408 key"], [["Z13", r["short"]["z13"], r["short"]["z13_symbols"], r["short"]["z13_with_z408_key"]], ["Z32", r["short"]["z32"], r["short"]["z32_symbols"], r["short"]["z32_with_z408_key"]]]), "paragraphs": ["These are far below the length needed for a unique solution. Claimed solutions, including names, cannot be verified from the ciphertext alone."]}]


def dorabella_sections(r):
    return [{"heading": "The text", "mono": [{"label": f"AZdecrypt transcription, {r['symbols']} distinct symbols", "text": r["text"]}], "table": _t(["Transcription", "Compared with", "Symbol pairs in disagreement"], [[a["a"], a["b"], f"{a['pair_disagreement']:.1%}"] for a in r["agreement"]]), "paragraphs": ["Three transcriptions are compared by whether they treat symbol pairs as the same glyph. Elgar's curves are ambiguous, so we run every attack on each."]},
            {"heading": "Attempt", "verdict": r["verdict"], "paragraphs": [f"{r['tests']} combinations of transcription, direction and language. The solver reads a control message of 87 letters almost perfectly, yet the best real outputs are not language.", "A short text can beat shuffled copies merely because repeated patterns exist, so this result is not a decipherment."], "table": _t(["Transcription", "Direction", "Language", "z", "Output (not a solution)"], [[h["transcription"], h["direction"], h["language"], h["z"], h["plaintext"][:64]] for h in r["hypotheses"][:10]])}]


def sweep_sections(r):
    rows = [[x["name"], x["length"], x["symbols"], x.get("model", ""), x.get("language", ""), x["z"] if x["z"] is not None else "", x.get("control", ""), (x.get("verdict") or x.get("status", ""))[:90]] for x in r["rows"]]
    return [{"heading": "What was tested", "paragraphs": [f"Every one of the {r['files']} files in the AZdecrypt Unsolved collection that has no case file of its own, in six languages, with shuffled nulls and controls.", "High z means only that the symbol order is non-random. The verdict column shows whether a solver could have read it and whether the output reads as text."], "table": _t(["Cryptogram", "Length", "Symbols", "Model", "Best language", "z", "Control", "Verdict"], rows)}]


def solvability_sections(r):
    return [{"heading": "Where homophonic solving works", "paragraphs": ["Each cell is the share of letters recovered from real English enciphered with that many symbols. It shows why some mysteries are approachable and others cannot be solved by statistics alone."], "heatmap": {"rows": r["lengths"], "cols": r["symbols"], "values": r["accuracy"], "row_label": "Message length", "col_label": "Distinct symbols", "markers": r["markers"]}}]


def scriptlab_sections(r):
    rows = [[k, v["tokens"], v["signs"], v["estimated_inventory"], v["class"], v["h2"], v["mean_word_length"]] for k, v in {**r["scripts"], **r["baselines"]}.items()]
    return [{"heading": "What statistics can say about a lost script", "paragraphs": ["With no known language, the honest targets are structural: how many signs exist, how predictable they are, and how words are built. The estimated inventory adds signs we have not yet seen, using the Chao1 estimator.", "The Phaistos Disc reproduces its published counts of 241 signs and 45 types. Its size suggests a syllabary, but 241 signs is too few for confidence.", (f"Rongorongo repeats itself across objects: {r['rongo_parallels']['share_on_multiple_tablets']:.0%} of its {r['rongo_parallels']['run_length']}-glyph runs occur on more than one tablet, against {r['rongo_parallels']['shuffled_mean']:.1%} in shuffled tablets." if r.get("rongo_parallels") else "")], "table": _t(["Text", "Signs", "Types", "Estimated inventory", "Size class", "H2", "Word length"], rows), "bars": {"title": "Conditional entropy (bits): lower means more predictable", "items": [{"label": k, "value": v["h2"], "hit": k in r["scripts"]} for k, v in {**r["scripts"], **r["baselines"]}.items()], "unit": "bits"}}]


def beale_forensics_sections(r):
    h, c = r["human"], r["control"]
    labels = {"lag1_corr": "Correlation between neighbouring numbers", "distinct_ratio": "Distinct numbers per number", "share_under_100": "Share at most 100", "last_digit_chi2": "Last-digit unevenness", "small_steps": "Steps of 3 or less", "repeat_within_8": "Repeat within 8 numbers"}
    rows = [[labels[k], h["B2"][k]["observed"], h["B1"][k]["observed"], h["B3"][k]["observed"], h["B2"][k]["sim_mean"]] for k in labels]
    return [{"heading": "Do the numbers behave like a real book cipher?", "paragraphs": ["We simulated honest encipherment: for each letter of English, pick a random matching word. Beale 2 is the known-genuine comparison, because it decodes.", f"Neighbouring numbers in Beale 2 are almost independent (r = {h['B2']['lag1_corr']['observed']}). In Beale 1 r = {h['B1']['lag1_corr']['observed']}, and in Beale 3 r = {h['B3']['lag1_corr']['observed']}. A person drifting through numbers would produce that. So would an encoder working through one region of a text at a time, and the Beale Drift Model case shows such an encoder can match it, so this is not evidence of a hoax on its own.", "Simulated values differ from Beale 2 on several other measures, because real encoders favour early words. Correlation is the measure where Beale 2 matches the simulation."], "bars": {"title": "Correlation between neighbouring numbers", "items": [{"label": n, "value": h[n]["lag1_corr"]["observed"], "hit": n != "B2"} for n in ("B2", "B1", "B3")], "unit": "r"}, "table": _t(["Measure", "Beale 2 (genuine)", "Beale 1", "Beale 3", "Simulated"], rows)},
            {"heading": "Other ways of using a key text", "paragraphs": [f"We tried first, second and last letters of each word, across eight key texts including the Beale pamphlet. Control: a planted last-letter cipher was found at the right offset, z = {c['z']}. Nothing in the real ciphers stands out: the best is z = {r['rules'][0]['z']}, across {len(r['rules'])} combinations."], "table": _t(["Cipher", "Key text", "Rule", "Offsets", "z"], [[x["cipher"], x["key_text"], x["rule"], x["offsets"], x["z"]] for x in r["rules"][:10]])}]


def dagapeyeff_models_sections(r):
    from collections import Counter
    n = Counter(x["verdict"].split(":")[0].split(" (")[0] for x in r["rows"])
    return [{"heading": "The 14 by 14 square", "paragraphs": [f"With the padding removed, the cipher has exactly {r['pairs']} pairs, a perfect 14 by 14 square. We read it by columns, spirals, diagonals and zigzags, and tried sliding the two coordinates against each other. That is {r['tests']} combinations of model and language.", f"Outcomes: {dict(n)}. No model reads as text. Solver controls of this size were recovered, so plain substitution through these reorderings is unlikely."], "table": _t(["Model", "Language", "z", "Control", "Output (not a solution)"], [[x["model"], x["language"], x["z"], x["control"], x["reading"][:64]] for x in r["rows"][:10]])}]


def kryptos_layers_sections(r):
    a = r["autokey"]
    return [{"heading": "Two-layer models against the clues", "paragraphs": [f"Control: we planted a width-7, period-5 cipher at K4's clue positions, and the scan recovered the exact column order: {r['control']['found']}.", f"We then tested {r['models']:,} configurations and {r['orders_tested']:,} column orders: every columnar width from 2 to 9, periods 1 to 12, standard and KRYPTOS alphabets, three key rules, and both layer orders. Survivors with at least six real comparisons: {r['survivors_total']}.", "Limits: this covers regular columnar transposition only. Irregular routes, longer periods, widths of 10 or more, or a different first layer remain open."]},
            {"heading": "Other systems", "paragraphs": [f"Autokey: of {a['models']} models, {a['ciphertext_autokey']} ciphertext-autokey and {a['plaintext_autokey']} plaintext-autokey models fit the clues. Plaintext-autokey lags {a['untestable'][0]} to {a['untestable'][-1]} cannot be tested from the clues." if a["untestable"] else "", f"Hill 2x2: {r['hill']['invertible_2x2_keys_consistent']} invertible keys fit the clues.", f"Letters that encrypt to themselves occur at clue positions {r['self_encryption_positions']}. That rules out plain Playfair and any Enigma-style reflector on K4 as a final step."]}]


def tamam_mnemonic_sections(r):
    return [{"heading": "Initials of a memorised text?", "paragraphs": [f"If the code is a memory aid, its letters might be the initials of a known passage. We searched six large books, allowing misreadings. Control: a hidden 44-letter passage with four errors was located exactly: {r['control']['success']}.", "None of the books beats blocks of ordinary English initials. The code does not appear to be the initials of a passage from these texts."], "table": _t(["Text", "Mismatches, line by line", "Expected", "p", "Whole-code mismatches", "p"], [[x["text"], x["line_mismatches"], x["null_mean"], x["p_lines"], x["whole_code_mismatches"], x["p_whole"]] for x in r["rows"]])}]


def voynich_generators_sections(r):
    return [{"heading": "Which mechanism fits?", "paragraphs": ["Each candidate generated text is scored on six statistics against a sample of the manuscript. Lower distance is closer. Two halves of the real manuscript differ by the noise floor shown below.", f"Noise floor (real against real): {r['split_half_distance']}. No candidate reaches it. A verbose cipher, where each letter becomes one to three glyphs, reproduces the low conditional entropy but makes words far too long.", "The fitted Markov chain is a baseline that learns from the manuscript itself. The self-citation and table models here are simple versions we wrote, so a poor score does not refute the published theories."], "table": _t(["Model", "Distance", "H2", "Word length", "Zipf slope", "Vocabulary per word"], [["Voynich target", 0, r["target"]["h2"], r["target"]["mean_word_length"], r["target"]["zipf_slope"], r["target"]["vocab_ratio"]]] + [[x["model"], x["distance"], x["h2"], x["mean_word_length"], x["zipf_slope"], x["vocab_ratio"]] for x in r["rows"]])}]


def liber_primus_sections(r):
    rows = sorted(r["rows"], key=lambda x: -x["z"])
    return [{"heading": "Solved pages as controls", "paragraphs": [f"Liber Primus uses a 29-rune alphabet. Uniform random runes have an index of coincidence near {r['uniform_ic']}, and English near {r['english_rune_ic']}. Our attacks recover the two pages whose answers are public: page 57 (plain runes, the Parable) and page 56 (a prime-number stream).", "On every other page, shifts, reflections, prime and totient streams and repeating keys up to period 20 stay at shuffled levels. Those pages remain unread."], "table": _t(["Page", "Runes", "IC", "Best attack", "z", "Output"], [[x["page"], x["runes"], x["ic"], x["attack"], x["z"], x["reading"][:64]] for x in rows[:12]])}]


def pigeon_sections(r):
    b = r["substitution"]
    return [{"heading": "What a pigeon carried", "paragraphs": [f"{r['groups']} five-letter groups. The first and last are both {r['indicator']}, the usual sign of an indicator group naming a key or code, so the body is {r['letters']} letters."], "table": _t(["Measure", "Message", "Random letters", "English"], [["Index of coincidence", r["ic"], f"{r['random_ic_mean']} (sd {r['random_ic_sd']})", r["english_ic"]]])},
            {"heading": "Attempt", "verdict": b["verdict"], "paragraphs": [f"The letters are statistically indistinguishable from random: an IC this high or higher appears in {r['p_ic_at_least']:.0%} of random messages, and the best key period is unremarkable (p = {r['p_period']}).", "That is what a one-time pad or a codebook superenciphered with random key looks like. GCHQ has said the message cannot be decoded without the original cryptographic material, and our statistics agree: no amount of computing helps if the key was truly random."]}]


def beale_drift_sections(r):
    t, c3, c1 = r["targets"], r["closest_B3"][0], r["closest_B1"][0]
    return [{"heading": "Testing our own hoax evidence", "paragraphs": ["Earlier we found neighbouring numbers strongly correlated in Beale 1 and 3. We then simulated an honest encoder working from a limited region of a text and moving around it.", f"That honest encoder can reach r = {c3['lag1']} with a window of plus or minus {c3['window']} words, close to Beale 3's {t['B3']['lag1']}. A wider window fits Beale 1 ({c1['lag1']} against {t['B1']['lag1']}). So the correlation does not prove a hoax: it shows that if Beale 3 is real, its author stayed in a narrow part of the key text.", "This narrows what to look for: short key passages, not whole books."], "table": _t(["Window (words each side)", "Chance of moving per letter", "Neighbour correlation", "Distinct ratio"], [[g["window"], g["drift"], g["lag1"], g["distinct"]] for g in r["grid"]])}]
