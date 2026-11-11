"""Ads whose cipher mixes letters and digits: digits stand for letters, on top of a letter system."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor

from ..languages import ROOT, corpus_text, score
from ..segment import segment
from ..text import A, letters
from ..validation import coverage
from .figaro_fusion import SYSTEMS
from .figaro_keys import OUT
from ..third_party import need

RESULT = ROOT / "data/results/figaro_digits.json"
COMMON = set(re.findall(r"[a-z]+", corpus_text("fr").lower()))
VALUES = "EAISTNRUOLDCMP"


def tokens(line: str) -> list[str]:
    """Cipher-looking words: those with both letters and digits, or letters that are not French."""
    out = []
    for t in re.split(r"[\s.,;:\-'\"()!]+", line):
        low = t.lower()
        if not re.fullmatch(r"[a-z0-9]+", low) or len(low) < 2:
            continue
        if re.search(r"\d", low):
            if re.search(r"[a-z]", low):
                out.append(low.upper())
        elif low not in COMMON:
            out.append(low.upper())
    return out


def pick(lines: list[str]) -> str:
    """The longest cipher word sequence, requiring digit-bearing words."""
    best = ""
    for line_set in lines:
        toks = [t for l in line_set for t in tokens(l)]
        text = " ".join(toks)
        if sum(c.isdigit() for c in text) >= 4 and len(text.replace(" ", "")) > len(best.replace(" ", "")):
            best = text
    return best


def apply(text: str, dec, digits: dict) -> str:
    return "".join(digits[c] if c.isdigit() else dec(i, c) for i, c in enumerate(text))


def solve(words: str, seed: int = 1) -> tuple:
    """Rank letter systems on digit-free runs, then fit the digits by coordinate ascent."""
    flat, rnd = words.replace(" ", ""), random.Random(seed)
    ds = sorted({c for c in flat if c.isdigit()})
    def blank(dec):
        return "".join(dec(i, c) for i, c in enumerate(flat) if c.isalpha())
    ranked = sorted([("identity", lambda i, c: c)] + SYSTEMS, key=lambda s: -score(blank(s[1]), "fr"))[:8]
    best = (-1.0, -99.0, "", "")
    for name, dec in ranked:
        for r in range(3):
            key = {d: rnd.choice(VALUES) for d in ds}
            cur = score(apply(flat, dec, key), "fr")
            for _ in range(3):
                for d in ds:
                    for v in A:
                        o = key[d]
                        key[d] = v
                        s = score(apply(flat, dec, key), "fr")
                        if s > cur:
                            cur = s
                        else:
                            key[d] = o
            p = apply(flat, dec, key)
            c = coverage(p, "fr")
            if (c, cur) > best[:2]:
                best = (c, cur, name, p, dict(key))
    return best


def plant(rnd: random.Random, text: str, n: int = 90) -> tuple[str, str]:
    """French text with a Caesar shift and the commonest letters written as digits."""
    i = rnd.randrange(len(text) - n)
    p = text[i:i + n]
    k, digs = rnd.randrange(26), dict(zip(rnd.sample("EAISTN", 5), rnd.sample("0123456789", 5)))
    out, run = [], 0
    for c in p:
        out.append(digs.get(c, A[(A.index(c) - k) % 26]))
        run += 1
        if run == 5:
            out.append(" ")
            run = 0
    return "".join(out).strip(), p


def _ctl(a):
    words, truth = a
    p = solve(words)[3]
    return sum(x == y for x, y in zip(p, truth)) / len(truth)


def _ad(a):
    name, words, seed = a
    c, s, method, p, key = solve(words)
    sh = list(words.replace(" ", ""))
    random.Random(seed).shuffle(sh)
    it = iter(sh)
    nullw = "".join(" " if ch == " " else next(it) for ch in words)
    return {"image": name, "text": words, "coverage": c, "null": solve(nullw)[0], "score": s, "method": method, "key": key, "plain": p, "reading": segment(p.lower(), "fr")}


def run() -> dict:
    text, rnd = letters(corpus_text("fr")), random.Random(6)
    planted = [plant(rnd, text) for _ in range(40)]
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    ads = json.loads(need(OUT / "ads.json").read_text())
    unsolved = {a["image"].replace("/", "_") for a in ads if not a["solved"]}
    jobs = []
    for i, n in enumerate(sorted(unsolved)):
        w = pick([e for src in (otsu, raw) for e in src.get(n, {}).values()])
        if len(w.replace(" ", "")) >= 25:
            jobs.append((n, w, 200 + i))
    with ProcessPoolExecutor(7) as ex:
        acc = list(ex.map(_ctl, planted, chunksize=2))
        rows = list(ex.map(_ad, jobs, chunksize=4))
    rows.sort(key=lambda r: -r["coverage"])
    return {"id": "figaro_digits", "control_accuracy": round(sum(acc) / len(acc), 3), "control_solved": sum(a >= 0.7 for a in acc), "control_n": len(acc), "tested": len(rows), "null_max": max((r["null"] for r in rows), default=0), "rows": rows}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print({k: v for k, v in out.items() if k != "rows"})
    for r in out["rows"][:12]:
        print(r["image"], round(r["coverage"], 2), r["null"], r["method"], r["reading"][:90], "<<", r["text"][:60])
