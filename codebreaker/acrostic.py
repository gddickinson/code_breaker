"""Acrostics and null ciphers (Round 83): messages hidden in the letters of an ordinary text.

Readings: first and last letters of lines, first letters of sentences, first, second and last letters of words (the
classic null cipher), and every n-th letter (n = 2..12, every starting offset). A reading of 8+ letters is scored by
word coverage (validation.coverage: share of letters inside dictionary words of 4+ letters after segmentation) in
each of the app's six languages. Null: the same reading taken from the text with its units shuffled (lines,
sentences or words), 200 times. A reading counts only at p <= 0.05 / (readings x languages tried), so trying many
readings does not manufacture a message. That bar is far below 1/201, so a reading no shuffle reaches in the first
200 gets 2/bar further shuffles of its own (the null must be able to reach the bar: Rounds 71 and 72)."""
import random
import re

from .languages import LANGS
from .text import letters
from .validation import coverage

MIN_LETTERS = 8


def _units(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if letters(l)]
    sentences = [s for s in re.split(r"(?<=[.!?;])\s+", " ".join(lines)) if letters(s)]
    words = [w for w in re.findall(r"[^\W\d_]+", text)]
    return {"lines": lines, "sentences": sentences, "words": words}


def _first(units: list[str]) -> str:
    return "".join(letters(u)[:1] for u in units)


def _last(units: list[str]) -> str:
    return "".join(letters(u)[-1:] for u in units)


def readings(u: dict) -> dict[str, str]:
    """Every reading tried, as name -> letters."""
    out = {"first letters of lines": _first(u["lines"]), "last letters of lines": _last(u["lines"]),
           "first letters of sentences": _first(u["sentences"]), "first letters of words": _first(u["words"]),
           "second letters of words": "".join(letters(w)[1:2] for w in u["words"]), "last letters of words": _last(u["words"])}
    flat = letters(" ".join(u["words"]))
    for n in range(2, 13):
        for off in range(n):
            out[f"every {n}th letter from letter {off + 1}"] = flat[off::n]
    return {k: v for k, v in out.items() if len(v) >= MIN_LETTERS}


def reading(u: dict, name: str) -> str:
    """One reading by name, without computing the others (for the second stage)."""
    m = re.match(r"every (\d+)th letter from letter (\d+)", name)
    if m:
        n, off = int(m.group(1)), int(m.group(2)) - 1
        return letters(" ".join(u["words"]))[off::n]
    return readings(u).get(name, "")


def _shuffled(u: dict, rnd: random.Random) -> dict:
    """Lines, sentences and words each shuffled; a text of few words (an unbroken letter string) has its letters
    shuffled instead, or the null would equal the text itself."""
    v = {k: list(x) for k, x in u.items()}
    for x in v.values():
        rnd.shuffle(x)
    if len(u["words"]) < 10:
        flat = list(letters(" ".join(u["words"])))
        rnd.shuffle(flat)
        v["words"] = ["".join(flat)]
    return v


def find(text: str, langs=tuple(LANGS), shuffles: int = 200, seed: int = 83, max_letters: int = 400) -> dict:
    u = _units(text)
    reads = {k: v[:max_letters] for k, v in readings(u).items()}
    tests = len(reads) * len(langs)
    bar = 0.05 / max(tests, 1)
    rnd = random.Random(seed)
    nulls = [readings(_shuffled(u, rnd)) for _ in range(shuffles)]
    found = []
    for name, s in reads.items():
        for lang in langs:
            c = coverage(s, lang)
            if c < 0.5:  # cheap screen: below half the letters in words no null could make it count
                continue
            null = [coverage(nr.get(name, "")[:max_letters], lang) for nr in nulls if nr.get(name)]
            p = (sum(x >= c for x in null) + 1) / (len(null) + 1)
            if p <= 1 / (len(null) + 1) and p > bar:  # nothing reached it: enough shuffles that p can fall below the bar
                more = [coverage(reading(_shuffled(u, rnd), name)[:max_letters], lang) for _ in range(int(2 / bar))]
                p = (sum(x >= c for x in null + more) + 1) / (len(null) + len(more) + 1)
            if p <= bar:
                found.append({"reading": name, "letters": s, "lang": lang, "language": LANGS[lang], "coverage": round(c, 3), "p": round(p, 5)})
    found.sort(key=lambda f: (-f["coverage"], f["p"]))
    return {"readings_tried": len(reads), "languages": list(langs), "bar": bar, "findings": found[:10],
            "note": f"{len(reads)} readings in {len(langs)} languages; a finding needs p <= {bar:.1e} against the text's own units shuffled."}
