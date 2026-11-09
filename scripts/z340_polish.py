"""Steepest-ascent key polishing guided by the neural scorer, in batches on the GPU."""
import json
import time
from concurrent.futures import ProcessPoolExecutor as P

import numpy as np

import z340_5gram as Z
from codebreaker import kernels_n as N, lm
from codebreaker.attacks.classical import symbols_to_ints
from codebreaker.languages import ROOT, model
from codebreaker.segment import segment
from codebreaker.text import similarity, to_text

BUDGET = 500


def start(seed):
    m = model("en")
    c, al = symbols_to_ints(Z.SEQ)
    k, _ = N.anneal5(c, len(al), np.asarray(N.table5()), m["letter"], 2.0, 8000000, 2, seed, 3.0)
    return k


def score_keys(keys, c):
    out = []
    for i in range(0, len(keys), 300):
        out += lm.scores([k[c] for k in keys[i:i + 300]])
    return out


def polish(key, c, deadline):
    cur = score_keys([key], c)[0]
    while time.time() < deadline:
        moves = []
        for s in range(len(key)):
            for L in range(26):
                if L != key[s]:
                    k = key.copy()
                    k[s] = L
                    moves.append(k)
        sc = score_keys(moves, c)
        i = int(np.argmax(sc))
        if sc[i] <= cur + 1e-6:
            break
        key, cur = moves[i], sc[i]
    return key, cur


if __name__ == "__main__":
    N.table5()
    t0 = time.time()
    c, al = symbols_to_ints(Z.SEQ)
    with P(7) as ex:
        keys = list(ex.map(start, range(300, 321)))
    s = lm.scores([k[c] for k in keys])
    order = np.argsort(s)[::-1]
    rows = []
    per = (BUDGET - (time.time() - t0)) / 8
    for j in order[:8]:
        k0 = keys[j]
        k, v = polish(k0, c, time.time() + per)
        rows.append({"before": round(similarity(Z.TARGET, to_text(k0[c])), 3), "after": round(similarity(Z.TARGET, to_text(k[c])), 3), "score": round(v, 4), "reading": segment(to_text(k[c]))[:300]})
        print({x: rows[-1][x] for x in ("before", "after", "score")}, flush=True)
        (ROOT / "data/results/z340_polish.json").write_text(json.dumps(rows, indent=1))
    best = max(rows, key=lambda r: r["score"])
    print("top neural score reading, accuracy", best["after"], best["reading"][:240], flush=True)
