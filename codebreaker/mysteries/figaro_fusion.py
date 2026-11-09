"""Fuse several OCR readings of an ad, then let a French letter HMM pick between their disagreements."""
import json
import math
import random
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher
from functools import lru_cache

import numpy as np

from ..languages import ROOT, corpus_text, score
from ..text import A, letters
from ..validation import coverage
from .figaro_keys import MIN_LETTERS, NOW, OUT, TABLES, VIG_KEYS, cipher_text, threshold

RESULT = ROOT / "data/results/figaro_fusion.json"
EPS = 0.15


@lru_cache(maxsize=1)
def bigrams() -> np.ndarray:
    t = letters(corpus_text("fr"))
    m = np.ones((26, 26))
    for a, b in zip(t, t[1:]):
        m[A.index(a), A.index(b)] += 1
    return np.log(m / m.sum(axis=1, keepdims=True))


def slots(texts: list[str]) -> list[Counter]:
    """A confusion network: votes per position, aligned to the longest reading."""
    ref = max(texts, key=len)
    out = [Counter({c: 1}) for c in ref]
    used = False
    for t in texts:
        if t is ref and not used:
            used = True
            continue
        sm = SequenceMatcher(None, ref, t, autojunk=False)
        if sm.ratio() < 0.5:
            continue
        for tag, a, b, c, d in sm.get_opcodes():
            if tag in ("equal", "replace") and b - a == d - c:
                for i, j in zip(range(a, b), range(c, d)):
                    out[i][t[j]] += 1
    return out


def systems():
    """Per-letter decryptions, as functions of position and ciphertext letter."""
    for tab in TABLES:
        yield f"table {tab['id']}", (lambda m: lambda i, c: m.get(c, c))(tab["map"])
    for k in range(1, 26):
        yield f"Caesar {k}", (lambda k: lambda i, c: A[(A.index(c) + k) % 26])(k)
    for k in range(1, 25):
        yield f"Caesar {k}, no W", (lambda k: lambda i, c: NOW[(NOW.index("V" if c == "W" else c) + k) % 25])(k)
    yield "Atbash", lambda i, c: A[25 - A.index(c)]
    for key in VIG_KEYS:
        yield f"Vigenere {key}", (lambda ks: lambda i, c: A[(A.index(c) - ks[i % len(ks)]) % 26])([A.index(x) for x in key])
        yield f"Vigenere {key}, no W", (lambda ks: lambda i, c: NOW[(NOW.index("V" if c == "W" else c) - ks[i % len(ks)]) % 25])([NOW.index(x) for x in key])


SYSTEMS = list(systems())


def viterbi(sl: list[Counter], dec, trans: np.ndarray, weight: float = 1.0) -> tuple[float, str]:
    """Best plaintext through the alternatives: OCR votes as emissions, French bigrams as transitions."""
    prev, back = {}, []
    for i, votes in enumerate(sl):
        n = sum(votes.values())
        cur, ptr = {}, {}
        for c, v in votes.items():
            p = A.index(dec(i, c))
            e = weight * math.log((v + EPS) / (n + EPS * len(votes)))
            if not prev:
                val, frm = e, None
            else:
                frm = max(prev, key=lambda q: prev[q] + trans[q, p])
                val = prev[frm] + trans[frm, p] + e
            if p not in cur or val > cur[p]:
                cur[p], ptr[p] = val, frm
        prev = cur
        back.append(ptr)
    p = max(prev, key=prev.get)
    ll, out = prev[p], []
    for ptr in reversed(back):
        out.append(p)
        p = ptr[p]
    return ll / len(sl), "".join(A[x] for x in reversed(out))


def majority(sl: list[Counter], dec) -> str:
    return "".join(dec(i, v.most_common(1)[0][0]) for i, v in enumerate(sl))


def best(sl: list[Counter], mode: str = "hmm") -> tuple:
    trans, tops = bigrams(), []
    for source, s in (("", sl), ("reversed, ", sl[::-1])):
        for name, dec in SYSTEMS:
            if mode == "hmm":
                ll, p = viterbi(s, dec, trans)
            else:
                p = majority(s, dec)
                ll = float(sum(trans[A.index(a), A.index(b)] for a, b in zip(p, p[1:]))) / len(p)
            tops.append((ll, source + name, p))
    tops.sort(key=lambda x: -x[0])
    return max(((coverage(p[:400], "fr"), score(p, "fr"), n, p) for _, n, p in tops[:12]), key=lambda x: x[:2])


def readings(name: str, sources: list[dict]) -> list[str]:
    out = []
    for src in sources:
        for eng in src.get(name, {}).values():
            t = cipher_text(eng)
            if len(t) >= MIN_LETTERS:
                out.append(t)
    return out


def job(a):
    name, texts, seed, mode = a
    sl = slots(texts)
    c, s, method, p = best(sl, mode)
    sh = list(sl)
    random.Random(seed).shuffle(sh)
    return {"image": name, "letters": len(sl), "readings": len(texts), "plain_coverage": coverage("".join(v.most_common(1)[0][0] for v in sl)[:400], "fr"), "coverage": c, "null_coverage": best(sh, mode)[0], "score": s, "method": method, "plaintext": p}


def run_names(names, sources, mode):
    jobs = [(n, t, 97 + i, mode) for i, n in enumerate(names) if (t := readings(n, sources))]
    with ProcessPoolExecutor(7) as ex:
        return list(ex.map(job, jobs, chunksize=6))


def control(sources, ads, mode):
    known = {a["image"].replace("/", "_"): a for a in ads if a["solved"]}
    rows = run_names([p.name for p in (OUT / "control").glob("*.jpg")], sources, mode)
    for r in rows:
        truth = letters(re.sub(r"\([a-z]+\)\s*$|\[|\]|\?", "", known[r["image"]]["text"]))
        r["match"] = round(SequenceMatcher(None, truth, r["plaintext"]).ratio(), 3)
    return rows


def run() -> dict:
    sources = [json.loads((OUT / f).read_text()) for f in ("ocr_raw.json", "ocr_otsu.json")]
    ads = json.loads((OUT / "ads.json").read_text())
    ctrl = {m: control(sources, ads, m) for m in ("majority", "hmm")}
    counts = {m: sum(r["match"] >= 0.6 for r in v) for m, v in ctrl.items()}
    mode = max(counts, key=lambda m: (counts[m], m == "majority"))
    rows = run_names(sorted({a["image"].replace("/", "_") for a in ads if not a["solved"]}), sources, mode)
    th = threshold(rows)
    flagged = [r for r in rows if r["coverage"] > max(th[min(r["letters"] // 20, 6)], 0.45) and r["plain_coverage"] < 0.35]
    flagged.sort(key=lambda r: -r["coverage"])
    return {"id": "figaro_fusion", "baseline_recovered": 16, "control_ads": len(ctrl["hmm"]), "control": counts, "chosen": mode, "tested": len(rows), "thresholds": th, "flagged": flagged}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(out["control"], out["control_ads"], out["chosen"], out["tested"], len(out["flagged"]))
