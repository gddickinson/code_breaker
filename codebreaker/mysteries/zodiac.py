"""Zodiac benchmarks: solve Z408, find Z340's period-19 signal, undo it, and test Z13/Z32."""
import random

import numpy as np

from ..attacks.classical import solve_symbols, symbols_to_ints
from ..languages import ROOT
from ..segment import segment
from ..text import letters, similarity

SRC = ROOT / "data/sources"


def load(name: str) -> str:
    return "".join((SRC / "zodiac" / name).read_text(errors="ignore").split())


def bigram_repeats(t: list, p: int) -> int:
    """Repeated symbol pairs among positions p apart: Oranchak's transposition detector."""
    pairs = [(t[i], t[i + p]) for i in range(len(t) - p)]
    return len(pairs) - len(set(pairs))


def period_scan(t: list, max_p: int = 40, n_null: int = 400, seed: int = 0) -> dict:
    r, s = random.Random(seed), list(t)
    real = {p: bigram_repeats(t, p) for p in range(1, max_p + 1)}
    tops = []
    for _ in range(n_null):
        r.shuffle(s)
        tops.append(max(bigram_repeats(s, p) for p in range(1, max_p + 1)))
    best = max(real, key=real.get)
    return {"best_period": best, "repeats": real[best], "by_period": real, "null_mean_of_max": round(float(np.mean(tops)), 2), "null_max": max(tops), "p_any_period": round((1 + sum(x >= real[best] for x in tops)) / (n_null + 1), 4)}


def untranspose(z: str, rows: int = 9, cols: int = 17) -> str:
    """Undo the knight-move reading (down 1, right 2, wrapping each axis) in the two 9-row sections.

    The last two rows were written in normal order.
    """
    size = rows * cols
    out = []
    for sec in (z[:size], z[size:2 * size]):
        out.append("".join(sec[(i % rows) * cols + (2 * i) % cols] for i in range(size)))
    return "".join(out) + z[2 * size:]


def run() -> dict:
    z408, z340 = load("z408.txt"), load("z340.txt")
    truth408, truth340 = letters(load("z408_solved.txt")), letters(load("z340_solved.txt"))
    r408 = solve_symbols(list(z408), "en", True, restarts=8)
    raw = solve_symbols(list(z340), "en", True, restarts=6)
    undone = untranspose(z340)
    r340 = solve_symbols(list(undone), "en", True, restarts=12)
    # Calibration only: positions 252-305 are a reading break found using the published solution.
    keep = list(range(153 + 99)) + list(range(306, 340))
    partial = solve_symbols([undone[i] for i in keep], "en", True, restarts=12)
    partial_truth = "".join(truth340[i] for i in keep)
    key = r408["key"]
    z13, z32 = load("z13.txt"), load("z32.txt")
    apply = lambda t, k: "".join(k.get(c, "?") for c in t)
    return {"id": "zodiac", "z408": {"symbols": len(set(z408)), "accuracy": round(similarity(truth408, r408["plaintext"]), 3), "plaintext": segment(r408["plaintext"])[:420]},
            "z340": {"symbols": len(set(z340)), "period_scan_raw": period_scan(list(z340)), "period_scan_z408_control": period_scan(list(z408)),
                     "period_scan_after_untransposing": period_scan(list(undone)), "raw_accuracy": round(similarity(truth340, raw["plaintext"]), 3), "raw_score": raw["score"],
                     "untransposed_score": r340["score"], "untransposed_plaintext": segment(r340["plaintext"])[:420], "solved_truth": truth340[:120], "untransposed_accuracy": round(similarity(truth340, r340["plaintext"]), 3),
                     "partial_positions": len(keep), "partial_accuracy": round(similarity(partial_truth, partial["plaintext"]), 3), "partial_plaintext": segment(partial["plaintext"])[:420]},
            "short": {"z13": z13, "z32": z32, "z13_with_z408_key": apply(z13, key), "z32_with_z408_key": apply(z32, key), "z13_symbols": len(set(z13)), "z32_symbols": len(set(z32))}}
