"""Round 43: re-rank, from transcriptions of the scans, the ads whose own documented system ranked 2nd to 10th on OCR.

Same test as Round 42 (every documented system, no free parameter, own system's rank among all; per-ad shuffle null),
on words read by eye before decoding. Ads that turned out to be plain abbreviated French or to use digits are listed
but not ranked: the letter tables do not apply to them."""
import json

from ..languages import ROOT
import random

from ..validation import coverage
from .figaro_documented import apply, judge, shuffle_null, systems
from .figaro_keys import OUT
from .figaro_pooled import signature

RESULT = ROOT / "data/results/figaro_rerank.json"
DATA = json.loads((OUT / "rerank_transcription.json").read_text())


def any_system(words: list[str], allsys: list[dict], n: int = 300, seed: int = 43) -> dict:
    """The best of all documented systems, with a null that takes the best of all systems on each shuffled copy."""
    read = lambda ws, s: "".join(apply(s, w) for w in ws).replace("?", "")
    best = max(allsys, key=lambda s: coverage(read(words, s), "fr"))
    cov = coverage(read(words, best), "fr")
    rnd, flat, sizes, null = random.Random(seed), list("".join(words)), [len(w) for w in words], []
    for _ in range(n):
        rnd.shuffle(flat)
        pos, parts = 0, []
        for k in sizes:
            parts.append("".join(flat[pos:pos + k]))
            pos += k
        null.append(max(coverage(read(parts, s), "fr") for s in allsys))
    return {"system": best["id"], "coverage": cov, "reading": " ".join(apply(best, w) for w in words),
            "null_p": round((sum(x >= cov for x in null) + 1) / (n + 1), 4), "null_max": max(null)}


def run() -> dict:
    allsys = systems()
    byid = {s["id"]: s for s in allsys}
    users = {}
    for s in allsys:
        for u in s["users"]:
            users.setdefault(u, set()).add(s["id"])
    before = {r["image"]: r["rank"] for r in json.loads((ROOT / "data/results/figaro_documented.json").read_text())["rows"]}
    rows = []
    for image, text in DATA["letters"].items():
        words = [w.upper() for w in text.split()]
        r = judge(words, allsys, users[signature(image)])
        ns = shuffle_null(words, byid[r["own"]])
        r["null_p"] = round((sum(x >= r["coverage"] for x in ns) + 1) / (len(ns) + 1), 4)
        rows.append({"image": image, "rank_ocr": before.get(image), **r, "any": any_system(words, allsys)})
    return {"id": "figaro_rerank", "rows": rows, "firsts": sum(r["rank"] == 1 for r in rows), "plain_abbreviated": DATA["plain_abbreviated"], "with_digits": DATA["with_digits"]}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for r in out["rows"]:
        print(r["image"][:13], r["own"], r["rank_ocr"], "->", r["rank"], r["coverage"], r["null_p"], r["reading"])
        a = r["any"]
        print("   any system", a["system"], a["coverage"], "p", a["null_p"], "null max", a["null_max"], a["reading"])
