"""Controls and worked examples for the acrostic finder (Round 83).

Positive controls: messages planted as the first letters of lines (an acrostic poem made of corpus sentences that
begin with the right letters), as the first letters of words (a null cipher made of corpus words), and as every 5th
letter of a passage. Null: plain corpus passages of the same sizes, for the false-alarm rate at the Bonferroni bar.
Worked example from a recorded source: the chapter initials of the Hypnerotomachia Poliphili (1499), read in Latin.
Lesson: the 1944 D-Day crossword answers, with a base-rate estimate (see dday_base_rate)."""
import json
import math
import random
import re
from collections import Counter

from .acrostic import find
from .languages import ROOT, corpus_text
from .text import letters
from .validation import coverage

RESULT = ROOT / "data/results/acrostic_eval.json"
MESSAGES = ["MEETMEATMIDNIGHT", "THEGOLDISBURIED", "TRUSTNOONEHERE", "SENDMOREMONEY", "WATCHTHEDOOR"]
HYPNEROTOMACHIA = "POLIAMFRATERFRANCISCVSCOLVMNAPERAMAVIT"  # Wikipedia, Hypnerotomachia Poliphili (saved page)
U_FOR_V = "POLIAMFRATERFRANCISCUSCOLUMNAPERAMAVIT"  # the same with U where the printed V stands for the vowel
DDAY = {"UTAH": "2 May 1944", "OMAHA": "22 May 1944", "OVERLORD": "27 May 1944", "MULBERRY": "30 May 1944", "NEPTUNE": "1 June 1944"}


def _sentences(rnd: random.Random) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", corpus_text("en"))
    return [" ".join(s.split()) for s in raw if 40 < len(" ".join(s.split())) < 110]


def acrostic_poem(msg: str, sents: list[str], rnd: random.Random) -> str:
    by = {}
    for s in sents:
        by.setdefault(s[0].upper(), []).append(s)
    return "\n".join(rnd.choice(by[c]) for c in msg)


def null_cipher(msg: str, rnd: random.Random) -> str:
    words = re.findall(r"[a-z]{3,}", corpus_text("en").lower())
    by = {}
    for w in words[:200000]:
        by.setdefault(w[0].upper(), []).append(w)
    return " ".join(rnd.choice(by[c]) for c in msg) + "."


def every_nth(msg: str, n: int, sents: list[str], rnd: random.Random) -> str:
    """A passage of corpus sentences with every n-th letter replaced by the message, spaces and punctuation kept."""
    text = list(" ".join(rnd.sample(sents, 12)))
    pos = [i for i, c in enumerate(text) if c.isalpha() and c.isascii()]
    for k, c in enumerate(msg):
        text[pos[k * n]] = c.lower()
    return "".join(text[:pos[(len(msg) - 1) * n] + 40])


def dday_base_rate(answers_per_month=(600, 900)) -> dict:
    """Chance of all five codewords among a month's crossword answers if answers were drawn by word frequency from the
    app's English corpus (a crude assumption: setters choose words differently, and proper names are rare in novels).
    Counts are smoothed by 0.5 so unseen words are rare, not impossible. Answers per month are not recorded; a range
    is used (about 25 puzzles of 25-35 answers)."""
    toks = re.findall(r"[A-Z]+", corpus_text("en").upper())
    counts = Counter(t for t in toks if 4 <= len(t) <= 9)
    total = sum(counts.values())
    out = {"corpus_counts": {w: counts.get(w, 0) for w in DDAY}, "eligible_tokens": total}
    for n in answers_per_month:
        probs = {w: 1 - math.exp(-n * (counts.get(w, 0) + 0.5) / total) for w in DDAY}
        out[str(n)] = {"each": {w: f"{p:.2e}" for w, p in probs.items()}, "all_five": f"{math.prod(probs.values()):.2e}"}
    return out


def run(trials: int = 5, seed: int = 83) -> dict:
    rnd = random.Random(seed)
    sents = _sentences(rnd)
    kinds = {"acrostic poem": lambda m: acrostic_poem(m, sents, rnd), "null cipher": lambda m: null_cipher(m, rnd),
             "every 5th letter": lambda m: every_nth(m, 5, sents, rnd)}
    pos = {}
    for kind, make in kinds.items():
        hits = 0
        for m in MESSAGES[:trials]:
            r = find(make(m), langs=("en", "fr", "de"))
            hits += any(m[:8] in f["letters"] for f in r["findings"])
        pos[kind] = {"planted": trials, "found": hits}
    false = 0
    for _ in range(trials * 2):
        r = find("\n".join(rnd.sample(sents, 16)), langs=("en", "fr", "de"))
        false += bool(r["findings"])
    hyp = {"letters": HYPNEROTOMACHIA}
    for name, t in (("as printed (V for U)", HYPNEROTOMACHIA), ("U for the vowel", U_FOR_V)):
        c = coverage(t, "la")
        shuf = []
        for _ in range(500):
            s = list(t)
            rnd.shuffle(s)
            shuf.append(coverage("".join(s), "la"))
        from .segment import segment
        hyp[name] = {"latin_coverage": c, "segmented": segment(t, "la"), "shuffled_max": max(shuf),
                     "p": round((sum(x >= c for x in shuf) + 1) / 501, 4)}
    return {"id": "acrostic_eval", "positive_controls": pos, "plain_passages_with_findings": f"{false} of {trials * 2}",
            "hypnerotomachia": hyp, "dday": {"codewords": DDAY, "base_rate": dday_base_rate()}}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))
