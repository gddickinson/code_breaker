"""Ciphertext statistics and cipher-type identification."""
import math
import re
from collections import Counter

import numpy as np

from .languages import LANGS, detect, model
from .text import A, letters, to_ints


def ic(t) -> float:
    """Index of coincidence: ~0.066 for English, ~0.038 for uniform random letters."""
    t = np.asarray(t)
    n = len(t)
    if n < 2:
        return 0.0
    c = np.bincount(t, minlength=26)
    return float((c * (c - 1)).sum() / (n * (n - 1)))


def entropy(symbols) -> float:
    c = Counter(symbols)
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values()) if n else 0.0


def conditional_entropy(symbols) -> float:
    """H(next symbol | this symbol) in bits."""
    symbols = list(symbols)
    return entropy(list(zip(symbols, symbols[1:]))) - entropy(symbols[:-1]) if len(symbols) > 1 else 0.0


def period_ic(t, max_p: int = 30) -> list[dict]:
    """Mean column IC for each candidate key period."""
    return [{"period": p, "ic": round(float(np.mean([ic(t[i::p]) for i in range(p)])), 4)}
            for p in range(1, min(max_p, len(t) // 3) + 1)]


def kasiski(text: str, size: int = 3) -> dict:
    """Distances between repeated n-grams; factors of those distances suggest the period."""
    pos: dict[str, list[int]] = {}
    for i in range(len(text) - size + 1):
        pos.setdefault(text[i:i + size], []).append(i)
    factors: Counter = Counter()
    for p in pos.values():
        for a, b in zip(p, p[1:]):
            factors.update(f for f in range(2, 31) if (b - a) % f == 0)
    return dict(factors.most_common(8))


def likely_period(t, max_p: int = 30) -> list[int]:
    """Candidate periods, smallest good one first, using an IC threshold over the peak."""
    rows = period_ic(t, max_p)
    peak = max(r["ic"] for r in rows)
    good = [r["period"] for r in rows if r["ic"] > 0.92 * peak]
    return good[:4] + [r["period"] for r in sorted(rows, key=lambda r: -r["ic"])[:3] if r["period"] not in good[:4]]


def identify(raw: str) -> list[dict]:
    """Rule-based guesses at the cipher family, with the evidence for each."""
    compact = re.sub(r"\s+", "", raw)
    out = []
    if compact and set(compact) <= set(".-/"):
        out.append(("Morse code", "only dots, dashes and separators"))
    if compact and set(compact) <= set("01"):
        out.append(("Binary encoding", "only 0 and 1"))
    if compact and re.fullmatch(r"[0-9a-fA-F]+", compact) and re.search(r"[a-fA-F]", compact):
        out.append(("Hex-encoded modern ciphertext", "hex digits; test for ECB repeats or XOR"))
    if compact and set(compact.upper()) <= set("AB"):
        out.append(("Baconian", "two-symbol alphabet"))
    if compact.isdigit():
        d = sorted(set(compact))
        out.append(("Digit cipher: Polybius, Nihilist, checkerboard or book cipher", f"digits only, alphabet {''.join(d)}"))
    if compact and set(compact.upper()) <= set("ADFGVX"):
        out.append(("ADFGX / ADFGVX", "only the signal letters ADFGVX"))
    t = to_ints(raw)
    if len(t) >= 20:
        v = ic(t)
        rows = period_ic(t)
        best = max(rows[1:] or rows, key=lambda r: r["ic"])
        lang = detect(raw)[0]
        if v > 0.058:
            if lang["score"] > -5.1:
                out.append(("Plaintext or transposition", f"IC {v:.3f}; already reads like {lang['name']}"))
            else:
                out.append(("Monoalphabetic substitution or transposition", f"IC {v:.3f} matches natural language"))
        elif best["ic"] > 0.058:
            out.append(("Periodic polyalphabetic (Vigenere family)", f"IC {v:.3f}, rising to {best['ic']:.3f} at period {best['period']}"))
        elif v < 0.047:
            out.append(("Long-key polyalphabetic, modern or random", f"IC {v:.3f} is close to uniform"))
        else:
            out.append(("Polygraphic or short-period polyalphabetic", f"IC {v:.3f} is intermediate"))
        if len(t) % 2 == 0 and 9 not in t:
            out.append(("Playfair-family", "even length and no letter J"))
    return [{"family": f, "evidence": e} for f, e in out] or [{"family": "Unknown", "evidence": "too short to classify"}]


def report(raw: str) -> dict:
    """Everything the workbench shows for a pasted ciphertext."""
    text = letters(raw)
    t = to_ints(raw)
    freq = np.bincount(t, minlength=26) if len(t) else np.zeros(26, dtype=int)
    return {
        "length": len(text), "ic": round(ic(t), 4), "entropy": round(entropy(text), 3),
        "frequencies": {A[i]: int(freq[i]) for i in range(26)},
        "english": {A[i]: round(float(model("en")["letter"][i]) * len(text), 1) for i in range(26)},
        "periods": period_ic(t) if len(t) > 6 else [], "kasiski": kasiski(text),
        "identify": identify(raw), "languages": detect(raw) if len(t) > 3 else [],
        "language_names": LANGS,
    }
