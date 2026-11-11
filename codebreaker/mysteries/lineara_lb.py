"""Round 80: Linear A read with Linear B sound values, against controls. Never a decipherment claim.

Fixed before running:
  Linear A words: the corpus in data/sources/scripts_lab/lineara.js (lineara.xyz; GORILA numbering), whose words are
    written with the conventional Linear B values (KU-RO); distinct words of 2+ syllabic signs.
  Lexicon: Mycenaean Greek spellings from Wiktionary (data/sources/glosses/mycenaean.json, CC BY-SA), read into
    syllables with the Linear B sign table (writing/signs.py); spellings of 2+ syllables.
  Statistic: the number of distinct Linear A words that equal a Mycenaean spelling.
  Null: the same words with the sound values permuted at random among the signs Linear A uses (2,000 permutations):
    word shapes and sign frequencies are kept, the values are not.
  Power control: genuine Mycenaean spellings planted among the Linear A words at known shares, with the same null:
    how large a Greek component this test can see.
A significant excess would show only that some Linear A words share spellings with Mycenaean (place and personal names
are long known to: pa-i-to, Phaistos), not that Linear A is Greek."""
import json
import random
import re
import unicodedata

from ..languages import ROOT
from ..writing.signs import tables
from .scriptlab import linear_a

RESULT = ROOT / "data/results/lineara_lb.json"
SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def la_words() -> set[tuple[str, ...]]:
    return {tuple(s.lower().translate(SUB) for s in w) for w in linear_a() if len(w) >= 2}


def lexicon() -> dict[tuple[str, ...], str]:
    """Mycenaean spellings as syllable tuples, with the Wiktionary title they come from."""
    data = json.loads((ROOT / "data/sources/glosses/mycenaean.json").read_text())
    lb = tables()["linear_b"]
    out = {}
    for title in data:
        signs = [c for c in unicodedata.normalize("NFC", title) if c in lb]
        vals = [lb[c]["values"][0] if lb[c]["values"] else None for c in signs]
        if len(vals) >= 2 and all(v and not v.startswith(("[", "*")) for v in vals) and len(signs) == len(re.sub(r"\s", "", title)):
            out[tuple(vals)] = title
    return out


def matches(words: set, lex: dict) -> set:
    return {w for w in words if w in lex}


def permuted(words: set, rnd: random.Random) -> set:
    signs = sorted({s for w in words for s in w})
    perm = signs[:]
    rnd.shuffle(perm)
    m = dict(zip(signs, perm))
    return {tuple(m[s] for s in w) for w in words}


def null_counts(words: set, lex: dict, trials: int, seed: int) -> list[int]:
    rnd = random.Random(seed)
    return [len(matches(permuted(words, rnd), lex)) for _ in range(trials)]


def power(words: set, lex: dict, shares=(0.005, 0.01, 0.02, 0.05), reps: int = 20, trials: int = 300, seed: int = 81) -> dict:
    """Planted Greek: that share of the Linear A words replaced by Mycenaean spellings not already matched."""
    rnd, pool, base = random.Random(seed), [k for k in lex if k not in words], sorted(words)
    out = {}
    for sh in shares:
        hits = 0
        for r in range(reps):
            n = max(1, int(sh * len(base)))
            keep = rnd.sample(base, len(base) - n)
            w = set(keep) | set(rnd.sample(pool, n))
            real = len(matches(w, lex))
            null = null_counts(w, lex, trials, seed + r)
            hits += (sum(x >= real for x in null) + 1) / (trials + 1) <= 0.05
        out[str(sh)] = {"planted_words": max(1, int(sh * len(base))), "detected_at_p05": round(hits / reps, 2)}
    return out


def run(trials: int = 2000, seed: int = 80) -> dict:
    words, lex = la_words(), lexicon()
    hit = matches(words, lex)
    null = null_counts(words, lex, trials, seed)
    p = (sum(x >= len(hit) for x in null) + 1) / (trials + 1)
    return {"id": "lineara_lb", "linear_a_words": len(words), "lexicon_spellings": len(lex), "matches": len(hit),
            "matched": sorted(("-".join(w), lex[w]) for w in hit), "null_mean": round(sum(null) / trials, 2), "null_max": max(null),
            "p": round(p, 4), "power": power(words, lex),
            "note": "Matches are spellings shared with Mycenaean Greek under Linear B values; place and personal names are expected to carry over. This tests the values, not the language."}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, ensure_ascii=False, indent=1))
    print({k: v for k, v in r.items() if k not in ("matched",)})
    print(r["matched"])
