"""Round 46: more ads of the two correspondences, searched by date with their own key only.

Berthe (table 2217, Oct 1881 to Dec 1882): every unsolved ad from June 1881 to June 1883 is scored with table 2217
alone (mean quadgram score of its enciphered blocks) against 20,000 shuffled copies. Valentin (the V. T. A. key, Oct
1878 to Jan 1879): every unsolved ad of 1878 and 1879 is scored with the V. T. A. key (segmented word share of its
non-word tokens) against 20,000 shuffled keys. One key per window keeps the test small; Bonferroni over each window."""
import json
import random

import numpy as np

from ..languages import ROOT, model
from . import figaro_vta as V
from .figaro_documented import ad_blocks
from .figaro_keys import OUT, TABLES
from .figaro_table_sweep import best_score, null_scores
from .figaro_vta_sweep import tokens

RESULT = ROOT / "data/results/figaro_windows.json"
SHUFFLES = 20000


def in_window(name: str, start: str, end: str) -> bool:
    return start <= name[5:13] <= end


def berthe(start="18810601", end="18830630") -> list[dict]:
    t = next(x for x in TABLES if x["id"] == "2217")
    maps = np.full((1, 26), -1, np.int64)
    for c, p in t["map"].items():
        maps[0, ord(c) - 65] = ord(p) - 65
    quad, rows = model("fr")["table"], []
    for i, (n, blocks) in enumerate(sorted(ad_blocks().items())):
        if not in_window(n, start, end):
            continue
        ct = np.array([ord(c) - 65 for c in "".join(blocks) if "A" <= c <= "Z"], np.int64)
        s = best_score(ct, maps, quad)[0]
        null = null_scores(ct, maps, quad, SHUFFLES, 4600 + i)
        rows.append({"image": n, "letters": len(ct), "score": round(float(s), 3), "p": float((np.sum(null >= s) + 1) / (SHUFFLES + 1)),
                     "reading": " ".join("".join(t["map"].get(c, "?") for c in b) for b in blocks)[:200]})
    return rows


def valentin(start="18780101", end="18791231") -> list[dict]:
    ads = {a["image"].replace("/", "_"): a for a in json.loads((OUT / "ads.json").read_text())}
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    saved, rows = V.SCORING, []
    V.SCORING = "segmented"
    try:
        key = V.full_key()
        for i, n in enumerate(sorted(set(otsu) | set(raw))):
            a = ads.get(n)
            if a is None or a["solved"] in (True, "True") or not in_window(n, start, end):
                continue
            words = tokens(" ".join((raw.get(n, {}).get("tesseract") or []) + (otsu.get(n, {}).get("tesseract") or [])))
            if sum(map(len, words)) < 12:
                continue
            real, rnd = V.word_share(words, key), random.Random(4700 + i)
            null = [V.word_share(words, V.shuffled_key(key, rnd)) for _ in range(SHUFFLES)]
            rows.append({"image": n, "words": len(words), "share": round(real, 3), "p": (sum(x >= real for x in null) + 1) / (SHUFFLES + 1),
                         "reading": " ".join(V.decode(w, key) for w in words)[:200]})
    finally:
        V.SCORING = saved
    return rows


def run() -> dict:
    out = {"id": "figaro_windows"}
    for name, fn in (("berthe", berthe), ("valentin", valentin)):
        rows = sorted(fn(), key=lambda r: r["p"])
        bar = 0.05 / max(len(rows), 1)
        for r in rows:
            r["passes"] = r["p"] <= bar
        out[name] = {"ads": len(rows), "bar": bar, "passed": [r["image"] for r in rows if r["passes"]], "rows": rows}
    return out


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for name in ("berthe", "valentin"):
        w = res[name]
        print(name, w["ads"], w["bar"], w["passed"])
        for r in w["rows"][:10]:
            print("  ", r["image"][:24], r["p"], r["passes"], r["reading"][:90])
