"""Columnar transposition helpers shared by transposition and fractionating ciphers."""
from ..text import letters


def order(key: str) -> list[int]:
    """Column read order: alphabetical by key letter, ties left to right."""
    k = letters(key)
    return sorted(range(len(k)), key=lambda i: (k[i], i))


def col_encrypt(text: str, key: str) -> str:
    o = order(key)
    return "".join(text[c::len(o)] for c in o)


def col_decrypt(text: str, key: str) -> str:
    o, n = order(key), len(text)
    k = len(o)
    rows, extra = n // k, n % k
    grid: list = [None] * n
    pos = 0
    for c in o:
        h = rows + (c < extra)
        grid[c::k] = text[pos:pos + h]
        pos += h
    return "".join(grid)
