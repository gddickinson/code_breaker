"""Forensic views of any file: entropy by region, printable strings, and signatures of files embedded inside it."""
import math
import re
from collections import Counter

from .file_inspector import _MAGIC

MIN_SIG = 4


def entropy(b: bytes) -> float:
    n = len(b)
    return -sum(c / n * math.log2(c / n) for c in Counter(b).values()) if n else 0.0


def entropy_map(data: bytes, blocks: int = 128) -> list[float]:
    """Entropy of equal slices: flat high regions are compressed or encrypted, low ones padding or text."""
    size = max(256, len(data) // blocks)
    return [round(entropy(data[i:i + size]), 3) for i in range(0, len(data), size)][:blocks]


def strings(data: bytes, min_len: int = 6, limit: int = 300) -> list[dict]:
    out = []
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data):
        out.append({"offset": m.start(), "text": m.group().decode("ascii")[:200]})
        if len(out) >= limit:
            break
    return out


ZIP_FAMILY = {"zip", "zip-empty", "npz", "jar", "whl", "apk", "docx", "xlsx", "pptx", "epub", "odt", "ods"}


def embedded(data: bytes, own_kind: str = "", limit: int = 60) -> list[dict]:
    """Known file signatures found anywhere after the start, as a tool like binwalk would.

    A ZIP repeats its own header for every member, so those are not reported inside a ZIP-family file."""
    found = []
    for offset, sig, kind, desc in _MAGIC:
        if offset != 0 or len(sig) < MIN_SIG or (own_kind in ZIP_FAMILY and kind in ZIP_FAMILY):
            continue
        start = 1
        while len(found) < limit:
            i = data.find(sig, start)
            if i < 0:
                break
            found.append({"offset": i, "kind": kind, "description": desc})
            start = i + 1
    return sorted(found, key=lambda x: x["offset"])[:limit]
