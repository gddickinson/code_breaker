"""Round 56: refine a blind homophonic key with the printed word breaks, under a matched null.

Refinement: starting from the blind key, give each symbol in turn the letter that puts the most letters into whole
French words (word breaks as printed), until nothing improves. Round 38 showed that such a refinement inflates on
shuffled symbols, so the null runs the identical pipeline (blind solve, then this refinement) on shuffled copies that
keep the word lengths. The refined real text must beat every refined shuffle."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

from ..languages import ROOT, model
from .figaro_codebook import _homo
from .figaro_lc15 import DATA

RESULT = ROOT / "data/results/figaro_wordrefine.json"
LETTERS = "abcdefghijlmnopqrstuvxyz"


@lru_cache(maxsize=1)
def vocab() -> frozenset:
    return frozenset(str(w).lower() for w in model("fr")["words"][:20000] if len(w) >= 2) | {"a", "y"}


def word_share(words: list[list[str]], key: dict) -> float:
    v, n = vocab(), sum(map(len, words))
    return sum(len(w) for w in words if "".join(key.get(c, "?") for c in w) in v) / n if n else 0.0


def refine(words: list[list[str]], key: dict, rounds: int = 4) -> dict:
    key = dict(key)
    cur = word_share(words, key)
    symbols = sorted({c for w in words for c in w}, key=lambda s: -sum(w.count(s) for w in words))
    for _ in range(rounds):
        changed = False
        for s in symbols:
            best, best_v = key.get(s), cur
            for l in LETTERS:
                if l != key.get(s):
                    key[s], old = l, key.get(s)
                    v = word_share(words, key)
                    key[s] = old
                    if v > best_v:
                        best, best_v = l, v
            if best != key.get(s):
                key[s], cur, changed = best, best_v, True
        if not changed:
            break
    return key


def pipeline(words: list[list[str]], ex) -> tuple[float, float, dict]:
    seq = [c for w in words for c in w]
    _, _, key = max(ex.map(_homo, [(seq, i) for i in range(7)]), key=lambda x: x[0])
    key = {k: v.lower() for k, v in key.items()}
    refined = refine(words, key)
    return word_share(words, key), word_share(words, refined), refined


def shuffled_words(words: list[list[str]], rnd: random.Random) -> list[list[str]]:
    flat = [c for w in words for c in w]
    rnd.shuffle(flat)
    out, pos = [], 0
    for w in words:
        out.append(flat[pos:pos + len(w)])
        pos += len(w)
    return out


def series(name: str) -> dict:
    if name == "jane":
        texts = {k: v.replace(" - 1925", "") for k, v in DATA["jane"].items()}
        return {k: [re.findall(r"\d+", w) for w in re.split(r"\s*-\s*|\s+", t) if re.findall(r"\d+", w)] for k, t in texts.items()}
    return {k: [list(w) for w in t.split()] for k, t in DATA[name].items()}


def planted_words(words: list[list[str]], seed: int = 7) -> tuple[list[list[str]], str]:
    """French running text cut into words of the same count, under a random homophonic key with as many symbols."""
    from ..languages import corpus_text

    rnd = random.Random(seed)
    corp = re.findall(r"[a-z]+", corpus_text("fr").lower())
    st = rnd.randrange(len(corp) - 2000)
    plain = corp[st:st + len(words)]
    n_sym = len({c for w in words for c in w})
    letters = sorted({c for w in plain for c in w})
    pool = [f"s{i}" for i in range(max(n_sym, len(letters)))]
    rnd.shuffle(pool)
    enc = {c: [pool[i]] for i, c in enumerate(letters)}
    for extra in pool[len(letters):]:
        enc[rnd.choice("eaisnrtu")].append(extra)
    return [[rnd.choice(enc[c]) for c in w] for w in plain], " ".join(plain)


def test(name: str, ex, shuffles: int = 3, seed: int = 56) -> dict:
    ads = series(name)
    words = [w for ws in ads.values() for w in ws]
    before, after, key = pipeline(words, ex)
    rnd, null = random.Random(seed), []
    for _ in range(shuffles):
        b, a, _ = pipeline(shuffled_words(words, rnd), ex)
        null.append({"blind": round(b, 3), "refined": round(a, 3)})
    from ..validation import coverage

    pw, ptext = planted_words(words)
    _, _, pkey = pipeline(pw, ex)
    pread = " ".join("".join(pkey.get(c, "?") for c in w) for w in pw)
    pcov = coverage(pread.replace(" ", "").replace("?", "").upper(), "fr")
    reading = " ".join("".join(key.get(c, "?") for c in w) for w in words)
    cov = coverage(reading.replace(" ", "").replace("?", "").upper(), "fr")
    acc = sum(a == b for a, b in zip(pread.replace(" ", ""), ptext.replace(" ", ""))) / len(ptext.replace(" ", ""))
    gates = {"control": acc >= 0.7, "null": after > max(n["refined"] for n in null), "reads": cov >= 0.8 * pcov}
    return {"series": name, "blind_share": round(before, 3), "refined_share": round(after, 3), "null": null,
            "planted_accuracy": round(acc, 3), "planted_refined_coverage": pcov, "coverage": cov, "gates": {**gates, "passed": all(gates.values())},
            "beats_null": after > max(n["refined"] for n in null), "key": key,
            "readings": {k: " ".join("".join(key.get(c, "?") for c in w) for w in ws) for k, ws in ads.items()}}


def run() -> dict:
    with ProcessPoolExecutor(7) as ex:
        return {"id": "figaro_wordrefine", "jane": test("jane", ex), "b": test("b", ex)}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for k in ("jane", "b"):
        r = res[k]
        print(k, r["blind_share"], "->", r["refined_share"], "null", r["null"], r["beats_null"], "planted", r["planted_accuracy"], r["planted_refined_coverage"], "cov", r["coverage"], r["gates"])
        for i, t in r["readings"].items():
            print("  ", i[:13], t)
