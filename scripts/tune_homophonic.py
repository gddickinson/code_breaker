"""Measure the homophonic solver across random keys for several schedules."""
import time
from concurrent.futures import ProcessPoolExecutor as P

from codebreaker import kernels as K
from codebreaker.attacks.classical import symbols_to_ints
from codebreaker.ciphers.base import DEMO_PLAIN as D
from codebreaker.ciphers.machines import hom_d, hom_e
from codebreaker.languages import model
from codebreaker.text import similarity, to_text


def run(a):
    m = model("en")
    seed, w, t0, it, rs = a
    ct = hom_e(D, seed=seed)
    truth = hom_d(ct, seed=seed)
    c, al = symbols_to_ints(ct.split())
    k, _ = K.anneal_homophonic(c, len(al), m["table"], m["letter"], w, it, rs, seed, t0)
    return similarity(truth, to_text(k[c]))


if __name__ == "__main__":
    run((1, 2.0, 2.0, 1000, 1))
    with P(9) as ex:
        for w, t0, it, rs in ((2, 2, 3000000, 6), (1, 1, 3000000, 6), (1, 2, 3000000, 6), (0.5, 1, 3000000, 6), (2, 3, 3000000, 6), (4, 3, 3000000, 6)):
            a = time.time()
            r = list(ex.map(run, [(s, float(w), float(t0), it, rs) for s in (1, 3, 7, 8, 11, 12, 13, 14, 15)]))
            print(w, t0, it, rs, [round(x, 2) for x in r], round(time.time() - a, 1), flush=True)
