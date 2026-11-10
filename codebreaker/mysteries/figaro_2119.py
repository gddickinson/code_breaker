"""Round 47: the letter-digit family of 1882-87 is the table 2119 correspondence (documented for writer 42).

Each transcribed ad is decoded with table 2119 plus the earlier inference R = O, and scored by the share of letters in
English or French dictionary words (the letters are bilingual). Controls: 2,000 shuffled copies of the ad (symbols
shuffled across its words), and the rank of table 2119 among all 32 documented digit tables. Bonferroni over the ads.
A screen of every other unsolved letter-digit ad (OCR) under the same key picks ads to transcribe next."""
import json
import random
from functools import lru_cache

from ..languages import ROOT, model
from .figaro_correspondence import FAMILIES
from .figaro_digit_family import digit_tables
from .figaro_digit_sweep import mixed_words
from .figaro_digit_words import shuffled
from .figaro_keys import OUT

RESULT = ROOT / "data/results/figaro_2119.json"
FAMILY = OUT / "letter_digit_family.json"
SHUFFLES = 2000
TOP, SCREEN_SHUFFLES = 40, 20000  # the screen's best ads get a fine null; Bonferroni over every ad screened


@lru_cache(maxsize=1)
def vocab() -> frozenset:
    return frozenset(str(w).upper() for lang in ("en", "fr") for w in model(lang)["words"] if len(w) >= 2) | {"A", "I", "Y"}


def key2119() -> dict:
    t = next(x for x in digit_tables() if x["id"] == "2119")
    return {**t["key"], **FAMILIES["2119"]}


def decode(text: str, key: dict) -> list[str]:
    return ["".join(key.get(c, ".") for c in w) for w in text.upper().split()]


def share(text: str, key: dict) -> float:
    out, v = decode(text, key), vocab()
    n = sum(map(len, out))
    return sum(len(x) for x in out if x in v) / n if n else 0.0


def judge(text: str, key: dict, tables: list[dict], seed: int) -> dict:
    real, rnd = share(text, key), random.Random(seed)
    null = [share(shuffled(text.upper(), rnd), key) for _ in range(SHUFFLES)]
    others = sorted((share(text, t["key"]) for t in tables if t["id"] != "2119"), reverse=True)
    return {"share": round(real, 3), "p": (sum(x >= real for x in null) + 1) / (SHUFFLES + 1), "null_max": round(max(null), 3),
            "best_other_table": round(others[0], 3), "rank": 1 + sum(o > real for o in others)}


def screen(members: set) -> list[dict]:
    """Every other unsolved letter-digit ad, from OCR, under table 2119 (to choose what to transcribe)."""
    ads = {a["image"].replace("/", "_"): a for a in json.loads((OUT / "ads.json").read_text())}
    raw = json.loads((OUT / "ocr_raw.json").read_text())
    key, out = key2119(), []
    for n, e in raw.items():
        a = ads.get(n)
        if a is None or a["solved"] in (True, "True") or n in members:
            continue
        w = mixed_words(e.get("tesseract") or [])
        if len(w.replace(" ", "")) >= 15:
            out.append({"image": n, "text": w, "share": round(share(w, key), 3), "reading": " ".join(decode(w, key))[:120]})
    out.sort(key=lambda r: -r["share"])
    bar = 0.05 / max(len(out), 1)
    for j, r in enumerate(out[:TOP]):
        rnd = random.Random(4900 + j)
        null = [share(shuffled(r["text"], rnd), key) for _ in range(SCREEN_SHUFFLES)]
        r["p"] = (sum(x >= r["share"] for x in null) + 1) / (SCREEN_SHUFFLES + 1)
        r["passes"] = r["p"] <= bar
    return out, bar


def run() -> dict:
    fam = json.loads(FAMILY.read_text())["ads"]
    key, tables = key2119(), digit_tables()
    rows = [{"image": i, **judge(t, key, tables, 4800 + j), "reading": " ".join(decode(t, key))} for j, (i, t) in enumerate(fam.items())]
    bar = 0.05 / len(rows)
    for r in rows:
        r["passes"] = r["p"] <= bar and r["rank"] == 1
    known = {t["image"] for f in json.loads((ROOT / "data/results/figaro_correspondence.json").read_text())["families"] for t in f["timeline"]}
    scr, sbar = screen(set(fam) | known)
    n_screen = round(0.05 / sbar)
    return {"id": "figaro_2119", "bar": bar, "rows": rows, "new_members": [r["image"] for r in rows if r["passes"] and r["image"] not in known],
            "screen": scr[:TOP], "screened": n_screen, "screen_bar": sbar, "screen_passed": [r["image"] for r in scr[:TOP] if r.get("passes")]}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for r in res["rows"]:
        print(r["image"][:16], r["share"], r["p"], r["null_max"], r["best_other_table"], r["rank"], r["passes"], r["reading"][:80])
    print("new members", res["new_members"])
    print("screened", res["screened"], "bar", res["screen_bar"], "passed", len(res["screen_passed"]))
    for r in res["screen"]:
        print("  screen", r["image"], r["share"], r["p"], r["passes"], r["reading"][:80])
