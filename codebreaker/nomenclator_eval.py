"""Controls for the archive-cipher solver (Round 88), saved to data/results/nomenclator_eval.json.

Planted ciphers in the style of early modern keys, from corpus passages: letters with homophones in proportion to
their frequency (about 50 two-digit symbols), 4 null symbols scattered at 6%, an optional word-divider symbol, and
code symbols for 10 of the language's commonest words (the solver is offered 40, so it must find which). Scores: the
share of symbol occurrences given their true value (letter, null or word), and of plaintext letters right. Each
device is tested alone and together, at 600 and 1,200 symbols, and with the solver's nulls and code words switched off
to show what they add. Null: the same ciphertext shuffled, for the score's z."""
import json
import random
import re

import numpy as np

from .attacks.nomenclator import NULL, code_words, solve
from .languages import ROOT, corpus_text, model
from .text import A, letters
from difflib import SequenceMatcher

RESULT = ROOT / "data/results/nomenclator_eval.json"


def make(lang: str, n_symbols: int, rnd: random.Random, nulls=True, divider=False, n_code=10) -> dict:
    words = [letters(w) for w in re.findall(r"[^\W\d_]+", corpus_text(lang)[-400000:])]
    words = [w for w in words if w]
    i = rnd.randrange(len(words) - 400)
    m = model(lang)
    pool = [f"{k:02d}" for k in range(10, 100)]
    rnd.shuffle(pool)
    homs = {}
    for li in np.argsort(-m["letter"]):  # 1 to 4 homophones by frequency
        homs[A[li]] = [pool.pop() for _ in range(1 + int(m["letter"][li] * 40))]
    null_syms = [pool.pop() for _ in range(4)] if nulls else []
    div = pool.pop() if divider else None
    coded = code_words(lang, 40)[:n_code]
    code = {w: pool.pop() for w in coded}
    toks, truth, plain = [], [], ""
    while len(toks) < n_symbols:
        w = words[i]
        i += 1
        if w in code:
            toks.append(code[w])
            truth.append(27 + code_words(lang, 40).index(w))
            plain += w
        else:
            for c in w:
                toks.append(rnd.choice(homs[c]))
                truth.append(A.index(c))
                plain += c
                if null_syms and rnd.random() < 0.06:
                    toks.append(rnd.choice(null_syms))
                    truth.append(NULL)
        if div:
            toks.append(div)
            truth.append(NULL)
    return {"tokens": toks, "truth": truth, "plain": plain, "divider": div}


def score(r: dict, c: dict) -> dict:
    v = np.array(r["values"])
    t = np.array(c["truth"])
    return {"symbols_right": round(float((v == t).mean()), 3), "letters_right": round(SequenceMatcher(None, r["plaintext"], c["plain"], autojunk=False).ratio(), 3),
            "divider_found": r["divider"]["divider"] and r["divider"]["symbol"] == c["divider"] if c["divider"] else not r["divider"]["divider"]}


def run(lang: str = "en", trials: int = 3, seed: int = 88) -> dict:
    rnd = random.Random(seed)
    cases = {"homophonic only": dict(nulls=False, divider=False, n_code=0), "with nulls": dict(nulls=True, divider=False, n_code=0),
             "with divider": dict(nulls=False, divider=True, n_code=0), "with code words": dict(nulls=False, divider=False, n_code=10),
             "all four": dict(nulls=True, divider=True, n_code=10)}
    out = {}
    for name, kw in cases.items():
        for n in (600, 1200):
            rows = [score(solve(c["tokens"], lang), c) for c in (make(lang, n, rnd, **kw) for _ in range(trials))]
            out[f"{name}, {n}"] = {k: (round(float(np.mean([r[k] for r in rows])), 3) if k != "divider_found" else sum(r[k] for r in rows)) for k in rows[0]}
    plain_solver = [score(solve(c["tokens"], lang, n_words=0, nulls=False), c) for c in (make(lang, 600, rnd, nulls=True, divider=True, n_code=10) for _ in range(trials))]
    out["all four, 600, solver without nulls or code words"] = {k: round(float(np.mean([r[k] for r in plain_solver])), 3) for k in ("symbols_right", "letters_right")}
    c = make(lang, 600, rnd, nulls=True, divider=True, n_code=10)
    real = solve(c["tokens"], lang)["score"]
    sh = []
    for k in range(6):
        t = c["tokens"][:]
        random.Random(k).shuffle(t)
        sh.append(solve(t, lang, divider=None)["score"])
    out["null: shuffled symbols"] = {"real_score": round(real, 1), "shuffled_mean": round(float(np.mean(sh)), 1), "z": round((real - np.mean(sh)) / (np.std(sh) + 1e-9), 1)}
    return {"id": "nomenclator_eval", "lang": lang, "trials": trials, "results": out}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r["results"], indent=1))
