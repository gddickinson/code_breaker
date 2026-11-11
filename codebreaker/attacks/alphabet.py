"""Shift, Vigenere and substitution ciphers in any alphabet (Round 86): Cyrillic, Greek, Hebrew, Arabic script.

Encryption works on a language's own alphabet (alphabets.py). Breaking: Caesar by trying every shift; Vigenere by the
period whose columns have the most language-like IC, each column's shift fitted to letter frequencies and then
improved by quadgram score; simple substitution by annealing (kernels_a.py). Each result is judged by the three gates
(validation.verdict): a planted passage of the same length is recovered (positive control), the score beats the same
attack on shuffled ciphertext (null), and the output reads as words of the language (coverage)."""
import numpy as np

from .. import alphabets as AB
from ..kernels_a import anneal_sub_a, quad_score_a
from ..validation import verdict

KINDS = ("caesar", "vigenere", "substitution")


def encrypt(text: str, lang: str, kind: str, key) -> str:
    """kind caesar: key = shift; vigenere: key = list of shifts; substitution: key = permutation (plain i -> key[i])."""
    a = AB.to_ints(text, lang)
    A = len(AB.model(lang)["alpha"])
    if kind == "caesar":
        c = (a + key) % A
    elif kind == "vigenere":
        k = np.array(key)
        c = (a + k[np.arange(len(a)) % len(k)]) % A
    else:
        c = np.asarray(key)[a]
    return AB.to_text(c, lang)


def _per_letter(a, lang) -> float:
    m = AB.model(lang)
    return float(quad_score_a(a.astype(np.int32), m["table"], len(m["alpha"]))) / max(len(a) - 3, 1)


def _ic(a, A) -> float:
    c = np.bincount(a, minlength=A)
    n = c.sum()
    return float((c * (c - 1)).sum() / (n * (n - 1))) if n > 1 else 0.0


def caesar(a: np.ndarray, lang: str) -> dict:
    A = len(AB.model(lang)["alpha"])
    s = max(range(A), key=lambda k: _per_letter((a - k) % A, lang))
    return {"key": s, "plain": (a - s) % A}


def _column_shift(col, q, A) -> int:
    f = np.bincount(col, minlength=A) / max(len(col), 1)
    return int(np.argmax([np.dot(f, np.log(np.roll(q, k) + 1e-6)) for k in range(A)]))


def vigenere(a: np.ndarray, lang: str, max_p: int = 12) -> dict:
    m = AB.model(lang)
    A, q = len(m["alpha"]), m["letter"]
    ics = {p: np.mean([_ic(a[i::p], A) for i in range(p)]) for p in range(1, min(max_p, len(a) // 6) + 1)}
    top = max(ics.values())
    p = min(k for k, v in ics.items() if v >= 0.9 * top)
    key = np.array([_column_shift(a[i::p], q, A) for i in range(p)])
    idx = np.arange(len(a)) % p
    for _ in range(2):  # improve each column's shift by quadgram score, the others held
        for i in range(p):
            def sc(k):
                key[i] = k
                return _per_letter((a - key[idx]) % A, lang)
            key[i] = max(range(A), key=sc)
    return {"key": key.tolist(), "plain": (a - key[idx]) % A}


def substitution(a: np.ndarray, lang: str, iters: int = 40000, restarts: int = 20, seed: int = 86) -> dict:
    m = AB.model(lang)
    A = len(m["alpha"])
    key, _ = anneal_sub_a(a.astype(np.int32), A, m["table"], iters, restarts, seed, 3.0)
    return {"key": key.tolist(), "plain": key[a]}


ATTACK = {"caesar": caesar, "vigenere": vigenere, "substitution": substitution}


def solve(a: np.ndarray, lang: str, kind: str) -> dict:
    r = ATTACK[kind](a, lang)
    return {**r, "score": _per_letter(r["plain"], lang), "text": AB.to_text(r["plain"], lang)}


def _random_key(kind, A, rnd):
    if kind == "caesar":
        return int(rnd.integers(1, A))
    if kind == "vigenere":
        return rnd.integers(0, A, int(rnd.integers(3, 8))).tolist()
    return rnd.permutation(A).tolist()


def positive_control(n: int, lang: str, kind: str, trials: int = 3, seed: int = 86) -> dict:
    """Held-out corpus passages of n letters, encrypted with random keys and solved: share of letters right, and what a real
    solve scores and covers."""
    m = AB.model(lang)
    A = len(m["alpha"])
    full = AB.to_ints(AB.held_out(lang), lang)  # text the model was not built on
    rnd = np.random.default_rng(seed)
    acc, scores, cov = [], [], []
    for _ in range(trials):
        i = int(rnd.integers(0, len(full) - n))
        p = full[i:i + n]
        c = AB.to_ints(encrypt(AB.to_text(p, lang), lang, kind, _random_key(kind, A, rnd)), lang)
        r = solve(c, lang, kind)
        acc.append(float((r["plain"] == p).mean()))
        scores.append(r["score"])
        cov.append(AB.coverage(AB.to_text(p, lang), lang))
    return {"mean": float(np.mean(acc)), "solved_score": float(np.mean(scores)), "true_coverage": float(np.mean(cov))}


def null_z(a: np.ndarray, lang: str, kind: str, score: float, n_null: int = 8, seed: int = 86) -> float:
    rnd = np.random.default_rng(seed)
    null = [solve(rnd.permutation(a), lang, kind)["score"] for _ in range(n_null)]
    return (score - float(np.mean(null))) / (float(np.std(null)) + 1e-6)


def crack(text: str, langs=None, kinds=KINDS) -> dict:
    """Every attack in every language of the text's script; the best by score, then the three gates on it."""
    script, share = AB.detect_script(text)
    if script is None:
        return {"script": None, "note": "Not mostly Cyrillic, Greek, Hebrew or Arabic-script letters."}
    langs = langs or [c for c in AB.available() if AB.script_of(c) == script]
    if not langs:
        return {"script": script, "note": f"No {script} corpus on disk: run scripts/fetch_corpora.py and fetch_wiki_corpora.py."}
    tried = []
    for lang in langs:
        a = AB.to_ints(text, lang)
        if len(a) < 20:
            continue
        base = AB.coverage(AB.to_text(a, lang), lang)
        tried.append({"lang": lang, "kind": "none (already plain)", "key": "", "text": AB.to_text(a, lang), "score": _per_letter(a, lang), "coverage": base})
        for kind in kinds:
            r = solve(a, lang, kind)
            tried.append({"lang": lang, "kind": kind, "key": r["key"], "text": r["text"], "score": r["score"], "coverage": AB.coverage(r["text"], lang)})
    if not tried:
        return {"script": script, "note": "Fewer than 20 letters in the script."}
    best = max(tried, key=lambda r: (r["score"], -KINDS.index(r["kind"]) if r["kind"] in KINDS else 1))
    out = {"script": script, "share": round(share, 2), "languages": langs, "attempts": [{k: v for k, v in r.items() if k != "key"} for r in tried], "best": best}
    if best["kind"] not in KINDS:
        out["verdict"] = "Already plain text in " + AB.LANGS[best["lang"]][0] + f" (word coverage {best['coverage']:.0%})."
        return out
    a = AB.to_ints(text, best["lang"])
    pc = positive_control(len(a), best["lang"], best["kind"])
    z = null_z(a, best["lang"], best["kind"], best["score"])
    tests = len(langs) * len(kinds)
    out.update(positive_control=pc, z=round(z, 1), tests=tests,
               verdict=verdict(pc, z, tests, best["text"], best["score"], best["lang"], cov_fn=AB.coverage))
    return out
