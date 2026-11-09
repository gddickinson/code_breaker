"""Word-model annealing: planted noisy control first, then Z340's verified positions."""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor as P

import numpy as np

import z340_5gram as Z
from codebreaker import kernels_n as N, kernels_word as W
from codebreaker.attacks.classical import symbols_to_ints
from codebreaker.languages import ROOT, model
from codebreaker.segment import segment
from codebreaker.text import similarity, to_text
from codebreaker.validation import homophonic_like, sample_plaintext

ITERS, UNK = 700000, -6.5


def job(a):
    seq, seed, t0, w = a
    m = model("en")
    c, al = symbols_to_ints(seq)
    child, value = W.build_trie()
    k0, _ = N.anneal5(c, len(al), np.asarray(N.table5()), m["letter"], 2.0, 4000000, 1, seed, 3.0)
    k, s = W.anneal_word(c, len(al), child, value, UNK, ITERS, seed, t0, k0, m["letter"], w)
    return float(s), to_text(k[c]), to_text(k0[c])


def noisy(seq, rate, seed):
    plain = sample_plaintext(len(seq), "en", 12)
    enc = homophonic_like(list(range(len(set(seq)))), plain, 5)
    r = np.random.default_rng(seed)
    syms = sorted(set(enc))
    enc = [syms[int(r.integers(len(syms)))] if r.random() < rate else s for s in enc]
    return plain, enc


if __name__ == "__main__":
    N.table5()
    t = time.time(); W.anneal_word(*(lambda c, al: (c, len(al), *W.build_trie(), UNK, 3000, 1, 4.0, np.zeros(len(al), dtype=np.int32), model("en")["letter"], 0.5))(*symbols_to_ints(Z.SEQ))); print("3000 iters", round(time.time() - t, 2), "s", flush=True)
    plain, enc = noisy(Z.SEQ, 0.10, 3)
    out = {}
    with P(7) as ex:
        for t0, w in ((0.4, 0.5), (1.2, 0.5)):
            c_res = max(ex.map(job, [(enc, s, t0, w) for s in range(1, 8)]))
            print("control t0", t0, "after", round(similarity(plain, c_res[1]), 3), "5-gram start", round(similarity(plain, c_res[2]), 3), flush=True)
            r_res = sorted(ex.map(job, [(Z.SEQ, s, t0, w) for s in range(20, 27)]), reverse=True)
            acc = [round(similarity(Z.TARGET, x[1]), 3) for x in r_res]
            print("z340 t0", t0, "acc by rank", acc, "starts", [round(similarity(Z.TARGET, x[2]), 3) for x in r_res], flush=True)
            out[str(t0)] = {"control_after": similarity(plain, c_res[1]), "control_start": similarity(plain, c_res[2]), "z340_by_rank": acc, "z340_reading": segment(r_res[0][1])[:320]}
            (ROOT / "data/results/z340_word.json").write_text(json.dumps(out, indent=1))
