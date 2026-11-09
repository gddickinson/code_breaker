"""Per-language statistics built from the public-domain corpora in data/corpora."""
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np

from .kernels import quad_score
from .text import letters, strip_accents, to_ints

ROOT = Path(__file__).resolve().parent.parent
CORPORA, MODELS = ROOT / "data/corpora", ROOT / "data/models"
LANGS = {"en": "English", "fr": "French", "de": "German", "it": "Italian", "es": "Spanish", "la": "Latin"}
FILES = {"en": ["en.txt", "en2.txt"], "fr": ["fr.txt"], "de": ["de.txt"], "it": ["it.txt"], "es": ["es.txt"], "la": ["la.txt"]}


def corpus_text(lang: str) -> str:
    """Corpus text with the Project Gutenberg header and licence removed."""
    parts = []
    for name in FILES[lang]:
        raw = (CORPORA / name).read_text(encoding="utf-8", errors="ignore")
        start = re.search(r"\*\*\* START OF.*?\*\*\*", raw)
        end = re.search(r"\*\*\* END OF", raw)
        parts.append(raw[start.end() if start else 0 : end.start() if end else None])
    return "\n".join(parts)


def _build(lang: str) -> dict:
    text = corpus_text(lang)
    ints = to_ints(text)
    idx = ints[:-3] * 17576 + ints[1:-2] * 676 + ints[2:-1] * 26 + ints[3:]
    counts = np.bincount(idx, minlength=26**4).astype(np.float64)
    table = np.log10((counts + 0.05) / (counts.sum() + 0.05 * 26**4)).astype(np.float64)
    words = [letters(w) for w in re.findall(r"[^\W\d_]+", strip_accents(text))]
    words = [w for w in words if w]
    wc = Counter(words)
    top = [w for w, _ in wc.most_common(60000)]
    freqs = np.array([wc[w] for w in top], dtype=np.float64)
    initial = np.bincount([ord(w[0]) - 65 for w in words], minlength=26) / len(words)
    return {"table": table, "letter": np.bincount(ints, minlength=26) / len(ints), "initial": initial,
            "words": np.array(top), "word_freq": freqs / len(words)}


@lru_cache(maxsize=None)
def model(lang: str = "en") -> dict:
    MODELS.mkdir(parents=True, exist_ok=True)
    path = MODELS / f"{lang}.npz"
    if not path.exists():
        np.savez_compressed(path, **_build(lang))
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


def score(text: str, lang: str = "en") -> float:
    """Mean quadgram log10-probability per quadgram; higher is more language-like."""
    t = to_ints(text)
    return float(quad_score(t, model(lang)["table"]) / max(len(t) - 3, 1)) if len(t) > 3 else -99.0


def detect(text: str) -> list[dict]:
    """Rank the known languages by how well the text fits, best first."""
    ranked = sorted(((score(text, c), c) for c in LANGS), reverse=True)
    return [{"lang": c, "name": LANGS[c], "score": round(s, 3)} for s, c in ranked]


def keywords(lang: str = "en", n: int = 2500, min_len: int = 3) -> list[str]:
    """Most common words of a language, for keyword-dictionary attacks."""
    return [str(w) for w in model(lang)["words"] if len(str(w)) >= min_len][:n]
