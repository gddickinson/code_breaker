"""A long calibration search on the Z340 positions whose reading order has been verified."""
import json
from concurrent.futures import ProcessPoolExecutor as P

from codebreaker import kernels as K
from codebreaker.attacks.classical import symbols_to_ints
from codebreaker.languages import ROOT, model
from codebreaker.mysteries.zodiac import load, untranspose
from codebreaker.segment import segment
from codebreaker.text import letters, similarity, to_text

z, truth = load("z340.txt"), letters(load("z340_solved.txt"))
keep = list(range(153 + 99)) + list(range(306, 340))
seq = [untranspose(z)[i] for i in keep]
target = "".join(truth[i] for i in keep)


def run(seed):
    m = model("en")
    c, al = symbols_to_ints(seq)
    t0 = 3.0 * (len(c) / 400) ** 0.5
    k, s = K.anneal_homophonic(c, len(al), m["table"], m["letter"], 2.0, 40000000, 3, seed, t0)
    return float(s), to_text(k[c])


if __name__ == "__main__":
    with P(6) as ex:
        res = sorted(ex.map(run, range(1, 13)), reverse=True)
    acc = [round(similarity(target, t), 3) for _, t in res]
    print("accuracy by rank", acc, flush=True)
    best = res[0][1]
    print(segment(best)[:260], flush=True)
    (ROOT / "data/results/z340_deep.json").write_text(json.dumps({"positions": len(keep), "accuracy_by_rank": acc, "best_reading": segment(best), "scores": [round(s, 1) for s, _ in res]}, indent=1))
