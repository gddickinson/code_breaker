"""Apply the Le Figaro writers' documented systems to every ad, and test them on solved ads first."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher

import numpy as np

from ..languages import ROOT, score
from ..segment import segment
from ..text import A, letters
from ..validation import coverage

OUT = ROOT / "data/sources/figaro"
NOW = A.replace("W", "")
VIG_KEYS = ["CEAD", "BCD", "CD", "AB", "ABC", "BC", "DE"]
MIN_LETTERS = 20


def cipher_text(lines: list[str]) -> str:
    """Letters from words that look enciphered: no digits, and no capitals after the first letter."""
    out = []
    for line in lines:
        for tok in re.split(r"[\s\-—.,;:]+", line):
            t = tok.strip("'\"()")
            if len(t) >= 2 and t.isalpha() and t[1:].islower():
                out.append(t)
    return letters("".join(out))


def shift(t, k, alpha):
    return "".join(alpha[(alpha.index(c) + k) % len(alpha)] if c in alpha else c for c in t)


def vig(t, key, alpha):
    ks = [alpha.index(c) for c in key]
    out, i = [], 0
    for c in t:
        if c in alpha:
            out.append(alpha[(alpha.index(c) - ks[i % len(ks)]) % len(alpha)])
            i += 1
        else:
            out.append(c)
    return "".join(out)


def candidates(t):
    for source, x in (("", t), ("reversed, ", t[::-1])):
        if source:
            yield "reversed", x
        for k in range(1, 26):
            yield f"{source}Caesar {k}", shift(x, k, A)
        for k in range(1, 25):
            yield f"{source}Caesar {k}, no W", shift(x.replace("W", "V"), k, NOW)
        yield f"{source}Atbash", "".join(A[25 - A.index(c)] for c in x)
        for key in VIG_KEYS:
            yield f"{source}Vigenere {key}", vig(x, key, A)
            yield f"{source}Vigenere {key}, no W", vig(x.replace("W", "V"), key, NOW)


def best(t):
    top = (-1.0, -99.0, "", t)
    for name, p in candidates(t):
        c = coverage(p[:400], "fr")
        s = score(p, "fr")
        if (c, s) > top[:2]:
            top = (c, s, name, p)
    return top


def job(a):
    name, lines_t, lines_r, seed = a
    picks = [x for x in (cipher_text(lines_r), cipher_text(lines_t)) if len(x) >= MIN_LETTERS]
    if not picks:
        return None
    t = max(picks, key=len)
    plain_cov = coverage(t[:400], "fr")
    c, s, method, p = best(t)
    r = random.Random(seed)
    sh = list(t)
    r.shuffle(sh)
    null_c = best("".join(sh))[0]
    return {"image": name, "letters": len(t), "raw": t, "plain_coverage": plain_cov, "coverage": c, "null_coverage": null_c, "score": s, "method": method, "plaintext": p, "reading": segment(p[:260], "fr")}


def run_all(raw, names):
    jobs = [(n, raw[n]["tesseract"], raw[n]["rapid"], 13 + i) for i, n in enumerate(names) if n in raw]
    with ProcessPoolExecutor(6) as ex:
        return [r for r in ex.map(job, jobs, chunksize=8) if r]


def control(raw, ads):
    known = {a["image"].replace("/", "_"): a for a in ads if a["solved"]}
    names = [p.name for p in (OUT / "control").glob("*.jpg")]
    rows = []
    for r in run_all(raw, names):
        truth = letters(re.sub(r"\([a-z]+\)\s*$|\[|\]|\?", "", known[r["image"]]["text"]))
        rows.append({"image": r["image"], "letters": r["letters"], "coverage": r["coverage"], "null": r["null_coverage"], "method": r["method"], "match": round(SequenceMatcher(None, truth, r["plaintext"]).ratio(), 3)})
    return rows


def threshold(rows):
    """Coverage needed by length, from the highest null values seen across all ads of similar length."""
    bins = {}
    for r in rows:
        bins.setdefault(min(r["letters"] // 20, 6), []).append(r["null_coverage"])
    return {b: float(np.max(v)) for b, v in bins.items()}


def run() -> dict:
    raw = json.loads((OUT / "ocr_raw.json").read_text())
    ads = json.loads((OUT / "ads.json").read_text())
    ctrl = control(raw, ads)
    unsolved = sorted({a["image"].replace("/", "_") for a in ads if not a["solved"]})
    rows = run_all(raw, unsolved)
    th = threshold(rows)
    flagged = [r for r in rows if r["coverage"] > max(th[min(r["letters"] // 20, 6)], 0.45) and r["plain_coverage"] < 0.35]
    flagged.sort(key=lambda r: -r["coverage"])
    (OUT / "keys_rows.json").write_text(json.dumps(rows, ensure_ascii=False))
    return {"id": "figaro_keys", "tested": len(rows), "plain_ads": sum(r["plain_coverage"] >= 0.35 for r in rows), "thresholds": th, "control_ads": len(ctrl), "control_recovered": sum(r["match"] >= 0.6 for r in ctrl), "control_rows": sorted(ctrl, key=lambda r: -r["match"])[:12], "flagged": flagged}
