"""Insert word breaks into solved text using dictionary frequencies (Viterbi)."""
import math

from .languages import model


def segment(text: str, lang: str = "en", max_word: int = 18) -> str:
    m = model(lang)
    probs = {str(w): math.log10(float(f)) for w, f in zip(m["words"], m["word_freq"])}
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
