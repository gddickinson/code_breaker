"""D'Agapeyeff: 14x14 route readings and shifted-coordinate models, each with controls."""
from concurrent.futures import ProcessPoolExecutor

from ..languages import LANGS
from ..segment import segment
from ..validation import null_test, positive_control, verdict
from .dagapeyeff import digits, pairs_of


def _grid(p, n=14):
    return [p[i * n:(i + 1) * n] for i in range(n)]


def models(p):
    g = _grid(p)
    n = 14
    yield "columns", [g[r][c] for c in range(n) for r in range(n)]
    yield "columns, bottom up", [g[r][c] for c in range(n) for r in range(n - 1, -1, -1)]
    yield "boustrophedon rows", [x for r in range(n) for x in (g[r] if r % 2 == 0 else g[r][::-1])]
    yield "boustrophedon columns", [g[r if c % 2 == 0 else n - 1 - r][c] for c in range(n) for r in range(n)]
    yield "main diagonals", [g[r][d - r] for d in range(2 * n - 1) for r in range(n) if 0 <= d - r < n]
    t, b, l, r, sp = 0, n - 1, 0, n - 1, []
    while t <= b and l <= r:
        sp += [g[t][c] for c in range(l, r + 1)] + [g[i][r] for i in range(t + 1, b + 1)]
        if t < b:
            sp += [g[b][c] for c in range(r - 1, l - 1, -1)]
        if l < r:
            sp += [g[i][l] for i in range(b - 1, t, -1)]
        t, b, l, r = t + 1, b - 1, l + 1, r - 1
    yield "spiral inward", sp
    yield "spiral outward", sp[::-1]
    yield "reversed", p[::-1]
    firsts, seconds = [x[0] for x in p], [x[1] for x in p]
    size = len(p)
    for k in range(1, 15):
        yield f"coordinates offset by {k}", [firsts[i] + seconds[(i + k) % size] for i in range(size)]
    yield "second coordinates reversed", [firsts[i] + seconds[size - 1 - i] for i in range(size)]


def job(a):
    name, seq, code, tests = a
    nt = null_test(seq, code, False, n_null=8)
    pc = positive_control(seq, code, False, trials=2)
    return {"model": name, "language": LANGS[code], "symbols": len(set(seq)), "z": nt["z"], "score": nt["score"], "null_mean": nt["null_mean"], "control": pc["mean"], "verdict": verdict(pc, nt["z"], tests, nt["plaintext"], nt["score"], code), "reading": segment(nt["plaintext"], code)}


def run() -> dict:
    d = digits()
    p = pairs_of(d[:-3] if d.endswith("000") else d)
    ms = list(models(p))
    tests = len(ms) * len(LANGS)
    jobs = [(n, s, c, tests) for n, s in ms for c in LANGS]
    with ProcessPoolExecutor(4) as ex:
        rows = list(ex.map(job, jobs))
    rows.sort(key=lambda r: -r["z"])
    return {"id": "dagapeyeff_models", "pairs": len(p), "is_square": len(p) == 196, "tests": tests, "rows": rows, "readable": [r for r in rows if r["verdict"].startswith("Readable")]}
