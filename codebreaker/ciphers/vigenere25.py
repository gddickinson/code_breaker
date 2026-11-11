"""Vigenere over a 25-letter alphabet without W (Round 87).

French writers often used an alphabet without W, which their language hardly needed: the Le Figaro personal-column
writers C. H. (key CEAD, 44 solved ads), 234 (BCD) and 54 (CD) all did, as Didier Muller's database documents. The
shifts then run modulo 25, so a 26-letter Vigenere attack cannot read them at all (Round 87 benchmark: 0 of 22). W in
a plaintext is written as V. The attack is the usual one: period by index of coincidence, then each key letter by
fitting the column and improving the whole by quadgram score."""
import numpy as np

from ..attacks import classical as X
from ..text import A, letters
from .base import Param, add

NOW = "ABCDEFGHIJKLMNOPQRSTUVXYZ"
IDX = np.array([NOW.index(c if c != "W" else "V") for c in A])   # 26-letter index -> 25-letter index
BACK = np.array([A.index(c) for c in NOW])                        # 25-letter index -> 26-letter index


def dec25(t, key):
    k = np.resize(np.asarray(key) % 25, len(t))
    return BACK[(IDX[t] - k) % 25]


def _keyints(key: str) -> list[int]:
    return [NOW.index(c if c != "W" else "V") for c in letters(key)]


def encrypt(text: str, key: str = "CEAD") -> str:
    t, k = letters(text).replace("W", "V"), _keyints(key)
    return "".join(NOW[(NOW.index(c) + k[i % len(k)]) % 25] for i, c in enumerate(t))


def decrypt(text: str, key: str = "CEAD") -> str:
    t, k = letters(text).replace("W", "V"), _keyints(key)
    return "".join(NOW[(NOW.index(c) - k[i % len(k)]) % 25] for i, c in enumerate(t))


def attack(ct: str, lang: str = "en") -> dict:
    cap = max(2, min(24, len(letters(ct)) // 6))  # at least six letters a column, or short ads overfit long periods
    r = X.periodic(ct, dec25, lang, 25, max_period=cap, method="period from IC, then column search over 25 letters (no W)")
    k = r.get("key") or {}
    if isinstance(k, dict) and k.get("key"):  # the shared attack spells key indices in A-Z; respell them in the 25 letters
        r["key"] = {**k, "key": "".join(NOW[A.index(c) % 25] for c in k["key"])}
    return r


add(id="vigenere25", name="Vigenere without W (25 letters)", family="Polyalphabetic", era="French practice, 19th century; Le Figaro ads 1883-1893",
    summary="Vigenere on an alphabet of 25 letters with no W, so every shift runs modulo 25.",
    how="As Vigenere, but the alphabet is ABCDEFGHIJKLMNOPQRSTUVXYZ. The Le Figaro writer C. H. used the key CEAD for years.",
    weakness="Exactly Vigenere's: a repeating key. But a 26-letter attack fails on it, so the alphabet must be tried too.",
    encrypt=encrypt, decrypt=decrypt, key={"key": "CEAD"}, example="Veux vous voir, beaucoup a vous dire", params=[Param("key", "Keyword")],
    attack=attack, attack_name="Find the period with index of coincidence, then fit each column over 25 letters",
    keygen=lambda r: {"key": "".join(r.choice(NOW) for _ in range(r.randint(3, 7)))})
