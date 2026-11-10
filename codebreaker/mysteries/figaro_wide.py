"""Round 34: columnar transposition keys of width 8 to 16 on the Le Figaro ads, found by hill-climbing.

Both directions are tried: undoing a columnar encipherment, and the reverse (a writer who wrote columns and read rows).
Controls: planted French texts by length and width. Null: each ad's letters shuffled and climbed the same way, so the
search's ability to make noise look French is measured, not assumed. A reading also needs real French words."""
import json
import random
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..kernels import columnar_decrypt
from ..kernels_t import _apply, climb_wide, columnar_encrypt
from ..languages import ROOT, model
from ..segment import segment
from ..text import to_ints, to_text
from ..validation import coverage
from .figaro_transposition import phrases
from .figaro_keys import OUT, cipher_words

RESULT = ROOT / "data/results/figaro_wide.json"
WIDTHS = range(8, 17)
MIN_LETTERS = 80  # the control shows texts of 50 letters overfit at these widths
ITERS, RESTARTS = 30000, 30
SHUFFLES = 4


def search(t: str, seed: int = 0, widths=WIDTHS) -> dict:
    """The best key over all widths that leave at least 3 rows, both directions; scores are per quadgram."""
    tab, ct = model("fr")["table"], to_ints(t)
    best = None
    for k in widths:
        if len(ct) < 3 * k:
            break
        for inverse in (False, True):
            perm, s = climb_wide(ct, k, tab, ITERS, RESTARTS, seed + k, inverse)
            s /= max(len(ct) - 3, 1)
            if best is None or s > best["score"]:
                best = {"score": s, "width": k, "direction": "reverse" if inverse else "undo", "key": [int(x) for x in perm], "text": to_text(_apply(ct, perm, inverse)).lower()}
    return best


def overlap6(a: str, b: str) -> float:
    """Share of 6-letter runs of a found in b: a rotated but correct reading still counts."""
    runs = {b[i:i + 6] for i in range(len(b) - 5)}
    return sum(a[i:i + 6] in runs for i in range(len(a) - 5)) / max(len(a) - 5, 1)


def _control(a):
    n, k, j = a
    plain = "".join(c for c in phrases(1, n, 1000 * n + 10 * k + j)[0] if c.isalpha())
    rnd = random.Random(j)
    perm = np.array(rnd.sample(range(k), k), np.int64)
    p = to_ints(plain)
    ct = to_text(columnar_encrypt(p, perm) if j % 2 == 0 else columnar_decrypt(p, perm)).lower()
    got = search(ct, j)
    return {"letters": n, "width": k, "solved": overlap6(got["text"], plain.lower()) >= 0.7, "width_found": got["width"], "score": got["score"], "coverage": coverage(got["text"].upper(), "fr")}


def _ad(a):
    name, t, seed = a
    rnd = random.Random(seed)
    got = search(t, seed)
    nulls = []
    for _ in range(SHUFFLES):
        s = list(t)
        rnd.shuffle(s)
        g = search("".join(s), seed)
        nulls.append((g["score"], coverage(g["text"].upper(), "fr")))
    return {"image": name, "letters": len(t), "width": got["width"], "direction": got["direction"], "key": got["key"], "score": round(got["score"], 3),
            "coverage": coverage(got["text"].upper(), "fr"), "null_score": round(max(x[0] for x in nulls), 3), "null_coverage": max(x[1] for x in nulls), "reading": segment(got["text"], "fr")}


def ad_texts() -> list[tuple]:
    """Unsolved ads with enough letters; ads the Round 36 filter finds to be abbreviated plain French are left out."""
    from .figaro_plainness import RESULT as PLAIN

    plain = set(json.loads(PLAIN.read_text())["plain_images"]) if PLAIN.exists() else set()
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    jobs = []
    for i, a in enumerate(json.loads((OUT / "ads.json").read_text())):
        if a["solved"]:
            continue
        n = a["image"].replace("/", "_")
        sets = [e for s in (otsu, raw) for e in s.get(n, {}).values() if e]
        t = "".join(max((cipher_words(e) for e in sets), key=lambda w: sum(map(len, w)), default=[]))
        if len(t) >= MIN_LETTERS and coverage(t[:400], "fr") < 0.35 and n not in plain:
            jobs.append((n, t[:400], 3400 + i))
    return jobs


def run(workers: int = 7) -> dict:
    cases = [(n, k, j) for n in (80, 120) for k in (8, 10, 12, 14, 16) for j in range(6)]
    jobs = ad_texts()
    with ProcessPoolExecutor(workers) as ex:
        ctrl = list(ex.map(_control, cases, chunksize=2))
        rows = list(ex.map(_ad, jobs, chunksize=1))
    table = {}
    for c in ctrl:
        d = table.setdefault(f"{c['letters']} letters", {})
        d.setdefault(str(c["width"]), [0, 0])
        d[str(c["width"])][0] += c["solved"]
        d[str(c["width"])][1] += 1
    solved_cov = sorted(c["coverage"] for c in ctrl if c["solved"])
    cov_gate = solved_cov[len(solved_cov) // 10] if solved_cov else 1.0  # 90% of solved controls reach this
    for r in rows:
        r["beats_null"] = r["score"] > r["null_score"]
        r["passes"] = r["beats_null"] and r["coverage"] >= cov_gate and r["coverage"] > r["null_coverage"]
    rows.sort(key=lambda r: -(r["score"] - r["null_score"]))
    return {"id": "figaro_wide", "control": table, "control_solved": sum(c["solved"] for c in ctrl), "control_n": len(ctrl),
            "coverage_gate": cov_gate, "tested": len(rows), "beat_null": sum(r["beats_null"] for r in rows), "passed": sum(r["passes"] for r in rows), "rows": rows}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print({k: v for k, v in out.items() if k != "rows"})
    for r in out["rows"][:15]:
        print(r["image"], r["letters"], r["width"], r["direction"], r["score"], r["null_score"], r["coverage"], r["null_coverage"], r["reading"][:90])
