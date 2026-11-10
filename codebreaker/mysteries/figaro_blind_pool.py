"""Round 53: the method that read L. R. G. (Round 52), screened over every other letter-digit signature.

For each signature, the OCR tokens containing digits are pooled (ads already in a family are left out) and solved blind
as one homophonic substitution of French: best of 7 seeds by score, seed agreement, 3 shuffled copies solved the same
way, and a planted control of the same length and symbol count. Gates as in Round 52. OCR loses digits, so a pass here
is a reason to transcribe the scans, not a reading."""
import json
import random
import re
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

from ..languages import ROOT
from ..validation import coverage
from .figaro_codebook import _homo
from .figaro_keys import OUT
from .figaro_lc15 import planted

RESULT = ROOT / "data/results/figaro_blind_pool.json"
MIN_SYMBOLS, SHUFFLES = 300, 3
EXCLUDE = ("VTA", "Valentin", "LRG", "LC15")


def family_members() -> set:
    known = {e["image"] for e in json.loads((ROOT / "data/results/figaro_2119_timeline.json").read_text())["timeline"]}
    fam = json.loads((OUT / "letter_digit_family.json").read_text())
    return known | set(fam["ads"]) | set(fam.get("checked_screen", {})) | set(fam.get("checked_rescreen", {}))


def pools() -> dict:
    ads = {a["image"].replace("/", "_"): a for a in json.loads((OUT / "ads.json").read_text())}
    raw, known, out = json.loads((OUT / "ocr_raw.json").read_text()), family_members(), defaultdict(list)
    for n, e in raw.items():
        a = ads.get(n)
        if a is None or a["solved"] in (True, "True") or n in known or "-" not in n or any(x in n for x in EXCLUDE):
            continue
        toks = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", " ".join(e.get("tesseract") or [])) if re.search(r"\d", t) and len(t) >= 2]
        s = "".join(toks)
        if len(s) >= 15:
            out[n.split("-", 1)[1][:-4]].append([n, s])
    return {k: v for k, v in out.items() if sum(len(s) for _, s in v) >= MIN_SYMBOLS}


def judge(sig: str, ads: list, ex) -> dict:
    seq = list("".join(s for _, s in ads))
    runs = sorted(ex.map(_homo, [(seq, i) for i in range(7)]), key=lambda x: -x[0])
    s, reading, key = runs[0]
    rnd, null = random.Random(53), []
    for _ in range(SHUFFLES):
        sh = seq[:]
        rnd.shuffle(sh)
        b = max(ex.map(_homo, [(sh, i) for i in range(7)]), key=lambda x: x[0])
        null.append((b[0], coverage(b[1], "fr")))
    pseq, plain = planted(len(seq), len(set(seq)))
    _, pread, _ = max(ex.map(_homo, [(pseq, i) for i in range(7)]), key=lambda x: x[0])
    acc, cov, pcov = sum(a == b for a, b in zip(pread.lower(), plain)) / len(plain), coverage(reading, "fr"), coverage(pread, "fr")
    gates = {"control": acc >= 0.7, "null": s > max(n[0] for n in null) + 0.15 and cov > max(n[1] for n in null), "reads": cov >= 0.8 * pcov}
    return {"signature": sig, "ads": len(ads), "symbols": len(seq), "distinct": len(set(seq)), "score": round(s, 3),
            "seeds_converged": sum(abs(r[0] - s) < 1e-6 and r[2] == key for r in runs), "coverage": cov,
            "null_score": round(max(n[0] for n in null), 3), "null_coverage": max(n[1] for n in null), "planted_accuracy": round(acc, 3),
            "planted_coverage": pcov, "gates": {**gates, "passed": all(gates.values())}, "reading": reading[:240].lower(), "images": [n for n, _ in ads]}


def run() -> dict:
    rows = []
    with ProcessPoolExecutor(7) as ex:
        for sig, ads in sorted(pools().items(), key=lambda x: -sum(len(s) for _, s in x[1])):
            rows.append(judge(sig, ads, ex))
    return {"id": "figaro_blind_pool", "signatures": len(rows), "passed": [r["signature"] for r in rows if r["gates"]["passed"]], "rows": rows}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(res["signatures"], res["passed"])
    for r in res["rows"]:
        print(r["signature"], r["symbols"], r["distinct"], r["score"], r["null_score"], r["coverage"], r["null_coverage"], r["planted_accuracy"], r["seeds_converged"], r["gates"], r["reading"][:70])
