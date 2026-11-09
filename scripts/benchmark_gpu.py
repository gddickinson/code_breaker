"""Compare GPU and compiled CPU routes on this machine; save results for accel.best_route."""
import json
import time

import numpy as np

from codebreaker import accel, kernels as K
from codebreaker.ciphers.base import DEMO_PLAIN
from codebreaker.ciphers.machines import REFLECTOR_B, _setup, enigma
from codebreaker.languages import corpus_text, model
from codebreaker.mysteries.beale import ciphers, initials
from codebreaker.text import similarity, to_ints, to_text
from codebreaker.ciphers.machines import hom_d, hom_e
from codebreaker.attacks.classical import symbols_to_ints


def timed(fn):
    t = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t


def main():
    print("device", accel.device(), flush=True)
    m, res = model("en"), {}
    nums = np.array(ciphers()["B3"], dtype=np.int64)
    ini = to_ints(initials("key_kjv.txt"))
    N = 200000
    K.book_offset_scan(nums[:20], ini, m["table"], 10)
    cpu, tc = timed(lambda: K.book_offset_scan(nums, ini, m["table"], N))
    gpu, tg = timed(lambda: accel.book_scan(nums, ini, m["table"], N))
    res["book_scan"] = {"cpu_per_s": N / tc, "gpu_per_s": N / tg, "agree_best_offset": int(np.argmax(cpu)) == int(np.argmax(gpu)), "unit": "offsets"}
    print(res["book_scan"], flush=True)

    plain = DEMO_PLAIN[:220]
    wires, notch = _setup("I II III")
    ct = to_ints(enigma(plain, "I II III", "AAA", "QHZ", ""))
    K.enigma_scan(ct[:6], wires, notch, REFLECTOR_B)
    cpu, tc = timed(lambda: K.enigma_scan(ct, wires, notch, REFLECTOR_B))
    gpu, tg = timed(lambda: accel.enigma_ic_scan(ct, wires, notch, REFLECTOR_B))
    res["enigma_scan"] = {"cpu_per_s": 17576 / tc, "gpu_per_s": 17576 / tg, "agree_position": to_text(cpu[0]) == to_text(gpu[0]), "found": to_text(gpu[0]), "unit": "start positions"}
    print(res["enigma_scan"], flush=True)

    c = hom_e(DEMO_PLAIN, seed=3)
    truth = hom_d(c, seed=3)
    x, al = symbols_to_ints(c.split())
    K.anneal_homophonic(x, len(al), m["table"], m["letter"], 2.0, 1000, 1, 1, 3.0)
    (kc, _), tc = timed(lambda: K.anneal_homophonic(x, len(al), m["table"], m["letter"], 2.0, 3000000, 4, 1, 3.0))
    (kg, _, props), tg = timed(lambda: accel.population_anneal(x, len(al), m["table"], m["letter"], chains=4096, steps=8000))
    res["homophonic_anneal"] = {"cpu_per_s": 12000000 / tc, "gpu_per_s": props / tg, "cpu_accuracy": similarity(truth, to_text(kc[x])), "gpu_accuracy": similarity(truth, to_text(kg[x])), "unit": "proposals, one CPU core"}
    print(res["homophonic_anneal"], flush=True)
    accel.BENCH.write_text(json.dumps(res, indent=1, default=lambda o: o.item()))


if __name__ == "__main__":
    main()
