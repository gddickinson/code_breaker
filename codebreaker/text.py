"""Text normalisation and letter/integer conversion shared by every module."""
import unicodedata

import numpy as np

A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_SPECIAL = str.maketrans({"ß": "SS", "Æ": "AE", "æ": "AE", "Œ": "OE", "œ": "OE",
                           "Ø": "O", "ø": "o", "Ł": "L", "ł": "l", "Đ": "D", "đ": "d", "ı": "i", "Þ": "TH", "þ": "th", "Ð": "D", "ð": "d"})


def strip_accents(text: str) -> str:
    text = text.translate(_SPECIAL)
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def letters(text: str) -> str:
    """Upper-case A-Z only, with accents folded onto their base letters."""
    return "".join(c for c in strip_accents(text).upper() if "A" <= c <= "Z")


def to_ints(text: str) -> np.ndarray:
    return np.frombuffer(letters(text).encode(), dtype=np.uint8).astype(np.int32) - 65


def to_text(ints) -> str:
    return "".join(A[int(i)] for i in ints)


def keyed_alphabet(keyword: str, alphabet: str = A) -> str:
    """Keyword letters (first occurrence only) followed by the rest of the alphabet."""
    out = []
    for c in letters(keyword) + alphabet:
        if c in alphabet and c not in out:
            out.append(c)
    return "".join(out)


def similarity(a: str, b: str) -> float:
    """Fraction of positions that agree, over the length of the longer string."""
    if not a and not b:
        return 1.0
    return sum(x == y for x, y in zip(a, b)) / max(len(a), len(b))
