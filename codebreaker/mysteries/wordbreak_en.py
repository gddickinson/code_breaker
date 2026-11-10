"""Round 63: the word-break pipeline (Rounds 54-56) for English texts outside Le Figaro.

For each text with printed word breaks: plain English words are set aside (the 1916 cryptogram mixes them with
enciphered words), the rest are solved blind as one homophonic substitution of English (best of 7 seeds), refined with
the word breaks, and the identical pipeline runs on 3 shuffled copies and on a planted English control with the same
word lengths and symbol count. Gates: control recovered; refined words beat every refined shuffle; coverage reaches
0.8 of the refined planted control's."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

from ..attacks.classical import solve_symbols
from ..languages import ROOT, corpus_text, model, score
from ..validation import coverage

RESULT = ROOT / "data/results/wordbreak_en.json"
SRC = ROOT / "data/sources/unsolved"
TEXTS = {"1916 train station robbery cryptogram": "1916 train station robbery cryptogram.txt", "Ricky McCormick page 1": "Ricky McCormick page 1.txt",
         "Ricky McCormick page 2": "Ricky McCormick page 2.txt", "Paul Rubin": "Paul Rubin.txt"}
LETTERS = "abcdefghijklmnopqrstuvwxyz"


@lru_cache(maxsize=1)
def vocab() -> frozenset:
    return frozenset(str(w).lower() for w in model("en")["words"][:20000] if len(w) >= 2) | {"a", "i"}


def words_of(name: str) -> tuple[list[list[str]], list[str]]:
    """Enciphered words as symbol lists, and the plain English words set aside. 'McCormick stems' (Round 65) are the
    groups of both pages with a final -se or -be removed."""
    if name == "McCormick stems":
        raw = " ".join((SRC / TEXTS[f"Ricky McCormick page {i}"]).read_text(errors="ignore").lower() for i in (1, 2))
        groups = [g for g in re.split(r"[^a-z]+", raw) if g]
        stems = [g[:-2] if len(g) >= 3 and g[-2:] in ("se", "be") else g for g in groups]
        return [list(g) for g in stems if g], []
    raw = (SRC / TEXTS[name]).read_text(errors="ignore").lower()
    toks = [t for t in re.split(r"[\s\-()\[\]*.,;:'\"!]+", raw) if t]
    v = vocab()
    plain = [t for t in toks if name.startswith("1916") and t in v and len(t) >= 2]
    enc = [list(t) for t in toks if t not in plain and re.fullmatch(r"[a-z?0-9]+", t) and "?" not in t]
    return enc, plain


def _homo(a):
    seq, seed = a
    r = solve_symbols(seq, "en", homophonic=True, seed=seed, iters=6000000, restarts=4, w=1.0)
    return score(r["plaintext"], "en"), {k: v.lower() for k, v in r["key"].items()}


def share(words, key) -> float:
    v, n = vocab(), sum(map(len, words))
    return sum(len(w) for w in words if "".join(key.get(c, "?") for c in w) in v) / n if n else 0.0


def refine(words, key, rounds: int = 4) -> dict:
    key, cur = dict(key), share(words, key)
    syms = sorted({c for w in words for c in w}, key=lambda s: -sum(w.count(s) for w in words))
    for _ in range(rounds):
        changed = False
        for s in syms:
            best, bv = key.get(s), cur
            for l in LETTERS:
                if l != key.get(s):
                    old = key.get(s)
                    key[s] = l
                    val = share(words, key)
                    key[s] = old
                    if val > bv:
                        best, bv = l, val
            if best != key.get(s):
                key[s], cur, changed = best, bv, True
        if not changed:
            break
    return key


def pipeline(words, ex) -> tuple[float, float, dict]:
    seq = [c for w in words for c in w]
    _, key = max(ex.map(_homo, [(seq, i) for i in range(7)]), key=lambda x: x[0])
    k2 = refine(words, key)
    return share(words, key), share(words, k2), k2


def shuffled(words, rnd):
    flat = [c for w in words for c in w]
    rnd.shuffle(flat)
    out, pos = [], 0
    for w in words:
        out.append(flat[pos:pos + len(w)])
        pos += len(w)
    return out


def planted(words, seed: int = 63):
    rnd = random.Random(seed)
    corp = re.findall(r"[a-z]+", corpus_text("en").lower())
    st = rnd.randrange(len(corp) - 3000)
    plain = corp[st:st + len(words)]
    n_sym = len({c for w in words for c in w})
    letters = sorted({c for w in plain for c in w})
    pool = [f"s{i}" for i in range(max(n_sym, len(letters)))]
    rnd.shuffle(pool)
    enc = {c: [pool[i]] for i, c in enumerate(letters)}
    for extra in pool[len(letters):]:
        enc[rnd.choice("etaoinsr")].append(extra)
    return [[rnd.choice(enc[c]) for c in w] for w in plain], plain


def test(name: str, ex, shuffles: int = 3) -> dict:
    words, plain = words_of(name)
    before, after, key = pipeline(words, ex)
    rnd, null = random.Random(63), []
    for _ in range(shuffles):
        b, a, _ = pipeline(shuffled(words, rnd), ex)
        null.append(round(a, 3))
    pw, ptext = planted(words)
    _, _, pkey = pipeline(pw, ex)
    pread = "".join("".join(pkey.get(c, "?") for c in w) for w in pw)
    acc = sum(a == b for a, b in zip(pread, "".join(ptext))) / max(len("".join(ptext)), 1)
    pcov = coverage(pread.replace("?", "").upper(), "en")
    reading = " ".join("".join(key.get(c, "?") for c in w) for w in words)
    cov = coverage(reading.replace(" ", "").replace("?", "").upper(), "en")
    gates = {"control": acc >= 0.7, "null": after > max(null), "reads": cov >= 0.8 * pcov}
    return {"text": name, "words": len(words), "plain_words_set_aside": len(plain), "symbols": len({c for w in words for c in w}),
            "blind_share": round(before, 3), "refined_share": round(after, 3), "null_refined": null, "planted_accuracy": round(acc, 3),
            "planted_coverage": pcov, "coverage": cov, "gates": {**gates, "passed": all(gates.values())}, "reading": reading[:400]}


def run(names=None) -> dict:
    with ProcessPoolExecutor(7) as ex:
        rows = [test(n, ex) for n in (names or list(TEXTS))]
    return {"id": "wordbreak_en", "rows": rows, "passed": [r["text"] for r in rows if r["gates"]["passed"]]}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "stems":
        prev = json.loads(RESULT.read_text())
        res = run(["McCormick stems"])
        prev["mccormick_stems"] = res["rows"][0]
        RESULT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
        print(res["rows"][0])
        raise SystemExit
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for r in res["rows"]:
        print(r["text"], r["words"], r["symbols"], r["blind_share"], "->", r["refined_share"], r["null_refined"], r["planted_accuracy"], r["coverage"], round(0.8 * r["planted_coverage"], 3), r["gates"])
        print("   ", r["reading"][:200])
