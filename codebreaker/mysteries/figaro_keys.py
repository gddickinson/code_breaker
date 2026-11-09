"""Apply the Le Figaro writers' documented systems to every ad, and test them on solved ads first."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher
from html import unescape

import numpy as np

from ..languages import ROOT, score
from ..segment import segment
from ..text import A, letters
from ..validation import coverage

OUT = ROOT / "data/sources/figaro"
NOW = A.replace("W", "")
VIG_KEYS = ["CEAD", "BCD", "CD", "AB", "ABC", "BC", "DE"]
MIN_LETTERS = 20


def cipher_text(lines: list[str]) -> str:
    """Letters from words that look enciphered: no digits, and no capitals after the first letter."""
    out = []
    for line in lines:
        for tok in re.split(r"[\s\-—.,;:]+", line):
            t = tok.strip("'\"()")
            if len(t) >= 2 and t.isalpha() and t[1:].islower():
                out.append(t)
    return letters("".join(out))


def shift(t, k, alpha):
    return "".join(alpha[(alpha.index(c) + k) % len(alpha)] if c in alpha else c for c in t)


def vig(t, key, alpha):
    ks = [alpha.index(c) for c in key]
    out, i = [], 0
    for c in t:
        if c in alpha:
            out.append(alpha[(alpha.index(c) - ks[i % len(ks)]) % len(alpha)])
            i += 1
        else:
            out.append(c)
    return "".join(out)


def load_tables() -> list[dict]:
    """Substitution tables, and the writers who used them, from the database's list of systems."""
    raw = (OUT / "codes.html").read_text(encoding="latin-1", errors="ignore")
    out = []
    parts = re.split(r"<tr><td>(\d+)</td><td><center>([^<]*)</center>", raw)
    for i in range(1, len(parts) - 2, 3):
        sid, name, chunk = parts[i], parts[i + 1], parts[i + 2]
        m = re.search(r"<table.*?</table>", chunk, flags=re.S | re.I)
        if not m:
            continue
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), flags=re.S | re.I)
        cells = [[unescape(re.sub(r"<[^>]+>|\s+", "", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, flags=re.S | re.I)] for r in rows]
        if len(cells) < 2 or not cells[0] or not cells[0][0].lower().startswith("chiffr"):
            continue
        mapping = {c.upper(): p.upper() for c, p in zip(cells[0][1:], cells[1][1:]) if len(c) == 1 and c.isalpha() and len(p) == 1 and p.isalpha()}
        after = re.sub(r"<[^>]+>", " ", chunk[m.end():])
        users = [u for u in unescape(after).replace("\xa0", " ").split()][1:]
        if len(mapping) >= 12:
            out.append({"id": sid, "name": unescape(name), "desc": re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", chunk[:m.start()])))[:90], "map": mapping, "users": users})
    return out


TABLES = load_tables() if (OUT / "codes.html").exists() else []


def cipher_words(lines: list[str]) -> list[str]:
    """Upper-case words from enciphered-looking tokens, keeping word boundaries."""
    out = []
    for line in lines:
        for tok in re.split(r"[\s\-\u2014.,;:]+", line):
            t = tok.strip("'\"()")
            if len(t) >= 2 and t.isalpha() and t[1:].islower():
                out.append(letters(t))
    return out


def word_systems(words: list[str]):
    """Documented systems needing word boundaries, or that remove inserted letters."""
    t = "".join(words)
    yield "mirror words", "".join(w[::-1] for w in words)
    yield "mirror words, reversed order", "".join(w[::-1] for w in reversed(words))
    yield "reversed word order", "".join(reversed(words))
    for a, b in ((1, 24), (24, 1), (2, 23), (23, 2)):
        yield f"alternate Caesar by word ({a},{b}), no W", "".join(shift(w.replace("W", "V"), a if i % 2 == 0 else b, NOW) for i, w in enumerate(words))
    yield "every second letter from first", t[0::2]
    yield "every second letter from second", t[1::2]
    yield "remove Javanais AV", re.sub(r"(?<=[^AEIOUY])AV(?=[AEIOUY])", "", t)
    yield "remove THO and RIA", t.replace("THO", "").replace("RIA", "")
    h = (len(t) + 1) // 2
    yield "two-line rail", "".join(a + b for a, b in zip(t[:h], t[h:] + " ")).replace(" ", "")
    n = len(t)
    rows = -(-n // 5)
    cols = [t[i * rows:(i + 1) * rows] for i in range(5)]
    yield "five-column read across", "".join(c[r] for r in range(rows) for c in cols if r < len(c))


def candidates(t):
    for source, x in (("", t), ("reversed, ", t[::-1])):
        for tab in TABLES:
            yield f"{source}table {tab['id']}", "".join(tab["map"].get(c, c) for c in x)
        if source:
            yield "reversed", x
        for k in range(1, 26):
            yield f"{source}Caesar {k}", shift(x, k, A)
        for k in range(1, 25):
            yield f"{source}Caesar {k}, no W", shift(x.replace("W", "V"), k, NOW)
        yield f"{source}Atbash", "".join(A[25 - A.index(c)] for c in x)
        for key in VIG_KEYS:
            yield f"{source}Vigenere {key}", vig(x, key, A)
            yield f"{source}Vigenere {key}, no W", vig(x.replace("W", "V"), key, NOW)


def best(t, words=None):
    top = (-1.0, -99.0, "", t)
    extra = list(word_systems(words)) if words else []
    for name, p in list(candidates(t)) + extra:
        if len(p) < 12:
            continue
        c = coverage(p[:400], "fr")
        s = score(p, "fr")
        if (c, s) > top[:2]:
            top = (c, s, name, p)
    return top


def job(a):
    name, lines_t, lines_r, seed = a
    picks = [x for x in (cipher_text(lines_r), cipher_text(lines_t)) if len(x) >= MIN_LETTERS]
    if not picks:
        return None
    t = max(picks, key=len)
    words = cipher_words(lines_r if cipher_text(lines_r) == t else lines_t)
    plain_cov = coverage(t[:400], "fr")
    c, s, method, p = best(t, words)
    r = random.Random(seed)
    sh = list(t)
    r.shuffle(sh)
    pos, shw = 0, []
    for w in words:
        shw.append("".join(sh[pos:pos + len(w)]))
        pos += len(w)
    null_c = best("".join(sh), shw)[0]
    sig = re.sub(r"\.jpg$", "", name.split("-", 1)[1]) if "-" in name else ""
    tab = next((x for x in TABLES if method.endswith(f"table {x['id']}")), None)
    author = bool(tab and sig and sig in tab["users"])
    return {"signature": sig, "author_match": author, "image": name, "letters": len(t), "raw": t, "plain_coverage": plain_cov, "coverage": c, "null_coverage": null_c, "score": s, "method": method, "plaintext": p, "reading": segment(p[:260], "fr")}


def run_all(raw, names):
    jobs = [(n, raw[n]["tesseract"], raw[n]["rapid"], 13 + i) for i, n in enumerate(names) if n in raw]
    with ProcessPoolExecutor(6) as ex:
        return [r for r in ex.map(job, jobs, chunksize=8) if r]


def control(raw, ads):
    known = {a["image"].replace("/", "_"): a for a in ads if a["solved"]}
    names = [p.name for p in (OUT / "control").glob("*.jpg")]
    rows = []
    for r in run_all(raw, names):
        truth = letters(re.sub(r"\([a-z]+\)\s*$|\[|\]|\?", "", known[r["image"]]["text"]))
        rows.append({"image": r["image"], "letters": r["letters"], "coverage": r["coverage"], "null": r["null_coverage"], "method": r["method"], "match": round(SequenceMatcher(None, truth, r["plaintext"]).ratio(), 3)})
    return rows


def threshold(rows):
    """Coverage needed by length, from the highest null values seen across all ads of similar length."""
    bins = {}
    for r in rows:
        bins.setdefault(min(r["letters"] // 20, 6), []).append(r["null_coverage"])
    return {b: float(np.max(v)) for b, v in bins.items()}


def run() -> dict:
    raw = json.loads((OUT / "ocr_raw.json").read_text())
    ads = json.loads((OUT / "ads.json").read_text())
    ctrl = control(raw, ads)
    unsolved = sorted({a["image"].replace("/", "_") for a in ads if not a["solved"]})
    rows = run_all(raw, unsolved)
    th = threshold(rows)
    flagged = [r for r in rows if r["coverage"] > max(th[min(r["letters"] // 20, 6)], 0.45) and r["plain_coverage"] < 0.35]
    flagged.sort(key=lambda r: -r["coverage"])
    (OUT / "keys_rows.json").write_text(json.dumps(rows, ensure_ascii=False))
    return {"id": "figaro_keys", "tested": len(rows), "plain_ads": sum(r["plain_coverage"] >= 0.35 for r in rows), "thresholds": th, "control_ads": len(ctrl), "control_recovered": sum(r["match"] >= 0.6 for r in ctrl), "control_rows": sorted(ctrl, key=lambda r: -r["match"])[:12], "flagged": flagged}
