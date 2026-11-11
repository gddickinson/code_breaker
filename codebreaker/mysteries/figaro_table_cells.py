"""Group ads by documented digit table, then infer cells the table leaves blank, after testing on hidden known cells."""
import json
import random
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

from ..languages import ROOT
from ..text import A
from .figaro_digit_family import digit_tables, words as vocabulary
from .figaro_digit_sweep import numeric_tables
from .figaro_keys import OUT
from ..third_party import need

RESULT = ROOT / "data/results/figaro_table_cells.json"
MIN_FAMILY_READ = 0.45
MIN_GAIN = 5
MIN_USES = 2
MIN_NUMBER_SHARE = 0.6


def mixed_tokens(lines: list[str]) -> list[list[str]]:
    toks = [t.upper() for l in lines for t in re.split(r"[^A-Za-z0-9]+", l) if len(t) >= 2]
    return [list(t) for t in toks]


def numeric_tokens(lines: list[str]) -> list[list[str]]:
    """Words separated by spaces or punctuation other than the dot joining numbers."""
    out = []
    for t in re.split(r"[\s:;,—\-]+", " ".join(lines)):
        ps = [str(int(p)) if p.isdigit() else p.upper() for p in re.findall(r"\d+|[A-Za-z]", t)]
        if ps and any(p.isdigit() for p in ps):
            out.append(ps)
    return out


def word(tok: list[str], key: dict, numeric: bool) -> str:
    return "".join(key.get(p, p if numeric and p.isalpha() else ".") for p in tok)


def read(ad: list, key: dict, numeric: bool) -> int:
    v = vocabulary()
    return sum(len(tok) for tok in ad if word(tok, key, numeric) in v)


def share(ad: list, key: dict, numeric: bool) -> float:
    n = sum(map(len, ad))
    return read(ad, key, numeric) / n if n else 0.0


def infer(ads: list, key: dict, sym: str, numeric: bool) -> dict | None:
    """The letter for one symbol that makes most dictionary letters readable, or None if evidence is thin."""
    base = sum(read(a, key, numeric) for a in ads)
    gains = []
    for l in A:
        trial = {**key, sym: l}
        gains.append((sum(read(a, trial, numeric) for a in ads) - base, l))
    gains.sort(reverse=True)
    if gains[0][0] < MIN_GAIN or gains[0][0] - gains[1][0] < 2:
        return None
    return {"letter": gains[0][1], "gain": gains[0][0], "runner_up": gains[1][0]}


def uses(ads: list, sym: str) -> int:
    return sum(sum(tok.count(sym) for tok in a) for a in ads)


def number_share(ad: list) -> float:
    """Share of an ad's pieces that are numbers, so plain ads with a few figures can be excluded."""
    ps = [p for tok in ad for p in tok]
    return sum(p.isdigit() for p in ps) / len(ps) if ps else 0.0


def family(table: dict, pool: list, numeric: bool) -> list:
    best = {}
    for name, sets in pool:
        for s in sets:
            if len(s) >= 3 and (not numeric or number_share(s) >= MIN_NUMBER_SHARE):
                v = share(s, table["key"], numeric)
                if v >= MIN_FAMILY_READ and v > best.get(name, (0,))[0]:
                    best[name] = (v, s)
    return [(n, v[1], round(v[0], 3)) for n, v in best.items()]


def hidden_cell_test(table: dict, fam: list, numeric: bool) -> list:
    """Hide each known cell in turn; infer it from every ad except any that the cell made qualify alone."""
    ads = [f[1] for f in fam]
    out = []
    for sym, truth in table["key"].items():
        if uses(ads, sym) < MIN_USES:
            continue
        key = {k: v for k, v in table["key"].items() if k != sym}
        got = infer(ads, key, sym, numeric)
        out.append({"table": table["id"], "symbol": sym, "truth": truth, "guess": got["letter"] if got else None})
    return out


def blanks(table: dict, fam: list, numeric: bool) -> list:
    ads = [f[1] for f in fam]
    seen = Counter(p for a in ads for tok in a for p in tok if (p.isdigit() if numeric else True) and p not in table["key"])
    props = []
    for sym, n in seen.most_common():
        if n < MIN_USES or (numeric and len(sym) > 2):
            continue
        got = infer(ads, table["key"], sym, numeric)
        if got:
            # Held-out check: the same letter must be chosen from each ad's complement, when the ad uses the symbol.
            agree = total = 0
            for i, a in enumerate(ads):
                if uses([a], sym):
                    total += 1
                    rest = ads[:i] + ads[i + 1:]
                    r = infer(rest, table["key"], sym, numeric)
                    agree += bool(r and r["letter"] == got["letter"])
            props.append({"table": table["id"], "name": table["name"], "symbol": sym, "letter": got["letter"], "uses": n, "gain": got["gain"], "runner_up": got["runner_up"], "ads_using": total, "held_out_agree": agree})
    return props


def _do(a):
    table, pool, numeric = a
    fam = family(table, pool, numeric)
    if len(fam) < 3:
        return None
    return {"id": table["id"], "name": table["name"], "users": table["users"], "numeric": numeric, "family": [(f[0], f[2]) for f in fam], "hidden": hidden_cell_test(table, fam, numeric), "proposals": blanks(table, fam, numeric)}


def run() -> dict:
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    ads = json.loads(need(OUT / "ads.json").read_text())
    names = sorted({a["image"].replace("/", "_") for a in ads if not a["solved"]})
    sets = {n: [e for s in (otsu, raw) for e in s.get(n, {}).values() if e] for n in names}
    mixed = [(n, [mixed_tokens(e) for e in v]) for n, v in sets.items() if v]
    nums = [(n, [numeric_tokens(e) for e in v]) for n, v in sets.items() if v]
    jobs = [(t, mixed, False) for t in digit_tables()] + [(t, nums, True) for t in numeric_tables()]
    with ProcessPoolExecutor(7) as ex:
        rows = [r for r in ex.map(_do, jobs, chunksize=1) if r]
    hidden = [h for r in rows for h in r["hidden"]]
    answered = [h for h in hidden if h["guess"]]
    return {"id": "figaro_table_cells", "tables_with_family": len(rows), "hidden_cells": len(hidden), "answered": len(answered), "correct": sum(h["guess"] == h["truth"] for h in answered), "rows": rows}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print({k: v for k, v in out.items() if k != "rows"})
    for r in out["rows"]:
        print(r["id"], r["name"], r["users"][:4], "family", len(r["family"]), [f[0][:14] for f in r["family"]][:7])
        for p in r["proposals"]:
            print("   ", p["symbol"], "=", p["letter"], "uses", p["uses"], "gain", p["gain"], "next", p["runner_up"], "heldout", p["held_out_agree"], "/", p["ads_using"])
