"""Vigenere-family attacks on every letter-only unsolved text, forwards and reversed, with controls."""
import random
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from .. import leads as L
from ..attacks.classical import periodic
from ..ciphers.polyalphabetic import beau_int, porta_int, var_int, vig_int
from ..languages import LANGS, score
from ..segment import segment
from ..text import similarity, to_ints, to_text
from ..validation import coverage, sample_plaintext
from .corpus import load

SYSTEMS = {"Vigenere": vig_int, "Beaufort": beau_int, "Variant": var_int, "Porta": porta_int}


def best_periodic(text, lang):
    top = None
    for name, fn in SYSTEMS.items():
        r = periodic(text, fn, lang, max_period=20)
        if top is None or r["score"] > top["score"]:
            top = {**r, "system": name}
    return top


def control(n, lang, seed):
    r = random.Random(seed)
    plain = sample_plaintext(n, lang, seed)
    key = to_ints("".join(r.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(r.randint(3, 7))))
    return similarity(plain, best_periodic(to_text(var_int(to_ints(plain), key)), lang)["plaintext"])


def attempt(a):
    slug, name, path = a
    seq = load(slug, path)
    if len(seq) < 40 or not all(len(x) == 1 and "A" <= x.upper() <= "Z" for x in seq):
        return None
    text = "".join(seq).upper()
    r = random.Random(1)
    rows = []
    for direction, t in (("forward", text), ("reversed", text[::-1])):
        for lang in LANGS:
            b = best_periodic(t, lang)
            s = list(t)
            nulls = []
            for _ in range(5):
                r.shuffle(s)
                nulls.append(best_periodic("".join(s), lang)["score"])
            z = (b["score"] - float(np.mean(nulls))) / (float(np.std(nulls, ddof=1)) + 1e-9)
            rows.append({"direction": direction, "language": LANGS[lang], "code": lang, "system": b["system"], "key": b["key"]["key"], "score": b["score"], "z": round(z, 2), "plaintext": b["plaintext"]})
    top = max(rows, key=lambda x: (coverage(x["plaintext"][:400], x["code"]), x["score"]))
    cov = coverage(top["plaintext"][:400], top["code"])
    ctrl = round(float(np.mean([control(len(text), top["code"], s) for s in range(3)])), 3)
    return {"slug": slug, "name": name, "length": len(text), "direction": top["direction"], "language": top["language"], "system": top["system"], "key": top["key"], "z": top["z"], "score": top["score"], "coverage": cov, "control": ctrl, "reading": segment(top["plaintext"][:200], top["code"]), "readable": bool(cov >= 0.6 and ctrl >= 0.7)}


def run() -> dict:
    db = L.connect()
    codes = [(r["slug"], r["name"], r["data_path"]) for r in db.execute("SELECT slug,name,data_path FROM codes WHERE data_path IS NOT NULL AND data_path NOT LIKE 'data/results%'")]
    with ProcessPoolExecutor(6) as ex:
        rows = [r for r in ex.map(attempt, codes) if r]
    rows.sort(key=lambda r: -r["coverage"])
    return {"id": "polyalpha_sweep", "tested": len(rows), "rows": rows, "readable": [r for r in rows if r["readable"]]}
