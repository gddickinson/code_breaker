from concurrent.futures import ProcessPoolExecutor as P
import random
from codebreaker.mysteries.combined import A, bigram_solve, sample_plaintext, similarity

def job(a):
    seed, n, w, tf = a
    plain = sample_plaintext(n, "en", seed); plain = plain[: len(plain) // 2 * 2]
    r = random.Random(seed); pairs = sorted({plain[i:i + 2] for i in range(0, len(plain) - 1, 2)})
    table = dict(zip(pairs, r.sample([x + y for x in A for y in A], len(pairs))))
    ct = "".join(table[plain[i:i + 2]] for i in range(0, len(plain) - 1, 2))
    return round(similarity(plain, bigram_solve(ct, seed, iters=4000000, restarts=3, w=w, tf=tf)[0]), 2)

if __name__ == "__main__":
    with P(8) as ex:
        for w, tf in ((2, 2), (6, 2), (12, 3), (20, 3), (6, 1), (12, 1.5)):
            print(w, tf, list(ex.map(job, [(s, 1000, float(w), float(tf)) for s in (2, 3, 4)])), list(ex.map(job, [(s, 1600, float(w), float(tf)) for s in (5, 6)])), flush=True)
