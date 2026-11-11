"""Language models over each language's own alphabet (Round 86): Cyrillic, Greek, Hebrew and Arabic-script languages.

The core models (languages.py) fold everything onto A-Z. Here each language keeps its letters: a text is normalised
(lower case; accents and vowel points removed; Greek final sigma, Hebrew final forms and Arabic letter variants folded
onto one letter each, as cipher clerks wrote them), its alphabet is the set of letters making up 0.05% or more of the
corpus, and quadgrams, letter frequencies and a word list are built over that alphabet. Corpora: Project Gutenberg
(el, ru, bg, he), Wikipedia extracts (scripts/fetch_wiki_corpora.py; Russian so far) and the language identifier's
Wikipedia intros (about 40,000 characters a language; the only source for uk, ar, fa, ur).
Coverage: the share of letters inside dictionary words after Viterbi segmentation, words of 4+ letters (3+ in Hebrew
and Arabic script, which omit most vowels)."""
import re
import unicodedata
from collections import Counter
from functools import lru_cache

import numpy as np

from .languages import CORPORA, FILES, MODELS, corpus_text

LANGS = {"ru": ("Russian", "Cyrillic"), "uk": ("Ukrainian", "Cyrillic"), "bg": ("Bulgarian", "Cyrillic"), "el": ("Greek", "Greek"),
         "he": ("Hebrew", "Hebrew"), "ar": ("Arabic", "Arabic"), "fa": ("Persian", "Arabic"), "ur": ("Urdu", "Arabic")}
BLOCKS = {"Cyrillic": (0x0400, 0x04FF), "Greek": (0x0370, 0x03FF), "Hebrew": (0x0590, 0x05FF), "Arabic": (0x0600, 0x06FF)}
# Gutenberg books, Wikipedia extracts, and the language identifier's Wikipedia intros (data/sources/langid, Round 85)
FILES.update({c: [f for f in (f"extra/{c}.txt", f"extra/{c}_wiki.txt", f"../sources/langid/{c}.txt") if (CORPORA / f).exists()] for c in LANGS})
MIN_WORD = {"Hebrew": 3, "Arabic": 3}
_FOLD = {"Greek": str.maketrans({"ς": "σ"}), "Hebrew": str.maketrans({"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}),
         "Cyrillic": str.maketrans({"ё": "е"}),
         "Arabic": str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ـ": None, "ۀ": "ه", "ة": "ه"})}
_PERSO = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})  # Persian and Urdu write these letters in their own forms
_ARABIC = str.maketrans({"ی": "ي", "ى": "ي", "ک": "ك"})


def script_of(lang: str) -> str:
    return LANGS[lang][1]


def in_block(c: str, script: str) -> bool:
    lo, hi = BLOCKS[script]
    return lo <= ord(c) <= hi and c.isalpha()


def normalise(text: str, lang: str) -> str:
    """Lower case, marks removed, letter variants folded; characters outside the script are kept as they are."""
    s = script_of(lang)
    t = unicodedata.normalize("NFD", text.lower())
    if s == "Cyrillic":  # only stress accents go: the breve of й and the dots of ї are part of the letter
        t = t.replace("\u0301", "").replace("\u0300", "")
    else:
        t = "".join(c for c in t if not unicodedata.combining(c))
    t = unicodedata.normalize("NFC", t).translate(_FOLD[s])
    if s == "Arabic":
        t = t.translate(_PERSO if lang in ("fa", "ur") else _ARABIC)
    return t


def available() -> list[str]:
    return [c for c in LANGS if FILES[c]]


def script_letters(text: str, lang: str) -> str:
    """The text's letters in the language's alphabet, nothing else."""
    alpha = set(model(lang)["alpha"])
    return "".join(c for c in normalise(text, lang) if c in alpha)


def to_ints(text: str, lang: str) -> np.ndarray:
    idx = {c: i for i, c in enumerate(model(lang)["alpha"])}
    return np.array([idx[c] for c in script_letters(text, lang)], dtype=np.int32)


def to_text(a, lang: str) -> str:
    alpha = model(lang)["alpha"]
    return "".join(alpha[int(i)] for i in a)


HELD_OUT = 0.1  # the last tenth of each corpus is never used for the model: controls and baselines are drawn from it


def held_out(lang: str) -> str:
    t = corpus_text(lang)
    return t[int(len(t) * (1 - HELD_OUT)):]


def _build(lang: str) -> dict:
    s = script_of(lang)
    t = corpus_text(lang)
    text = normalise(t[:int(len(t) * (1 - HELD_OUT))], lang)
    counts = Counter(c for c in text if in_block(c, s))
    total = sum(counts.values())
    alpha = "".join(sorted(c for c, n in counts.items() if n / total >= 0.0005))
    idx = {c: i for i, c in enumerate(alpha)}
    a = np.array([idx[c] for c in text if c in idx], dtype=np.int64)
    A = len(alpha)
    q = ((a[:-3] * A + a[1:-2]) * A + a[2:-1]) * A + a[3:]
    c4 = np.bincount(q, minlength=A ** 4).astype(np.float64)
    table = np.log10((c4 + 0.05) / (c4.sum() + 0.05 * A ** 4))
    words = Counter(w for w in re.findall(f"[{re.escape(alpha)}]+", text))
    top = [w for w, _ in words.most_common(60000)]
    n_words = sum(words.values())
    return {"alpha": np.array(alpha), "table": table, "letter": np.bincount(a, minlength=A) / len(a),
            "words": np.array(top), "word_freq": np.array([words[w] for w in top], np.float64) / n_words}


@lru_cache(maxsize=None)
def model(lang: str) -> dict:
    path = MODELS / f"alpha_{lang}.npz"
    if not path.exists():
        MODELS.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **_build(lang))
    d = dict(np.load(path, allow_pickle=False))
    d["alpha"] = str(d["alpha"])
    return d


@lru_cache(maxsize=None)
def _probs(lang: str) -> dict:
    import math

    m = model(lang)
    return {str(w): math.log10(float(f)) for w, f in zip(m["words"], m["word_freq"])}


@lru_cache(maxsize=None)
def _vocab(lang: str) -> frozenset:
    return frozenset(str(w) for w in model(lang)["words"][:20000])


def segment(text: str, lang: str) -> str:
    from .segment import viterbi

    return viterbi(text, _probs(lang))


def coverage(text: str, lang: str) -> float:
    """Share of letters inside dictionary words (4+ letters; 3+ in Hebrew and Arabic script) after segmentation."""
    k = MIN_WORD.get(script_of(lang), 4)
    words, parts = _vocab(lang), segment(text, lang).split()
    return round(sum(len(w) for w in parts if len(w) >= k and w in words) / max(sum(map(len, parts)), 1), 3)


def detect_script(text: str) -> tuple[str | None, float]:
    """The script most of the text's letters belong to, and that share (None when Latin or unknown dominate)."""
    letters_ = [c for c in text if c.isalpha()]
    if not letters_:
        return None, 0.0
    counts = {s: sum(in_block(c, s) for c in letters_) for s in BLOCKS}
    best = max(counts, key=counts.get)
    share = counts[best] / len(letters_)
    return (best, share) if share >= 0.6 else (None, share)
