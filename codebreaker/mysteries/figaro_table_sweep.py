"""Round 44: every documented substitution table on every unsolved letter ad, not only on the writers listed for it.

Statistic: the best mean French quadgram score over all 60 tables (unmapped letters cost as an unseen quadgram). Null:
20,000 shuffled copies of the same ad's enciphered letters, each also taking the best of all tables, so the search over
tables is paid for. Across ads, Bonferroni and Benjamini-Hochberg thresholds are both reported. Survivors must then
reach the word bar and be read against the scan. Plain abbreviated ads (Round 36 filter) are left out."""
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from numba import njit

from ..languages import ROOT, model
from ..validation import coverage
from .figaro_documented import WORD_BAR, ad_blocks
from .figaro_keys import TABLES

RESULT = ROOT / "data/results/figaro_table_sweep.json"
SHUFFLES = 20000
MISSING = -7.5  # an unmapped letter makes its quadgrams count as unseen


def table_arrays() -> np.ndarray:
    out = np.full((len(TABLES), 26), -1, np.int64)
    for i, t in enumerate(TABLES):
        for c, p in t["map"].items():
            out[i, ord(c) - 65] = ord(p) - 65
    return out


@njit(cache=True)
def best_score(ct, maps, quad):
    best, arg = -1e18, -1
    n = len(ct)
    for k in range(maps.shape[0]):
        s = 0.0
        for i in range(n - 3):
            a, b, c, d = maps[k, ct[i]], maps[k, ct[i + 1]], maps[k, ct[i + 2]], maps[k, ct[i + 3]]
            s += MISSING if a < 0 or b < 0 or c < 0 or d < 0 else quad[a * 17576 + b * 676 + c * 26 + d]
        s /= max(n - 3, 1)
        if s > best:
            best, arg = s, k
    return best, arg


@njit(cache=True)
def null_scores(ct, maps, quad, shuffles, seed):
    np.random.seed(seed)
    out = np.empty(shuffles)
    x = ct.copy()
    for j in range(shuffles):
        np.random.shuffle(x)
        out[j] = best_score(x, maps, quad)[0]
    return out


def _job(a):
    name, blocks, seed = a
    maps, quad = table_arrays(), model("fr")["table"]
    text = "".join(blocks)
    ct = np.array([ord(c) - 65 for c in text if "A" <= c <= "Z"], np.int64)
    s, k = best_score(ct, maps, quad)
    null = null_scores(ct, maps, quad, SHUFFLES, seed)
    p = (np.sum(null >= s) + 1) / (SHUFFLES + 1)
    reading = " ".join("".join(TABLES[k]["map"].get(c, "?") for c in b) for b in blocks)
    return {"image": name, "letters": len(ct), "table": TABLES[k]["id"], "users": TABLES[k]["users"][:8], "score": round(float(s), 3),
            "null_max": round(float(null.max()), 3), "p": float(p), "coverage": coverage(reading.replace(" ", "").replace("?", ""), "fr"), "reading": reading}


def run(workers: int = 7) -> dict:
    plain_path = ROOT / "data/results/figaro_plainness.json"
    plain = set(json.loads(plain_path.read_text())["plain_images"]) if plain_path.exists() else set()
    jobs = [(n, b, 4400 + i) for i, (n, b) in enumerate(sorted(ad_blocks().items())) if n not in plain]
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_job, jobs, chunksize=4))
    m = len(rows)
    rows.sort(key=lambda r: r["p"])
    floor = 1 / (SHUFFLES + 1)
    bh = 0.0
    for i, r in enumerate(rows, 1):
        if r["p"] <= 0.05 * i / m:
            bh = r["p"]
    for r in rows:
        r["bonferroni"] = r["p"] <= 0.05 / m
        r["fdr"] = r["p"] <= bh
        r["candidate"] = r["fdr"] and r["coverage"] >= WORD_BAR
    return {"id": "figaro_table_sweep", "ads": m, "tables": len(TABLES), "shuffles": SHUFFLES, "p_floor": floor, "bonferroni_bar": 0.05 / m,
            "bonferroni": sum(r["bonferroni"] for r in rows), "fdr": sum(r["fdr"] for r in rows), "candidates": [r["image"] for r in rows if r["candidate"]], "rows": rows}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print({k: v for k, v in res.items() if k != "rows"})
    for r in res["rows"][:30]:
        print(r["image"][:16], r["letters"], r["table"], r["p"], r["bonferroni"], r["fdr"], r["coverage"], r["reading"][:80])
