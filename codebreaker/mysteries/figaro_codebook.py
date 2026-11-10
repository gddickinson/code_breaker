"""Round 52: codebook-style tests on L. R. G. and L. C. 15, each with its own control.

1. Shared groups: do the four unsigned numeric ads of March-April 1879 share 3- and 4-symbol groups with L. R. G.
   (Aug 1879 on) more than shuffled copies of them do? A shared code would show as shared groups.
2. L. R. G. as a homophonic substitution of French (each digit and letter a symbol), solved blind, with a planted
   control of the same length and symbol count: closes or opens the simplest reading.
3. L. C. 15 of 1881-82 ad by ad as simple substitutions, with planted controls of each length: how much ads of
   25-36 letters can tell."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor

from ..attacks.classical import solve_symbols
from ..languages import ROOT, corpus_text, score
from ..validation import coverage
from .figaro_lc15 import DATA, planted

RESULT = ROOT / "data/results/figaro_codebook.json"


def clean(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.lower())


def grams(texts: list[str], k: int) -> set:
    return {t[i:i + k] for t in texts for i in range(len(t) - k + 1)}


def shared(a: list[str], b: list[str], k: int) -> int:
    return len(grams(a, k) & grams(b, k))


def shared_groups(trials: int = 2000, seed: int = 52) -> dict:
    lrg = [clean(t) for t in DATA["lrg"].values()]
    num = [clean(t) for t in DATA["numeric_1879"].values()]
    out, rnd = {}, random.Random(seed)
    for k in (3, 4):
        real = shared(num, lrg, k)
        null = []
        for _ in range(trials):
            flat = list("".join(num))
            rnd.shuffle(flat)
            pos, sh = 0, []
            for t in num:
                sh.append("".join(flat[pos:pos + len(t)]))
                pos += len(t)
            null.append(shared(sh, lrg, k))
        out[f"k{k}"] = {"shared": real, "null_mean": round(sum(null) / trials, 2), "null_max": max(null), "p": (sum(x >= real for x in null) + 1) / (trials + 1),
                        "groups": sorted(grams(num, k) & grams(lrg, k))[:30]}
    return out


def _homo(a):
    seq, seed = a
    r = solve_symbols(seq, "fr", homophonic=True, seed=seed, iters=6000000, restarts=4, w=1.0)
    return score(r["plaintext"], "fr"), r["plaintext"], {k: v.lower() for k, v in r["key"].items()}


def _mono(a):
    seq, seed = a
    r = solve_symbols(seq, "fr", seed=seed, iters=100000, restarts=8)
    return score(r["plaintext"], "fr"), r["plaintext"]


def lrg_blind(ex, shuffles: int = 5) -> dict:
    """Best of seven seeds by score; agreement among seeds; shuffled copies solved the same way; planted control."""
    from ..segment import segment

    ads = {k: clean(t) for k, t in DATA["lrg"].items()}
    seq = list("".join(ads.values()))
    runs = sorted(ex.map(_homo, [(seq, i) for i in range(7)]), key=lambda x: -x[0])
    s, reading, key = runs[0]
    converged = sum(abs(r[0] - s) < 1e-6 and r[2] == key for r in runs)
    rnd, null = random.Random(4), []
    for _ in range(shuffles):
        sh = seq[:]
        rnd.shuffle(sh)
        b = max(ex.map(_homo, [(sh, i) for i in range(7)]), key=lambda x: x[0])
        null.append({"score": round(b[0], 3), "coverage": coverage(b[1], "fr")})
    pseq, plain = planted(len(seq), len(set(seq)))
    ps, pread, _ = max(ex.map(_homo, [(pseq, i) for i in range(7)]), key=lambda x: x[0])
    cov, pcov = coverage(reading, "fr"), coverage(pread, "fr")
    gates = {"control": sum(a == b for a, b in zip(pread.lower(), plain)) / len(plain) >= 0.7,
             "null": s > max(n["score"] for n in null) + 0.15 and cov > max(n["coverage"] for n in null),
             "reads": cov >= 0.8 * pcov}
    per_ad = {i: segment("".join(key[c] for c in t), "fr") for i, t in ads.items()}
    return {"letters": len(seq), "symbols": len(set(seq)), "score": round(s, 3), "seeds_converged": converged, "key": key, "coverage": cov,
            "null": null, "planted_accuracy": round(sum(a == b for a, b in zip(pread.lower(), plain)) / len(plain), 3), "planted_coverage": pcov,
            "gates": {**gates, "passed": all(gates.values())}, "per_ad": per_ad}


def series_blind(ex, words: dict, shuffles: int = 3, seed: int = 54) -> dict:
    """A series with printed word breaks ({ad: [word symbol lists]}), solved blind as one homophonic substitution of
    French; best of 7 seeds, seed agreement, shuffled copies solved the same way, planted control and word bar."""
    seq = [c for ws in words.values() for w in ws for c in w]
    runs = sorted(ex.map(_homo, [(seq, i) for i in range(7)]), key=lambda x: -x[0])
    s, reading, key = runs[0]
    rnd, null = random.Random(seed), []
    for _ in range(shuffles):
        sh = seq[:]
        rnd.shuffle(sh)
        b = max(ex.map(_homo, [(sh, i) for i in range(7)]), key=lambda x: x[0])
        null.append({"score": round(b[0], 3), "coverage": coverage(b[1], "fr")})
    pseq, plain = planted(len(seq), len(set(seq)))
    _, pread, _ = max(ex.map(_homo, [(pseq, i) for i in range(7)]), key=lambda x: x[0])
    acc, cov, pcov = sum(a == b for a, b in zip(pread.lower(), plain)) / len(plain), coverage(reading, "fr"), coverage(pread, "fr")
    gates = {"control": acc >= 0.7, "null": s > max(n["score"] for n in null) + 0.15 and cov > max(n["coverage"] for n in null), "reads": cov >= 0.8 * pcov}
    return {"symbols": len(seq), "distinct": len(set(seq)), "score": round(s, 3), "seeds_converged": sum(abs(r[0] - s) < 1e-6 and r[2] == key for r in runs),
            "coverage": cov, "null": null, "planted_accuracy": round(acc, 3), "planted_coverage": pcov, "gates": {**gates, "passed": all(gates.values())},
            "key": key, "readings": {k: " ".join("".join(key[c] for c in w) for w in ws) for k, ws in words.items()}}


def jane_blind(ex) -> dict:
    """Round 54: the two 'Jane' ads of Sep 1886, numbers 1-74 as symbols, word breaks as printed."""
    texts = {k: v.replace(" - 1925", "") for k, v in DATA["jane"].items()}
    words = {k: [re.findall(r"\d+", w) for w in re.split(r"\s*-\s*|\s+", t) if re.findall(r"\d+", w)] for k, t in texts.items()}
    out = series_blind(ex, words, seed=54)
    out["numbers"] = out["symbols"]
    return out


def b_blind(ex) -> dict:
    """Round 55: the 'B' ads of 1882-1886 (signed B ... A.), letters and digits as symbols, word breaks as printed."""
    return series_blind(ex, {k: [list(w) for w in t.split()] for k, t in DATA["b"].items()}, seed=55)


def per_ad(ex, controls: int = 6) -> list[dict]:
    words = re.findall(r"[a-z]+", corpus_text("fr").lower())
    rnd, rows = random.Random(52), []
    for image, t in DATA["lc15_letters"].items():
        seq = [c for c in t if c.isalpha()]
        s, reading = max(ex.map(_mono, [(seq, i) for i in range(7)]), key=lambda x: x[0])
        acc = []
        for _ in range(controls):
            st = rnd.randrange(len(words) - 100)
            plain = "".join(words[st:st + 30])[:len(seq)]
            k = list("abcdefghijklmnopqrstuvwxyz")
            rnd.shuffle(k)
            m = dict(zip("abcdefghijklmnopqrstuvwxyz", k))
            ps, pread = max(ex.map(_mono, [([m[c] for c in plain], i) for i in range(7)]), key=lambda x: x[0])
            acc.append(sum(a == b for a, b in zip(pread.lower(), plain)) / len(plain))
        rows.append({"image": image, "letters": len(seq), "score": round(s, 3), "coverage": coverage(reading, "fr"), "reading": reading.lower(),
                     "control_mean_accuracy": round(sum(acc) / len(acc), 3)})
    return rows


def run() -> dict:
    out = {"id": "figaro_codebook", "shared_1879_lrg": shared_groups()}
    with ProcessPoolExecutor(7) as ex:
        out["lrg_blind"] = lrg_blind(ex)
        out["lc15_per_ad"] = per_ad(ex)
        out["jane_blind"] = jane_blind(ex)
        out["b_blind"] = b_blind(ex)
    return out


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res["shared_1879_lrg"], indent=1))
    print({k: v for k, v in res["lrg_blind"].items() if k != "reading"})
    print({k: v for k, v in res["jane_blind"].items() if k not in ("key", "readings")})
    print(res["jane_blind"]["readings"])
    print({k: v for k, v in res["b_blind"].items() if k not in ("key", "readings")})
    print(res["b_blind"]["readings"])
    for r in res["lc15_per_ad"]:
        print(r["image"][:13], r["letters"], r["coverage"], r["control_mean_accuracy"], r["reading"])
