"""Does scaling the starting temperature with text length fix long low-symbol messages?"""
from concurrent.futures import ProcessPoolExecutor as P

from codebreaker.attacks.classical import solve_symbols
from codebreaker.text import similarity
from codebreaker.validation import homophonic_like, sample_plaintext


def run(a):
    n, k, scale, s = a
    plain = sample_plaintext(n, "en", 77 + s + n)
    enc = homophonic_like(list(range(k)), plain, s)
    t0 = 3.0 * (n / 400) ** scale
    return similarity(plain, solve_symbols(enc, "en", True, restarts=4, seed=s, t0=t0)["plaintext"])


if __name__ == "__main__":
    with P(6) as ex:
        for n, k in ((800, 26), (1500, 26), (1500, 54), (340, 63), (408, 54), (800, 200)):
            print(n, k, {sc: round(sum(ex.map(run, [(n, k, sc, s) for s in range(4)])) / 4, 2) for sc in (0, 0.5, 1)}, flush=True)
