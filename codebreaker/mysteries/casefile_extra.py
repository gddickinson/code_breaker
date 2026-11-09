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
    return [{"heading": "What statistics can say about a lost script", "paragraphs": ["With no known language, the honest targets are structural: how many signs exist, how predictable they are, and how words are built. The estimated inventory adds signs we have not yet seen, using the Chao1 estimator.", "The Phaistos Disc reproduces its published counts of 241 signs and 45 types. Its size suggests a syllabary, but 241 signs is too few for confidence."], "table": _t(["Text", "Signs", "Types", "Estimated inventory", "Size class", "H2", "Word length"], rows), "bars": {"title": "Conditional entropy (bits): lower means more predictable", "items": [{"label": k, "value": v["h2"], "hit": k in r["scripts"]} for k, v in {**r["scripts"], **r["baselines"]}.items()], "unit": "bits"}}]
