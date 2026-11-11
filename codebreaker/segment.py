"""Insert word breaks into solved text using dictionary frequencies (Viterbi)."""
import math
from functools import lru_cache

from .languages import model


@lru_cache(maxsize=None)
def _probs(lang: str) -> dict:
    m = model(lang)
    return {str(w): math.log10(float(f)) for w, f in zip(m["words"], m["word_freq"])}


def segment(text: str, lang: str = "en", max_word: int = 18) -> str:
    return viterbi(text, _probs(lang), max_word)


def viterbi(text: str, probs: dict, max_word: int = 18) -> str:
    """Most probable split into words, given log10 word probabilities (unknown words cost by length)."""
    n = len(text)
    best = [0.0] + [-1e18] * n
    back = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(max(0, i - max_word), i):
            w = text[j:i]
            p = probs.get(w, -7.0 - 1.5 * len(w))
            if best[j] + p > best[i]:
                best[i], back[i] = best[j] + p, j
    out, i = [], n
    while i > 0:
        out.append(text[back[i]:i])
        i = back[i]
    return " ".join(reversed(out))


def word_score(text: str, lang: str = "en", max_word: int = 18) -> float:
    """Best-segmentation log-probability per letter: rewards text that splits into common words."""
    probs = _probs(lang)
    n = len(text)
    best = [0.0] + [-1e18] * n
    for i in range(1, n + 1):
        for j in range(max(0, i - max_word), i):
            w = text[j:i]
            p = probs.get(w, -7.0 - 1.5 * len(w))
            if best[j] + p > best[i]:
                best[i] = best[j] + p
    return best[n] / max(n, 1)
