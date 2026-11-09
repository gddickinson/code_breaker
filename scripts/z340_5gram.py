"""Does a 5-gram language model read Z340's verified positions? Includes a planted control."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor as P

import numpy as np

from codebreaker import kernels_n as N
from codebreaker.attacks.classical import symbols_to_ints
from codebreaker.languages import ROOT, model
from codebreaker.mysteries.zodiac import load, untranspose
from codebreaker.segment import segment
from codebreaker.text import letters, similarity, to_ints, to_text
from codebreaker.validation import homophonic_like, sample_plaintext

z, truth = load("z340.txt"), letters(load("z340_solved.txt"))
keep = list(range(153 + 99)) + list(range(306, 340))
SEQ = [untranspose(z)[i] for i in keep]
TARGET = "".join(truth[i] for i in keep)


def run(a):
    seq, seed, t0, w, it = a
    tab = np.asarray(N.table5())
    m = model("en")
    c, al = symbols_to_ints(seq)
    k, s = N.anneal5(c, len(al), tab, m["letter"], w, it, 2, seed, t0)
    return float(s), to_text(k[c])


def objective(text, w):
    tab, m, p = np.asarray(N.table5()), model("en"), to_ints(text).astype(np.int64)
    c, n = np.bincount(p, minlength=26), len(p)
    return float(N.score5(p, tab)) - w * float((((c - n * m["letter"]) ** 2) / (n * m["letter"])).sum())


if __name__ == "__main__":
    N.table5()
    plant_text = sample_plaintext(len(SEQ), "en", 41)
    plant = homophonic_like(list(range(len(set(SEQ)))), plant_text, 3)
    out = {}
    with P(6) as ex:
        for t0, w in ((3, 2), (6, 2), (10, 2), (6, 0.5)):
            pc = sorted(ex.map(run, [(plant, s, float(t0), float(w), 8000000) for s in range(1, 5)]), reverse=True)
            real = sorted(ex.map(run, [(SEQ, s, float(t0), float(w), 8000000) for s in range(1, 7)]), reverse=True)
            row = {"control_accuracy": round(similarity(plant_text, pc[0][1]), 3), "accuracy_top": round(similarity(TARGET, real[0][1]), 3), "accuracy_all": [round(similarity(TARGET, t), 3) for _, t in real], "best_objective": round(real[0][0], 1), "truth_objective": round(objective(TARGET, float(w)), 1), "reading": segment(real[0][1])[:260]}
            out[f"t0={t0},w={w}"] = row
            print(t0, w, {k: v for k, v in row.items() if k != "reading"}, flush=True)
    (ROOT / "data/results/z340_5gram.json").write_text(json.dumps(out, indent=1))
    b = max(out.values(), key=lambda r: r["accuracy_top"])
    print(b["reading"])
