"""Map where homophonic solving works: message length against number of distinct symbols."""
from ..attacks.classical import solve_symbols
from ..text import similarity
from ..validation import homophonic_like, sample_plaintext

LENGTHS = [100, 200, 340, 500, 800, 1500]
SYMBOLS = [26, 54, 63, 100, 200, 300]
MARKERS = {"Z408": (408, 54), "Z340 (after untransposing)": (340, 63), "Beale 1": (520, 298), "Beale 3": (618, 263), "Dorabella": (87, 20)}


def cell(n: int, k: int, trials: int = 4) -> float:
    acc = []
    for t in range(trials):
        plain = sample_plaintext(n, "en", 1000 * n + 10 * k + t)
        spec = [0] * 0 + list(range(k))
        enc = homophonic_like(spec, plain, t)
        acc.append(similarity(plain, solve_symbols(enc, "en", True, restarts=4, seed=t)["plaintext"]))
    return round(sum(acc) / trials, 3)


def run() -> dict:
    grid = [[cell(n, k) if k < n else None for k in SYMBOLS] for n in LENGTHS]
    return {"id": "solvability", "lengths": LENGTHS, "symbols": SYMBOLS, "accuracy": grid, "markers": {k: list(v) for k, v in MARKERS.items()}}
