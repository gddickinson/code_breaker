"""Round 51: the L. C. 15 (1879-1882) and L. R. G. (1879-1880) series.

1. Repeats: how much of each series is covered by repeated substrings of 5+ symbols, against shuffled copies (a sign
   of fixed formulas, words or code groups). 2. The L. C. 15 letter-digit ads of 1879-81 pooled and solved blind as one
   homophonic substitution in French (best of seven seeds by score), with a shuffled null and a planted control of the
   same length and symbol count, as for V. T. A. 3. The 1881-82 L. C. 15 ads, mostly letters: index of coincidence
   against French and against shuffled text (a transposition keeps French letter frequencies)."""
import json
import random
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

from ..attacks.classical import solve_symbols
from ..languages import ROOT, corpus_text, score
from ..validation import coverage
from .figaro_keys import OUT

RESULT = ROOT / "data/results/figaro_lc15.json"
DATA = json.loads((OUT / "lc15_lrg_transcription.json").read_text())


def repeat_share(texts: list[str], k: int = 5) -> float:
    """Share of positions inside a k-gram that occurs at least twice in the series (within or across ads)."""
    counts = Counter(t[i:i + k] for t in texts for i in range(len(t) - k + 1))
    covered = total = 0
    for t in texts:
        mark = [False] * len(t)
        for i in range(len(t) - k + 1):
            if counts[t[i:i + k]] >= 2:
                mark[i:i + k] = [True] * k
        covered += sum(mark)
        total += len(t)
    return covered / total if total else 0.0


def shuffled_texts(texts: list[str], rnd: random.Random) -> list[str]:
    flat = list("".join(texts))
    rnd.shuffle(flat)
    out, pos = [], 0
    for t in texts:
        out.append("".join(flat[pos:pos + len(t)]))
        pos += len(t)
    return out


def repeats(texts: list[str], trials: int = 1000, seed: int = 51) -> dict:
    real, rnd = repeat_share(texts), random.Random(seed)
    null = [repeat_share(shuffled_texts(texts, rnd)) for _ in range(trials)]
    return {"share": round(real, 3), "null_mean": round(sum(null) / trials, 3), "null_max": round(max(null), 3), "p": (sum(x >= real for x in null) + 1) / (trials + 1)}


def _solve(a):
    seq, seed = a
    r = solve_symbols(seq, "fr", homophonic=True, seed=seed, iters=6000000, restarts=4, w=1.0)
    return score(r["plaintext"], "fr"), r["plaintext"]


def blind(seq: list[str], ex) -> tuple[float, str]:
    return max(ex.map(_solve, [(seq, s) for s in range(7)]), key=lambda x: x[0])


def planted(n: int, symbols: int, seed: int = 7) -> tuple[list[str], str]:
    """French running text of the same length under a random homophonic key with the same number of symbols."""
    import re

    rnd = random.Random(seed)
    words = re.findall(r"[a-z]+", corpus_text("fr").lower())
    start = rnd.randrange(len(words) - 2000)
    plain = "".join(words[start:start + 600])[:n]
    letters = sorted(set(plain))
    pool = [f"s{i}" for i in range(max(symbols, len(letters)))]
    rnd.shuffle(pool)
    enc = {c: [pool[i]] for i, c in enumerate(letters)}
    for extra in pool[len(letters):]:
        enc[rnd.choice("eaisnrtu")].append(extra)
    return [rnd.choice(enc[c]) for c in plain], plain


def _mono(a):
    seq, seed = a
    r = solve_symbols(seq, "fr", seed=seed, iters=200000, restarts=8)
    return score(r["plaintext"], "fr"), r["plaintext"]


def blind_letters(ex) -> dict:
    """The 1881-82 ads, letters only, as one simple substitution; planted control of the same length."""
    import re

    letters = [c for t in DATA["lc15_letters"].values() for c in t if c.isalpha()]
    rnd = random.Random(1)
    words = re.findall(r"[a-z]+", corpus_text("fr").lower())
    st = rnd.randrange(len(words) - 500)
    plain = "".join(words[st:st + 80])[:len(letters)]
    k = list("abcdefghijklmnopqrstuvwxyz")
    rnd.shuffle(k)
    planted_seq = [dict(zip("abcdefghijklmnopqrstuvwxyz", k))[c] for c in plain]
    best = lambda seq: max(ex.map(_mono, [(seq, s) for s in range(7)]), key=lambda x: x[0])
    s, reading = best(letters)
    sh = letters[:]
    rnd.shuffle(sh)
    ps, pread = best(planted_seq)
    return {"letters": len(letters), "score": round(s, 3), "shuffled_score": round(best(sh)[0], 3), "coverage": coverage(reading, "fr"),
            "reading": reading.lower(), "planted_accuracy": round(sum(a == b for a, b in zip(pread.lower(), plain)) / len(plain), 3)}


def index_of_coincidence(t: str) -> float:
    t = [c for c in t if c.isalpha()]
    n, c = len(t), Counter(t)
    return sum(v * (v - 1) for v in c.values()) / (n * (n - 1)) if n > 1 else 0.0


def run() -> dict:
    out = {"id": "figaro_lc15"}
    series = {"lc15_digits": list(DATA["lc15_digits"].values()), "lc15_letters": list(DATA["lc15_letters"].values()), "lrg": list(DATA["lrg"].values())}
    out["repeats"] = {k: repeats(v) for k, v in series.items()}
    seq = list("".join(series["lc15_digits"]))
    with ProcessPoolExecutor(7) as ex:
        s, reading = blind(seq, ex)
        rnd = random.Random(3)
        sh = seq[:]
        rnd.shuffle(sh)
        ns, _ = blind(sh, ex)
        pseq, plain = planted(len(seq), len(set(seq)))
        ps, pread = blind(pseq, ex)
        out["blind_lc15_letters"] = blind_letters(ex)
    out["blind_lc15"] = {"letters": len(seq), "symbols": len(set(seq)), "score": round(s, 3), "shuffled_score": round(ns, 3), "coverage": coverage(reading, "fr"),
                         "reading": reading[:300].lower(), "planted_score": round(ps, 3), "planted_accuracy": round(sum(a == b for a, b in zip(pread.lower(), plain)) / len(plain), 3),
                         "reads": coverage(reading, "fr") >= 0.8 * coverage(pread, "fr") and s > ns + 0.15}
    letters = "".join(series["lc15_letters"])
    fr = corpus_text("fr").lower()
    out["ic_lc15_letters"] = {"ic": round(index_of_coincidence(letters), 4), "french": round(index_of_coincidence(fr[:20000]), 4), "random": round(1 / 26, 4)}
    return out


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, indent=1)[:2500])
