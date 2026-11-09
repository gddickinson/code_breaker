"""The Bletchingley pigeon message: is it the kind of cipher statistics could ever break?"""
import random
import re

import numpy as np

from ..analysis import ic, period_ic
from ..attacks.classical import solve_symbols
from ..languages import ROOT
from ..text import to_ints
from ..validation import null_test, positive_control, sample_plaintext, verdict

SRC = ROOT / "data/sources/research/wp_nps.txt"


def groups() -> list[str]:
    raw = SRC.read_text()
    block = raw[raw.index("AOAKN"): raw.index("1525/6")]
    return re.findall(r"\b[A-Z]{5}\b", block)


def text() -> str:
    """The first and last groups are identical indicators, so the message body lies between them."""
    return "".join(groups()[1:-1])


def monte(n, stat, trials=4000, seed=0):
    r = np.random.default_rng(seed)
    return np.array([stat(r.integers(0, 26, n)) for _ in range(trials)])


def one_time_pad_like(n, seed):
    return to_ints(sample_plaintext(n, "en", seed)) + np.random.default_rng(seed).integers(0, 26, n)


def run() -> dict:
    g = groups()
    body = text()
    t = to_ints(body)
    sims = monte(len(t), ic)
    english = np.mean([ic(to_ints(sample_plaintext(len(t), "en", s))) for s in range(60)])
    best_period = max(period_ic(t, 20)[1:], key=lambda p: p["ic"])
    per_null = np.array([max(period_ic(np.random.default_rng(s).integers(0, 26, len(t)), 20)[1:], key=lambda p: p["ic"])["ic"] for s in range(300)])
    nt = null_test(list(body), "en", False, n_null=12)
    pc = positive_control(list(body), "en", False)
    return {"id": "pigeon", "groups": len(g), "letters": len(body), "indicator_repeats": g[0] == g[-1], "indicator": g[0], "ic": round(ic(t), 4), "random_ic_mean": round(float(sims.mean()), 4), "random_ic_sd": round(float(sims.std()), 4), "p_ic_at_least": round(float((sims >= ic(t)).mean()), 3), "english_ic": round(float(english), 4),
            "best_period": best_period, "p_period": round(float((per_null >= best_period["ic"]).mean()), 3), "substitution": {"z": nt["z"], "score": nt["score"], "control": pc["mean"], "verdict": verdict(pc, nt["z"], 1, nt["plaintext"], nt["score"])}}
