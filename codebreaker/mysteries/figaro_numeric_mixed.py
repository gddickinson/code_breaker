"""Ads that mix table numbers with letters printed in clear; only the numbers are shuffled for the null."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor

from ..languages import ROOT, corpus_text
from ..segment import segment
from ..text import letters
from ..validation import coverage
from .figaro_digit_sweep import numeric_tables, signature
from .figaro_keys import OUT

RESULT = ROOT / "data/results/figaro_numeric_mixed.json"
MIN_NUMBERS = 8
PIECE = re.compile(r"\d+|[A-Za-z]")


def pieces(lines: list[str]) -> list[str]:
    return PIECE.findall(" ".join(lines))


def decode(ps: list[str], key: dict) -> str:
    """Numbers through the table, clear letters as printed, numbers missing from the table dropped."""
    return "".join((key.get(str(int(p)), "") if p.isdigit() else p.upper()) for p in ps)


def shuffle_numbers(ps: list[str], rnd: random.Random) -> list[str]:
    nums = [p for p in ps if p.isdigit()]
    rnd.shuffle(nums)
    it = iter(nums)
    return [next(it) if p.isdigit() else p for p in ps]


def decoded_share(ps: list[str], key: dict) -> float:
    nums = [p for p in ps if p.isdigit()]
    return sum(str(int(p)) in key for p in nums) / len(nums) if nums else 0.0


def assess(ps: list[str], key: dict, seed: int, trials: int = 8) -> dict:
    """Coverage against the mean and highest of several shuffles of the numbers alone."""
    rnd = random.Random(seed)
    text = decode(ps, key)
    nulls = [coverage(decode(shuffle_numbers(ps, rnd), key), "fr") for _ in range(trials)]
    return {"read": round(coverage(text, "fr"), 3), "null_mean": round(sum(nulls) / trials, 3), "null_max": round(max(nulls), 3), "plain": text}


def plant(rnd: random.Random, words: list[str], key: dict, n: int = 14, clear: float = 0.12) -> list[str]:
    """French words written through a numeric table, with some letters left in clear."""
    inverse = {}
    for k, v in key.items():
        inverse.setdefault(v, k)
    i, out = rnd.randrange(len(words) - 50), []
    for w in words[i:i + n]:
        for c in w.upper():
            out.append(c if c not in inverse or rnd.random() < clear else inverse[c])
    return out


def _job(a):
    name, sets, seed, tables = a
    best = None
    for lines in sets:
        ps = pieces(lines)
        if sum(p.isdigit() for p in ps) < MIN_NUMBERS:
            continue
        for t in tables:
            if decoded_share(ps, t["key"]) < 0.8:
                continue
            quick = coverage(decode(ps, t["key"]), "fr")
            if best is not None and quick <= best["read"]:
                continue
            res = assess(ps, t["key"], seed)
            if res["read"] - res["null_max"] > (best["read"] - best["null_max"] if best else -1):
                best = {"image": name, "table": t["id"], "name": t["name"], "author": signature(name) in t["users"], **res}
    if best:
        best["reading"] = segment(best["plain"].lower(), "fr")
    return best


def control(tables: list[dict]) -> dict:
    rnd, words, hits, nulls, n = random.Random(12), [w for w in letters(corpus_text("fr")).split()] or [], 0, 0, 40
    corp = re.findall(r"[a-zà-ÿ]+", corpus_text("fr").lower())
    corp = [letters(w).lower() for w in corp if letters(w)]
    usable = [t for t in tables if len(set(t["key"].values())) >= 18]
    for i in range(n):
        t = rnd.choice(usable)
        ps = plant(rnd, corp, t["key"])
        r = assess(ps, t["key"], i)
        hits += r["read"] - r["null_max"] >= 0.2
        junk = [str(rnd.choice(list(t["key"]))) if p.isdigit() else p for p in ps]
        q = assess(junk, t["key"], i + 500)
        nulls += q["read"] - q["null_max"] >= 0.2
    return {"planted": n, "detected": hits, "false_on_junk": nulls}


def run() -> dict:
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    ads = json.loads((OUT / "ads.json").read_text())
    tables = numeric_tables()
    jobs = []
    for i, a in enumerate(ads):
        if a["solved"]:
            continue
        n = a["image"].replace("/", "_")
        sets = [e for s in (otsu, raw) for e in s.get(n, {}).values()]
        if sets:
            jobs.append((n, sets, 900 + i, tables))
    with ProcessPoolExecutor(7) as ex:
        rows = [r for r in ex.map(_job, jobs, chunksize=6) if r]
    rows.sort(key=lambda r: -(r["read"] - r["null_max"]))
    return {"id": "figaro_numeric_mixed", "control": control(tables), "tables": len(tables), "tested": len(jobs), "with_numbers": len(rows), "rows": rows}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(out["control"], out["tested"], out["with_numbers"])
    for r in out["rows"][:24]:
        print(r["image"], r["table"], r["name"], "A" if r["author"] else "-", r["read"], r["null_mean"], r["null_max"], r["reading"][:110])
