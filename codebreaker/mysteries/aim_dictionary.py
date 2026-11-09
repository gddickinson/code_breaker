"""The AIM ads: a dictionary code on Landais' Petit dictionnaire, tested on solved ads before unsolved ones."""
import json
import random
import re
import unicodedata
from difflib import SequenceMatcher

from ..languages import ROOT

SOURCE = ROOT / "data/sources/aim"
CONTROL = ROOT / "data/mysteries/aim_controls.json"
RESULT = ROOT / "data/results/aim_dictionary.json"
LEAF_OFFSET = 13
TOLERANCE = 3
HEAD = re.compile(r"^[^A-Za-zÀ-ÿ]{0,3}([A-ZÀ-Þ][a-zà-ÿ'\-]+)\b")


def plain(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c) and c.isalpha())


def pages() -> list:
    return json.loads((SOURCE / "pages.json").read_text())


def columns(leaf: list) -> dict:
    """Headwords of each column in reading order. OCR misses some, so positions are approximate."""
    if not leaf:
        return {"L": [], "R": []}
    width, out = max(l[0] for l in leaf) + 300, {"L": [], "R": []}
    top = min(l[1] for l in leaf)
    for x, y, text in sorted(leaf, key=lambda l: l[1]):
        m = HEAD.match(text)
        if y - top < 60 or not m or len(m.group(1)) < 2:
            continue
        out["L" if x < width * 0.42 else "R"].append(m.group(1))
    return out


def similar(word: str, target: str) -> bool:
    a, b = plain(word), plain(target)
    if len(b) <= 3:
        return a == b
    n = min(len(b), 6)
    return SequenceMatcher(None, a[:n], b[:n]).ratio() >= 0.75


def near(cols: dict, side: str, n: int, target: str, tol: int = TOLERANCE) -> bool:
    words = cols.get(side, [])
    return any(similar(w, target) for w in words[max(0, n - 1 - tol):n + tol])


def index() -> dict:
    return {p - LEAF_OFFSET: columns(leaf) for p, leaf in enumerate(pages())}


def control(idx: dict, pairs: list, trials: int = 300, seed: int = 4) -> dict:
    """Do the published words sit at their references, compared with random references?"""
    rnd = random.Random(seed)
    hits = [near(idx.get(p, {}), s, n, w) for p, s, n, w in pairs]
    known = [k for k in idx if 8 <= k <= 590]
    null = []
    for _ in range(trials):
        c = 0
        for _, s, n, w in pairs:
            c += near(idx[rnd.choice(known)], s, n, w)
        null.append(c)
    return {"pairs": len(pairs), "hits": sum(hits), "misses": [pairs[i] for i, h in enumerate(hits) if not h], "null_mean": round(sum(null) / trials, 2), "null_max": max(null)}


def lookup(idx: dict, refs: list, tol: int = 2) -> list:
    out = []
    for p, s, n, _ in refs:
        words = idx.get(p, {}).get(s, [])
        out.append({"ref": f"{p}{'a' if s == 'R' else ''}.{n}", "candidates": words[max(0, n - 1 - tol):n + tol], "entries_on_column": len(words)})
    return out


def run() -> dict:
    data, idx = json.loads(CONTROL.read_text()), index()
    return {"id": "aim_dictionary", "control": control(idx, data["pairs"]), "unsolved": {k: {"context": data["unsolved_context"][k], "words": lookup(idx, v)} for k, v in data["unsolved"].items()}}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(out["control"])
    for k, v in out["unsolved"].items():
        print(k, v["context"])
        for w in v["words"]:
            print(" ", w["ref"], w["candidates"], w["entries_on_column"])
