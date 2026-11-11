"""Archive ciphers (Round 88): homophonic substitution with nulls, word dividers and nomenclator code words.

Early modern diplomatic ciphers (the bulk of archives such as DECODE) mix several devices in one key: each letter has
several symbols (homophones), some symbols mean nothing (nulls), one may mark the end of a word (a divider), and some
stand for whole words or names (the nomenclator). Here: a divider is found first from its spacing (never twice in a
row, gaps distributed like the language's word lengths); then kernels_nom.anneal_nom searches a key of letters (as a homophonic
solve), and from it each symbol in turn takes whichever value scores best: a letter, a null, or one of the language's
most common words. A free search over all three at once fills any text with common words. The controls (nomenclator_eval.py) plant all
four devices in held-out text and count how many symbol occurrences get the right value."""
import re
from collections import Counter

import numpy as np

from ..kernels import quad_score
from ..kernels_nom import _expand, _score, anneal_nom
from ..languages import model
from ..text import A

NULL = 26


def tokens(raw: str) -> list[str]:
    """Numbers or space-separated groups when there are several, else one symbol per character."""
    parts = re.findall(r"\S+", raw)
    if len(parts) > 3 and sum(map(len, parts)) / len(parts) > 1.2:
        return [p.strip(".,;:") for p in parts if p.strip(".,;:")]
    return [c for c in raw if not c.isspace()]


def word_lengths(lang: str, max_len: int = 15) -> np.ndarray:
    """Running-text distribution of word lengths 1..max_len, from the model's word frequencies."""
    m = model(lang)
    d = np.zeros(max_len + 1)
    for w, f in zip(m["words"], m["word_freq"]):
        d[min(len(str(w)), max_len)] += f
    d[0] = 0
    return d / d.sum()


CANDIDATE_KL = 0.8


def find_divider(toks: list[str], lang: str = "en") -> dict:
    """The symbol that best behaves as a word divider, if any. A candidate makes up 8-30% of the text, never follows
    itself, and the gaps between its occurrences fit the language's word-length distribution. KL up to CANDIDATE_KL
    makes it a candidate only: real dividers distorted by nulls and code words reached 0.45, while a frequent German
    letter scored 0.22, so solve() decides by decoding both ways."""
    n = len(toks)
    ref = word_lengths(lang)
    best = {"symbol": None, "kl": None}
    for s, c in Counter(toks).most_common(8):
        if not 0.08 <= c / n <= 0.30:
            continue
        pos = [i for i, t in enumerate(toks) if t == s]
        gaps = np.diff([-1] + pos) - 1
        if (gaps == 0).any():
            continue
        h = np.bincount(np.clip(gaps, 0, len(ref) - 1), minlength=len(ref)) / len(gaps)
        m = h > 0
        kl = float(np.sum(h[m] * np.log(h[m] / np.clip(ref[m], 1e-6, 1))))
        if best["kl"] is None or kl < best["kl"]:
            best = {"symbol": s, "kl": round(kl, 3), "share": round(c / n, 3)}
    best["divider"] = best["kl"] is not None and best["kl"] <= CANDIDATE_KL
    return best


def code_words(lang: str, n: int) -> list[str]:
    return [str(w) for w in model(lang)["words"] if len(str(w)) >= 2][:n]


def _values(words: list[str]):
    exp = [[i] for i in range(26)] + [[]] + [[A.index(c) for c in w] for w in words]
    lens = np.array([len(e) for e in exp], np.int32)
    starts = np.concatenate([[0], np.cumsum(lens)[:-1]]).astype(np.int32)
    flat = np.array([c for e in exp for c in e] or [0], np.int32)
    return starts, lens, flat


def caps(lang: str, words: list[str], n_tokens: int) -> np.ndarray:
    """Most occurrences a symbol may have for each value: letters any; a null 3% of the text; a code word three times
    its expected count (word frequency x words in the text), at least 2. Without caps the search fills any text with
    common words, whose quadgrams beat the average (first trial: 0% of symbols right)."""
    m = model(lang)
    freq = dict(zip((str(x) for x in m["words"]), m["word_freq"]))
    n_words = n_tokens / 4.5
    return np.array([n_tokens] * 26 + [max(1, int(0.03 * n_tokens))] + [max(2, int(3 * freq.get(w, 0) * n_words)) for w in words], np.int64)


def mean_quad(lang: str) -> float:
    from ..langchoice import _baseline

    return _baseline(lang, 250)[0]


ROUNDS = 3  # stage 2 and a fresh letter search alternate: with every device at once one pass is not enough
NULL_SHARE = 0.10  # nulls together make up at most this share of the text
MARGIN = 1.5  # log10 per occurrence a null or code word must gain over the best letter: a symbol is a letter unless clearly not


def _ascend(ct, key, allowed, cap, fixed, starts, lens, flat, m, mu, w, passes: int = 3):
    count = np.bincount(ct, minlength=len(key))
    out = np.zeros(len(ct) * 12 + 16, np.int32)
    src = np.zeros(len(ct) * 12 + 16, np.int64)
    free = fixed < 0
    first = key.copy()

    def sc_():  # the score minus the margin for every symbol currently read as a null or code word
        return _score(out, src, _expand(ct, key, starts, lens, flat, out, src), m["table"], mu, m["letter"], w) - MARGIN * float(count[(key >= NULL) & free].sum())

    cur = sc_()
    for _ in range(passes):
        changed = False
        for s in np.argsort(count):  # rare symbols first: code words and nulls are usually rare
            if fixed[s] >= 0:
                continue
            old, best_v = key[s], key[s]
            for v in [first[s]] + [v for v in allowed if v >= NULL]:  # letters stay as stage 1 found them: no cascades
                if v == old or count[s] > cap[v]:
                    continue
                if v > NULL and ((key == v) & free).any():  # one symbol per code word, as in a nomenclator
                    continue
                if v == NULL and count[(key == NULL) & free].sum() + count[s] > NULL_SHARE * len(ct):
                    continue
                key[s] = v
                sc = sc_()
                if sc > cur + 1e-9:
                    cur, best_v, changed = sc, v, True
            key[s] = best_v
        if not changed:
            break
    return key, cur


def _mean_fit(ct, key, starts, lens, flat, m) -> float:
    """Mean quadgram log-probability of the decoded letters: compares readings of different lengths."""
    out = np.zeros(len(ct) * 12 + 16, np.int32)
    src = np.zeros(len(ct) * 12 + 16, np.int64)
    n = _expand(ct, key, starts, lens, flat, out, src)
    return float(quad_score(out[:n], m["table"])) / max(n - 3, 1)


def solve(toks: list[str], lang: str = "en", n_words: int = 40, nulls: bool = True, divider="auto", iters: int | None = None,
          restarts: int = 8, seed: int = 88, w: float = 2.0) -> dict:
    """Key and reading. divider: 'auto' (detect), None (no divider) or a symbol."""
    alpha = sorted(set(toks))
    idx = {s: i for i, s in enumerate(alpha)}
    ct = np.array([idx[t] for t in toks], np.int32)
    div = find_divider(toks, lang) if divider == "auto" else {"symbol": divider, "divider": divider is not None}
    words = code_words(lang, n_words)
    starts, lens, flat = _values(words)
    m = model(lang)
    iters = iters or int(min(3_000_000, max(400_000, 4000 * len(alpha))))
    t0 = 3.0 * (len(ct) / 400) ** 0.5
    cap = caps(lang, words, len(ct))
    mu = mean_quad(lang)
    no_words = np.minimum(cap, np.array([len(ct)] * 26 + [-1] * (1 + len(words)), np.int64))  # stage 1: letters only
    tries = [True, False] if div["divider"] and divider == "auto" else [bool(div["divider"])]
    best = None
    for as_divider in tries:  # stage 1: letters only, with the candidate divider read as a space or as a symbol
        fixed = np.full(len(alpha), -1, np.int32)
        if as_divider:
            fixed[idx[div["symbol"]]] = NULL
        key, _ = anneal_nom(ct, len(alpha), starts, lens, flat, 27, False, m["table"], mu, m["letter"], w, iters, restarts, seed, t0, fixed, no_words)
        fit = _mean_fit(ct, key, starts, lens, flat, m)
        if best is None or fit > best[0]:
            best = (fit, key, fixed, as_divider)
    _, key, fixed, as_divider = best
    div = {**div, "divider": as_divider, "tested_both": len(tries) == 2}
    sc = 0.0
    if nulls or n_words:  # stage 2: from the letter key, each symbol may become a null or code word; then re-solve letters
        allowed = [v for v in range(27 + len(words)) if v < 26 or (v == NULL and nulls) or (v > NULL and n_words)]
        for rnd_ in range(ROUNDS):
            key, sc = _ascend(ct, key, allowed, cap, fixed, starts, lens, flat, m, mu, w)
            special = (key >= NULL) & (fixed < 0)
            if rnd_ == ROUNDS - 1 or not special.any():
                break
            pinned = fixed.copy()
            pinned[special] = key[special]  # nulls and code words held while the letters are searched again
            key, _ = anneal_nom(ct, len(alpha), starts, lens, flat, 27 + len(words), False, m["table"], mu, m["letter"], w, iters, restarts, seed + rnd_ + 1, t0, pinned, no_words)
    names = [A[i] for i in range(26)] + ["(null)"] + [w.lower() for w in words]
    reading, spaced = [], []
    for t in toks:
        v = int(key[idx[t]])
        if div["divider"] and t == div["symbol"]:
            spaced.append(" ")
        elif v == NULL:
            continue
        else:
            reading.append(names[v])
            spaced.append(names[v] if v <= NULL else f"[{names[v]}]")
    return {"key": {a: names[int(key[i])] for i, a in enumerate(alpha)}, "values": [int(key[idx[t]]) for t in toks], "score": float(sc),
            "plaintext": "".join(r.upper() for r in reading), "spaced": "".join(spaced), "divider": div, "symbols": len(alpha), "code_words": words}
