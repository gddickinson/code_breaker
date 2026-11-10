"""Round 35: transposition followed by simple substitution on the long Le Figaro ads.

Two families, each with planted controls near 100 letters and a null that runs the whole search on shuffled copies:
  routes   keyless reading paths (columns, snakes, diagonals, spirals) at widths 2 to 20, then a substitution solve;
  columnar a columnar key of width 4 to 12 and a substitution annealed together (kernels_t.anneal_joint)."""
import json
import random
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..kernels import anneal_mapping, quad_score
from ..kernels_t import _apply, anneal_joint
from ..languages import ROOT, model
from ..segment import segment
from ..text import to_ints, to_text
from ..validation import coverage
from .figaro_transposition import phrases
from .figaro_wide import ad_texts, overlap6

RESULT = ROOT / "data/results/figaro_layered.json"
ROUTE_WIDTHS = range(2, 21)
JOINT_WIDTHS = range(4, 13)
JOINT_MIN = 100  # the control shows joint solves need about 100 letters at width 8, 150 at width 10 and up
JOINT_ITERS, JOINT_RESTARTS = 600000, 20
SHUFFLES = 2


def route(n: int, w: int, name: str) -> list[int]:
    """Plaintext positions in the order a route visits them, on a grid w wide with a short last row."""
    rows = -(-n // w)
    cell = lambda r, c: r * w + c if r * w + c < n else None
    if name == "columns":
        seq = [cell(r, c) for c in range(w) for r in range(rows)]
    elif name == "columns up":
        seq = [cell(r, c) for c in range(w) for r in range(rows - 1, -1, -1)]
    elif name == "snake columns":
        seq = [cell(r if c % 2 == 0 else rows - 1 - r, c) for c in range(w) for r in range(rows)]
    elif name == "snake rows":
        seq = [cell(r, c if r % 2 == 0 else w - 1 - c) for r in range(rows) for c in range(w)]
    elif name == "diagonals":
        seq = [cell(r, d - r) for d in range(rows + w - 1) for r in range(rows) if 0 <= d - r < w]
    elif name == "anti-diagonals":
        seq = [cell(r, w - 1 - (d - r)) for d in range(rows + w - 1) for r in range(rows) if 0 <= d - r < w]
    elif name in ("spiral in", "spiral out"):
        t, b, lft, rt, seq = 0, rows - 1, 0, w - 1, []
        while t <= b and lft <= rt:
            seq += [cell(t, c) for c in range(lft, rt + 1)] + [cell(i, rt) for i in range(t + 1, b + 1)]
            if t < b:
                seq += [cell(b, c) for c in range(rt - 1, lft - 1, -1)]
            if lft < rt:
                seq += [cell(i, lft) for i in range(b - 1, t, -1)]
            t, b, lft, rt = t + 1, b - 1, lft + 1, rt - 1
        if name == "spiral out":
            seq = seq[::-1]
    else:
        raise ValueError(name)
    return [i for i in seq if i is not None]


ROUTES = ("columns", "columns up", "snake columns", "snake rows", "diagonals", "anti-diagonals", "spiral in", "spiral out")


def route_texts(ct: np.ndarray):
    """Every route, width and direction: 'undo' if the route made the cipher, 'reverse' if it was read the other way."""
    n = len(ct)
    for w in ROUTE_WIDTHS:
        if n < 3 * w:
            break
        for name in ROUTES:
            order = np.array(route(n, w, name))
            if (order == np.arange(n)).all():  # e.g. diagonals of a 2-wide grid: no transposition at all
                continue
            undo = np.empty(n, np.int32)
            undo[order] = ct
            yield f"{name}, width {w}, undo", undo
            yield f"{name}, width {w}, reverse", ct[order].astype(np.int32)


def solve_sub(t: np.ndarray, seed: int, iters: int = 30000, restarts: int = 4):
    m = model("fr")
    key, _ = anneal_mapping(t, 26, m["table"], iters, restarts, seed, False, 3.0, m["letter"], 0.0)
    plain = key[t].astype(np.int32)
    return quad_score(plain, m["table"]) / max(len(t) - 3, 1), to_text(plain).lower()


def search_routes(text: str, seed: int = 0) -> dict:
    """The best route reading after a substitution solve. Shortlists by quadgram score after a quick solve."""
    ct = to_ints(text)
    quick = sorted(((solve_sub(t, seed, 8000, 2)[0], name, t) for name, t in route_texts(ct)), key=lambda x: -x[0])[:12]
    best = max(((*solve_sub(t, seed), name) for _, name, t in quick), key=lambda x: x[0])
    return {"score": best[0], "text": best[1], "model": best[2]}


def search_joint(text: str, seed: int = 0, widths=JOINT_WIDTHS, iters: int = JOINT_ITERS, restarts: int = JOINT_RESTARTS) -> dict:
    tab, ct = model("fr")["table"], to_ints(text)
    best = None
    for k in widths:
        if len(ct) < 3 * k:
            break
        for inverse in (False, True):
            perm, key, s = anneal_joint(ct, k, tab, iters, restarts, seed + k, inverse)
            s /= max(len(ct) - 3, 1)
            if best is None or s > best["score"]:
                best = {"score": s, "model": f"columnar width {k}, {'reverse' if inverse else 'undo'}", "text": to_text(key[_apply(ct, perm, inverse)]).lower()}
    return best


def _plant(kind, n, w, j):
    plain = "".join(c for c in phrases(1, n, 9000 + 100 * n + 10 * w + j)[0] if c.isalpha())
    rnd, p = random.Random(j), to_ints(plain)
    sub = np.array(rnd.sample(range(26), 26), np.int32)
    if kind == "routes":
        name = ROUTES[j % len(ROUTES)]
        mid = p[np.array(route(len(p), w, name))]
    else:
        from ..kernels_t import columnar_encrypt
        mid = columnar_encrypt(p, np.array(rnd.sample(range(w), w), np.int64))
    return plain.lower(), to_text(sub[mid]).lower()


def _control(a):
    kind, n, w, j = a
    plain, ct = _plant(kind, n, w, j)
    got = search_routes(ct, j) if kind == "routes" else search_joint(ct, j, widths=[w])
    return {"kind": kind, "letters": n, "width": w, "solved": overlap6(got["text"], plain) >= 0.7, "coverage": coverage(got["text"].upper(), "fr")}


def _ad(a):
    kind, name, t, seed = a
    fn = search_routes if kind == "routes" else search_joint
    rnd, got = random.Random(seed), fn(t, seed)
    nulls = []
    for _ in range(SHUFFLES):
        s = list(t)
        rnd.shuffle(s)
        g = fn("".join(s), seed)
        nulls.append((g["score"], coverage(g["text"].upper(), "fr")))
    return {"kind": kind, "image": name, "letters": len(t), "model": got["model"], "score": round(got["score"], 3), "coverage": coverage(got["text"].upper(), "fr"),
            "null_score": round(max(x[0] for x in nulls), 3), "null_coverage": max(x[1] for x in nulls), "reading": segment(got["text"], "fr")}


def run(workers: int = 7, kinds=("routes", "columnar"), previous: dict | None = None) -> dict:
    cases = [("routes", n, w, j) for n in (80, 100) for w in (4, 6, 9, 12) for j in range(4)]
    cases += [("columnar", n, w, j) for n in (100, 150) for w in (6, 8, 10) for j in range(4)]
    ads = ad_texts()
    jobs = [("routes", n, t, s) for n, t, s in ads] + [("columnar", n, t, s) for n, t, s in ads if len(t) >= JOINT_MIN]
    cases, jobs = [c for c in cases if c[0] in kinds], [j for j in jobs if j[0] in kinds]
    with ProcessPoolExecutor(workers) as ex:
        ctrl = list(ex.map(_control, cases, chunksize=1))
        rows = list(ex.map(_ad, jobs, chunksize=1))
    out = previous or {"id": "figaro_layered", "families": {}}
    for kind in kinds:
        cs = [c for c in ctrl if c["kind"] == kind]
        table = {}
        for c in cs:
            table.setdefault(f"{c['letters']} letters", {}).setdefault(str(c["width"]), [0, 0])
            table[f"{c['letters']} letters"][str(c["width"])][0] += c["solved"]
            table[f"{c['letters']} letters"][str(c["width"])][1] += 1
        cov = sorted(c["coverage"] for c in cs if c["solved"])
        gate = cov[len(cov) // 10] if cov else 1.0
        rs = sorted((r for r in rows if r["kind"] == kind), key=lambda r: -(r["coverage"] - r["null_coverage"]))
        for r in rs:
            r["passes"] = r["score"] > r["null_score"] and r["coverage"] >= gate and r["coverage"] > r["null_coverage"]
        out["families"][kind] = {"control": table, "solved": sum(c["solved"] for c in cs), "n": len(cs), "coverage_gate": gate, "tested": len(rs), "passed": sum(r["passes"] for r in rs), "rows": rs}
    return out


if __name__ == "__main__":
    import sys

    kinds = tuple(sys.argv[1:]) or ("routes", "columnar")
    res = run(kinds=kinds, previous=json.loads(RESULT.read_text()) if RESULT.exists() and len(kinds) < 2 else None)
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for kind, f in res["families"].items():
        print(kind, {k: v for k, v in f.items() if k != "rows"})
        for r in f["rows"][:8]:
            print(" ", r["image"], r["letters"], r["model"], r["score"], r["null_score"], r["coverage"], r["null_coverage"], r["reading"][:80])
