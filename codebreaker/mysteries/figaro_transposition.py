"""Irregular transpositions on Le Figaro ads: word anagrams and columnar grids with a short last row."""
import json
import random
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from itertools import permutations

from ..languages import ROOT, corpus_text, score
from ..segment import segment
from ..text import letters
from ..validation import coverage
from .figaro_digit_family import words as vocabulary
from .figaro_digit_words import letters_lower
from .figaro_keys import OUT, cipher_words
from ..third_party import need

RESULT = ROOT / "data/results/figaro_transposition.json"
WIDTHS = range(3, 8)
MIN_LETTERS = 24
TOP = 6


@lru_cache(maxsize=1)
def anagrams() -> frozenset:
    return frozenset("".join(sorted(w)) for w in vocabulary())


def word_anagram_share(words: list[str]) -> float:
    """Share of letters in words whose letters can be rearranged into a common French word."""
    a, n = anagrams(), sum(map(len, words))
    return sum(len(w) for w in words if len(w) >= 2 and "".join(sorted(w)) in a) / n if n else 0.0


def column_lengths(n: int, w: int) -> list[int]:
    """Columns in an irregular grid: the first n mod w columns are one letter longer."""
    rows, extra = divmod(n, w)
    return [rows + (i < extra) for i in range(w)]


def undo(t: str, order: tuple) -> str:
    """Read off columns in key order, as an encipherer would have written them, and rebuild the rows."""
    w, lens = len(order), column_lengths(len(t), len(order))
    cols, pos = [""] * w, 0
    for c in order:
        cols[c] = t[pos:pos + lens[c]]
        pos += lens[c]
    return "".join(cols[c][r] for r in range(lens[0]) for c in range(w) if r < len(cols[c]))


def redo(p: str, order: tuple) -> str:
    return "".join(p[c::len(order)] for c in order)


def best_columnar(t: str) -> tuple:
    """Every key of width 3 to 7, each way round; rank by letter score, then check real words."""
    top = []
    for w in WIDTHS:
        for order in permutations(range(w)):
            for name, p in ((f"undo width {w}", undo(t, order)), (f"redo width {w}", redo(t, order))):
                top.append((score(p, "fr"), name, order, p))
        top = sorted(top, key=lambda x: -x[0])[:TOP * 3]
    top = top[:TOP]
    return max(((coverage(p, "fr"), s, n, o, p) for s, n, o, p in top), key=lambda x: x[:2])


def shuffle_within(words: list[str], rnd: random.Random) -> list[str]:
    out = []
    for w in words:
        c = list(w)
        rnd.shuffle(c)
        out.append("".join(c))
    return out


def _control(a):
    kind, plain, seed = a
    rnd = random.Random(seed)
    if kind == "columnar":
        w = rnd.choice(list(WIDTHS)[:4])
        order = tuple(rnd.sample(range(w), w))
        t = redo(letters(plain), order)
        got = best_columnar(t)[4]
        return sum(x == y for x, y in zip(got, letters(plain))) / len(letters(plain))
    return word_anagram_share(shuffle_within(plain.upper().split(), rnd))


def _ad(a):
    name, words, seed = a
    rnd, t = random.Random(seed), "".join(words)
    c, s, method, order, p = best_columnar(t)
    sh = list(t)
    rnd.shuffle(sh)
    return {"image": name, "letters": len(t), "text": " ".join(words), "columnar": round(c, 3), "null": round(best_columnar("".join(sh))[0], 3), "method": method, "order": list(order), "reading": segment(p.lower(), "fr"), "anagram": round(word_anagram_share(words), 3), "anagram_null": round(word_anagram_share(shuffled_words(words, rnd)), 3)}


def shuffled_words(words: list[str], rnd: random.Random) -> list[str]:
    s = list("".join(words))
    rnd.shuffle(s)
    out, i = [], 0
    for w in words:
        out.append("".join(s[i:i + len(w)]))
        i += len(w)
    return out


def phrases(n: int, target: int, seed: int) -> list[str]:
    corp, rnd = re.findall(r"[a-z]+", letters_lower()), random.Random(seed)
    out = []
    for _ in range(n):
        i, run = rnd.randrange(len(corp) - 200), []
        while sum(map(len, run)) < target:
            run.append(corp[i])
            i += 1
        out.append(" ".join(run))
    return out


def run() -> dict:
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    ads = json.loads(need(OUT / "ads.json").read_text())
    jobs = []
    for i, a in enumerate(ads):
        if a["solved"]:
            continue
        n = a["image"].replace("/", "_")
        sets = [e for s in (otsu, raw) for e in s.get(n, {}).values() if e]
        pick = max((cipher_words(e) for e in sets), key=lambda w: sum(map(len, w)), default=[])
        t = "".join(pick)
        if len(t) >= MIN_LETTERS and coverage(t[:400], "fr") < 0.35:
            jobs.append((n, pick, 1200 + i))
    with ProcessPoolExecutor(7) as ex:
        col = list(ex.map(_control, [("columnar", p, i) for i, p in enumerate(phrases(30, 45, 3))], chunksize=2))
        ana = list(ex.map(_control, [("anagram", p, i) for i, p in enumerate(phrases(60, 45, 4))], chunksize=6))
        rows = list(ex.map(_ad, jobs, chunksize=2))
    rows.sort(key=lambda r: -(r["columnar"] - r["null"]))
    nulls = sorted(r["anagram_null"] for r in rows)
    cut = nulls[int(len(nulls) * 0.99)] if nulls else 1.0
    return {"id": "figaro_transposition", "columnar_control": {"n": len(col), "solved": sum(a >= 0.7 for a in col)}, "anagram_control": {"n": len(ana), "above_cut": sum(a > cut for a in ana), "cut": round(cut, 3)}, "tested": len(rows), "null_max": max((r["null"] for r in rows), default=0), "rows": rows}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print({k: v for k, v in out.items() if k != "rows"})
    for r in out["rows"][:12]:
        print("C", r["image"], r["letters"], r["columnar"], r["null"], r["method"], r["reading"][:95])
    for r in sorted(out["rows"], key=lambda r: -(r["anagram"] - r["anagram_null"]))[:12]:
        print("A", r["image"], r["letters"], r["anagram"], r["anagram_null"], r["text"][:90])
