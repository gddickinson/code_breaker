"""One key shared by many letter-digit ads: fit on half, test on the rest, and try the documented digit tables."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from html import unescape

import numpy as np

from ..languages import ROOT
from ..text import A
from .figaro_digit_words import HAND, SYM, letters_lower, planted, qualifies, shuffled, solve, vocabulary
from .figaro_digits import pick
from .figaro_keys import OUT
from ..third_party import need

RESULT = ROOT / "data/results/figaro_digit_family.json"
MEMBER = 0.7


@lru_cache(maxsize=1)
def words() -> frozenset:
    return frozenset("".join(A[x] for x in row) for m, _ in vocabulary().values() for row in m)


def apply(text: str, key: dict) -> list[str]:
    return ["".join(key.get(c, ".") for c in w) for w in text.split()]


def read_share(text: str, key: dict) -> float:
    w, out = words(), apply(text, key)
    n = sum(map(len, out))
    return sum(len(x) for x in out if x in w) / n if n else 0.0


def _total(texts: list[str], key: dict) -> int:
    w = words()
    return sum(len(x) for t in texts for x in apply(t, key) if x in w)


def fit(seed: dict, ads: list[str], rounds: int = 4) -> tuple[dict, list[str]]:
    """Grow the family and refine the key by coordinate ascent on dictionary letters read."""
    key, fam = dict(seed), []
    for _ in range(rounds):
        fam = [t for t in ads if read_share(t, key) >= 0.6]
        if not fam:
            break
        for s in SYM:
            best, val, old = _total(fam, key), key.get(s), key.get(s)
            for l in A:
                key[s] = l
                v = _total(fam, key)
                if v > best:
                    best, val = v, l
            if val is None:
                key.pop(s, None)
            else:
                key[s] = val
    return key, fam


def seed_key(text: str) -> dict:
    r = solve(text)
    key = {}
    for w, p in zip(text.split(), r["words"]):
        for c, l in zip(w, p):
            if l != ".":
                key[c] = l
    return key


def heldout(seed: dict, ads: list[str], rnd: random.Random) -> dict:
    """Fit on one half; count members in the other half, against the same ads shuffled."""
    order = ads[:]
    rnd.shuffle(order)
    train, test = order[::2], order[1::2]
    key, fam = fit(seed, train)
    real = [read_share(t, key) for t in test]
    null = [read_share(shuffled(t, rnd), key) for t in test]
    return {"train": len(train), "family_in_train": len(fam), "test": len(test), "members": sum(v >= MEMBER for v in real), "null_members": sum(v >= MEMBER for v in null), "null_max": round(max(null, default=0), 3)}


def planted_control(rnd: random.Random) -> dict:
    """Twenty ads under one key among sixty under others: is the family found out of sample?"""
    corp = re.findall(r"[a-z]+", letters_lower())
    table = dict(zip(A, rnd.sample(A, 26)))
    table.update(zip(rnd.sample("EAISTN", 5), rnd.sample("0123456789", 5)))
    def member(n):
        i, run = rnd.randrange(len(corp) - 200), []
        while sum(map(len, run)) < n:
            run.append(corp[i])
            i += 1
        return "".join(table.get(c, c) for c in " ".join(run).upper())
    fam = [member(35) for _ in range(20)]
    decoys = [planted(rnd, corp, 35)[0] for _ in range(60)]
    seed = seed_key(member(70))
    res = heldout(seed, fam + decoys, rnd)
    key, _ = fit(seed, fam + decoys)
    right = sum(key.get(table.get(c)) == c for c in A if table.get(c) in key)
    return {**res, "family_total": 20, "key_correct": right, "key_size": len(key)}


def digit_tables() -> list[dict]:
    """The writers' tables with digit symbols, which the letter-only parser skipped."""
    raw = need(OUT / "codes.html").read_text(encoding="latin-1", errors="ignore")
    parts = re.split(r"<tr><td>(\d+)</td><td><center>([^<]*)</center>", raw)
    out = []
    for i in range(1, len(parts) - 2, 3):
        m = re.search(r"<table.*?</table>", parts[i + 2], flags=re.S | re.I)
        if not m:
            continue
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), flags=re.S | re.I)
        cells = [[unescape(re.sub(r"<[^>]+>|\s+", "", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, flags=re.S | re.I)] for r in rows]
        if len(cells) < 2 or not re.search(r"\d", "".join(cells[0][1:])):
            continue
        key = {c.upper(): p[0].upper() for c, p in zip(cells[0][1:], cells[1][1:]) if len(c) == 1 and c.isalnum() and p and p[0].isalpha()}
        if len(key) >= 8:
            users = unescape(re.sub(r"<[^>]+>", " ", parts[i + 2][m.end():])).replace("\xa0", " ").split()[1:8]
            out.append({"id": parts[i], "name": unescape(parts[i + 1]), "key": key, "users": users})
    return out


def _qual():
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    ads = json.loads(need(OUT / "ads.json").read_text())
    names = sorted({a["image"].replace("/", "_") for a in ads if not a["solved"]})
    return {n: w for n in names if qualifies(w := pick([e for src in (otsu, raw) for e in src.get(n, {}).values()]))}


def run() -> dict:
    rnd = random.Random(31)
    control = [planted_control(random.Random(40 + i)) for i in range(6)]
    hand = json.loads(HAND.read_text())
    ads = _qual()
    seed = seed_key(hand["1883_18830605-7.jpg"]["words"])
    splits = [heldout(seed, [v for k, v in ads.items() if k != "1883_18830605-7.jpg"], random.Random(70 + i)) for i in range(5)]
    key, fam = fit(seed, list(ads.values()))
    rows = []
    for n, t in ads.items():
        v = read_share(t, key)
        if v >= MEMBER:
            rows.append({"image": n, "text": t, "read": round(v, 3), "null": round(read_share(shuffled(t, rnd), key), 3), "words": apply(t, key)})
    rows.sort(key=lambda r: r["image"])
    tables = []
    for tab in digit_tables():
        for n, t in ads.items():
            v, nv = read_share(t, tab["key"]), read_share(shuffled(t, rnd), tab["key"])
            if v >= 0.6:
                sig = n.rsplit("-", 1)[-1].replace(".jpg", "") if "-" in n else ""
                tables.append({"table": tab["id"], "name": tab["name"], "image": n, "read": round(v, 3), "null": round(nv, 3), "author": sig in tab["users"], "words": apply(t, tab["key"])})
    tables.sort(key=lambda r: -r["read"])
    return {"id": "figaro_digit_family", "planted": control, "heldout": splits, "tested": len(ads), "key": dict(sorted(key.items())), "members": rows, "digit_tables": tables, "n_tables": len(digit_tables())}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(out["planted"]); print(out["heldout"]); print(out["tested"], len(out["members"]), out["key"], out["n_tables"])
    for r in out["members"]:
        print(r["image"], r["read"], r["null"], " ".join(r["words"])[:120])
    for r in out["digit_tables"][:12]:
        print("T", r["table"], r["name"], r["image"], r["read"], r["null"], r["author"], " ".join(r["words"])[:90])
