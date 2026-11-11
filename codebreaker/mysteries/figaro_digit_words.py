"""Letter-digit ads by dictionary beam search: word breaks do the work that letter statistics cannot."""
import json
import random
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher
from functools import lru_cache

import numpy as np
from numba import njit

from ..languages import ROOT, corpus_text
from ..text import A, letters
from .figaro_digits import pick
from .figaro_keys import OUT
from ..third_party import need

RESULT = ROOT / "data/results/figaro_digit_words.json"
HAND = ROOT / "data/mysteries/figaro_digit_hand.json"
SYM = A + "0123456789"
TOP = 6000
BEAM = 400
MISS = -14.0


@lru_cache(maxsize=1)
def vocabulary():
    """Commonest French words as a matrix per length, with log frequencies."""
    words = re.findall(r"[a-z]+", re.sub(r"[^a-z]+", " ", letters_lower()))
    counts = Counter(w for w in words if len(w) > 1 or w in ("a", "y"))
    top = counts.most_common(TOP)
    n = sum(counts.values())
    by = {}
    for w, c in top:
        if len(w) <= 14:
            by.setdefault(len(w), []).append((w.upper(), float(np.log(c / n))))
    return {k: (np.array([[A.index(ch) for ch in w] for w, _ in v], dtype=np.int8), np.array([f for _, f in v])) for k, v in by.items()}


def letters_lower() -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", corpus_text("fr").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


@njit(cache=True)
def _expand(keys, used, scores, word, vocab, freqs, beam):
    """All consistent extensions of the beam by one cipher word, plus the option to leave it unread."""
    L, nb, nv = len(word), keys.shape[0], vocab.shape[0]
    cap = max(nb * 30, beam * 4)
    ps, ws, ss = np.zeros(cap, np.int64), np.zeros(cap, np.int64), np.zeros(cap)
    m = 0
    for b in range(nb):
        for v in range(nv):
            ok, base = True, keys[b]
            for i in range(L):
                s, l = word[i], vocab[v, i]
                k = base[s]
                if k >= 0:
                    if k != l:
                        ok = False
                        break
                    continue
                if s < 26 and (used[b] >> l) & 1:
                    ok = False
                    break
                for j in range(i):
                    if word[j] == s and vocab[v, j] != l:
                        ok = False
                        break
                    if word[j] != s and word[j] < 26 and s < 26 and vocab[v, j] == l and base[word[j]] < 0:
                        ok = False
                        break
                if not ok:
                    break
            if ok and m < cap:
                ps[m], ws[m], ss[m] = b, v, scores[b] + freqs[v] + 0.9 * L
                m += 1
    for b in range(nb):
        if m < cap:
            ps[m], ws[m], ss[m] = b, -1, scores[b] + MISS - 0.5 * L
            m += 1
    order = np.argsort(-ss[:m])[:beam]
    nk, nu, ns = np.empty((len(order), keys.shape[1]), np.int8), np.zeros(len(order), np.int64), np.zeros(len(order))
    for t, o in enumerate(order):
        b, v = ps[o], ws[o]
        nk[t] = keys[b]
        u = used[b]
        if v >= 0:
            for i in range(L):
                nk[t, word[i]] = vocab[v, i]
                if word[i] < 26:
                    u |= 1 << int(vocab[v, i])
        nu[t], ns[t] = u, ss[o]
    return nk, nu, ns


def solve(text: str) -> dict:
    """Beam over the cipher words, longest first, then read the whole text with the best key."""
    words = text.split()
    vocab = vocabulary()
    arr = [np.array([SYM.index(c) for c in w], dtype=np.int8) for w in words]
    keys, used, scores = np.full((1, 36), -1, np.int8), np.zeros(1, np.int64), np.zeros(1)
    for i in sorted(range(len(words)), key=lambda x: -len(words[x])):
        L = len(words[i])
        if L in vocab:
            keys, used, scores = _expand(keys, used, scores, arr[i], vocab[L][0], vocab[L][1], BEAM)
    key = keys[0]
    out = ["".join(A[key[SYM.index(c)]] if key[SYM.index(c)] >= 0 else "." for c in w) for w in words]
    known = sum(c != "." for w in out for c in w)
    allw = {w for L, (m, _) in vocab.items() for w in ("".join(A[x] for x in row) for row in m)}
    read = sum(len(w) for w in out if w in allw)
    n = sum(len(w) for w in out)
    return {"words": out, "read": read / n, "known": known / n, "score": float(scores[0]) / n}


def shuffled(text: str, rnd: random.Random) -> str:
    s = list(text.replace(" ", ""))
    rnd.shuffle(s)
    it = iter(s)
    return "".join(" " if c == " " else next(it) for c in text)


def planted(rnd: random.Random, words: list[str], target: int) -> tuple[str, str]:
    """A French word run, randomly substituted, with five common letters written as digits."""
    i, run = rnd.randrange(len(words) - 200), []
    while sum(map(len, run)) < target:
        run.append(words[i])
        i += 1
    plain = " ".join(run).upper()
    mixed = rnd.sample(A, 26)
    table = dict(zip(A, mixed))
    table.update(zip(rnd.sample("EAISTN", 5), rnd.sample("0123456789", 5)))
    return "".join(table.get(c, c) for c in plain), plain


def _ctl(a):
    cipher, plain = a
    r = solve(cipher)
    return sum(x == y for x, y in zip(" ".join(r["words"]), plain)) / len(plain)


def _ad(a):
    name, text, seed = a
    r = solve(text)
    return {"image": name, "text": text, "null": solve(shuffled(text, random.Random(seed)))["read"], **r}


def qualifies(words: str) -> bool:
    toks = words.split()
    return sum(bool(re.search(r"\d", t)) and len(t) >= 3 for t in toks) >= 3 and len(words.replace(" ", "")) >= 20


def run() -> dict:
    corp, rnd = [w for w in re.findall(r"[a-z]+", letters_lower())], random.Random(9)
    ctrl = {}
    with ProcessPoolExecutor(7) as ex:
        for target in (30, 50, 90):
            acc = list(ex.map(_ctl, [planted(rnd, corp, target) for _ in range(30)], chunksize=2))
            ctrl[target] = {"mean": round(sum(acc) / len(acc), 3), "solved": sum(a >= 0.7 for a in acc), "n": len(acc)}
        otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
        ads = json.loads(need(OUT / "ads.json").read_text())
        unsolved = {a["image"].replace("/", "_") for a in ads if not a["solved"]}
        jobs = [(n, w, 300 + i) for i, n in enumerate(sorted(unsolved)) if qualifies(w := pick([e for src in (otsu, raw) for e in src.get(n, {}).values()]))]
        rows = list(ex.map(_ad, jobs, chunksize=3))
        hand = [dict(image=n, text=v["words"], null=solve(shuffled(v["words"], random.Random(1)))["read"], **solve(v["words"])) for n, v in json.loads(HAND.read_text()).items()]
    rows.sort(key=lambda r: -(r["read"] - r["null"]))
    return {"id": "figaro_digit_words", "control": ctrl, "tested": len(rows), "hand": hand, "rows": rows}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(out["control"], out["tested"])
    for r in out["hand"] + out["rows"][:14]:
        print(r["image"], round(r["read"], 2), round(r["null"], 2), " ".join(r["words"])[:110], "<<", r["text"][:50])
