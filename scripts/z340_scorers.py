"""Which scorer prefers the best achievable Z340 key over the solver's decoys?"""
import json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor as P

import numpy as np

import z340_5gram as Z
from codebreaker import kernels_n as N, lm
from codebreaker.languages import ROOT, score
from codebreaker.segment import segment, word_score
from codebreaker.text import similarity, to_ints
from codebreaker.validation import homophonic_like, sample_plaintext

DECOY_ITERS = 8000000


def achievable(seq, truth):
    votes = defaultdict(Counter)
    for s, p in zip(seq, truth):
        votes[s][p] += 1
    k = {s: c.most_common(1)[0][0] for s, c in votes.items()}
    return "".join(k[s] for s in seq)


def corrupted(text, rate, seed):
    r = np.random.default_rng(seed)
    t = list(text)
    for i in np.flatnonzero(r.random(len(t)) < rate):
        t[i] = chr(65 + r.integers(26))
    return "".join(t)


def evaluate(name, right, decoys):
    fns = {"quadgram": lambda x: score(x), "5-gram": lambda x: Z.objective(x, 2.0), "word model": lambda x: word_score(x)}
    out = {}
    for label, f in fns.items():
        a = f(right)
        out[label] = round(float(np.mean([a > f(d) for d in decoys])), 3)
    s = lm.scores([to_ints(right)] + [to_ints(d) for d in decoys])
    out["neural GRU"] = round(float(np.mean([s[0] > x for x in s[1:]])), 3)
    blended = lambda x, g: word_score(x) * 4 + g
    g = dict(zip([right] + decoys, s))
    b = blended(right, g[right])
    out["word + GRU"] = round(float(np.mean([b > blended(d, g[d]) for d in decoys])), 3)
    print(name, out, flush=True)
    return out


if __name__ == "__main__":
    N.table5()
    if not lm.PATH.exists():
        print("final loss", lm.train(), flush=True)
    with P(7) as ex:
        z_runs = list(ex.map(Z.run, [(Z.SEQ, s, 3.0, 2.0, DECOY_ITERS) for s in range(1, 29)]))
    decoys = sorted({t for _, t in z_runs if similarity(Z.TARGET, t) < 0.6})
    print("decoys", len(decoys), flush=True)
    good = achievable(Z.SEQ, Z.TARGET)
    print("key matches published text on", round(similarity(good, Z.TARGET), 3), flush=True)
    res = {"Z340 best key": evaluate("Z340 best key", good, decoys)}
    plain = sample_plaintext(len(Z.SEQ), "en", 7)
    enc = homophonic_like(list(range(len(set(Z.SEQ)))), plain, 2)
    res["clean English control"] = evaluate("clean control", plain, decoys)
    res["English with 10% errors"] = evaluate("10% errors", corrupted(plain, 0.10, 1), decoys)
    (ROOT / "data/results/z340_scorers.json").write_text(json.dumps({"decoys": len(decoys), "share_of_decoys_beaten": res, "best_key_match": round(similarity(good, Z.TARGET), 3), "decoy_sample": segment(decoys[0])[:200]}, indent=1))
