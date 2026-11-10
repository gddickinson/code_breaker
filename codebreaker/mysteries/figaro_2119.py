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


CORRECTIONS = {"1": "B"}  # Round 49: the database's table gives x; B reads better in 11 of 12 ads (sign test p=0.003)


def full_key() -> dict:
    """Documented table, R=O (Round 26), the seven inferred symbols (Round 48) and the Round 49 correction."""
    r = json.loads(RESULT.read_text()) if RESULT.exists() else {}
    return {**key2119(), **r.get("missing", {}).get("fitted_all", {}), **CORRECTIONS}


def screen(members: set, key: dict | None = None) -> list[dict]:
    """Every other unsolved letter-digit ad, from OCR, under table 2119 (to choose what to transcribe)."""
    ads = {a["image"].replace("/", "_"): a for a in json.loads((OUT / "ads.json").read_text())}
    raw = json.loads((OUT / "ocr_raw.json").read_text())
    key, out = key or key2119(), []
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


LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def texts() -> dict:
    d = json.loads(FAMILY.read_text())
    return {**d["ads"], **d.get("checked_screen", {})}


def missing_symbols(key: dict, ts: dict) -> list[str]:
    return sorted({c for t in ts.values() for c in t.upper().replace(" ", "") if c not in key})


def fit_missing(key: dict, ts: list[str], choices: dict) -> dict:
    """Greedy: give each missing symbol the choice that puts most letters into dictionary words in these texts."""
    k = dict(key)
    total = lambda kk: sum(share(t, kk) * len(t.replace(" ", "")) for t in ts)
    for s in sorted(choices, key=lambda s: -sum(t.upper().count(s) for t in ts)):
        k[s] = max(choices[s], key=lambda l: total({**k, s: l}))
    return {s: k[s] for s in choices}


def held_out_missing(draws: int = 30, seed: int = 48, symbols=None, base=None) -> dict:
    """Each ad in turn: fit the missing symbols on the others, measure the gain on it. Control: the same fit when each
    symbol may only take one of three random letters (so a gain from mere freedom is measured)."""
    key, ts = dict(base or key2119()), texts()
    miss = symbols or missing_symbols(key, ts)
    for s in miss:
        key.pop(s, None)
    full = {s: list(LETTERS) for s in miss}
    gain = 0.0
    for name, t in ts.items():
        fitted = fit_missing(key, [x for n, x in ts.items() if n != name], full)
        gain += (share(t, {**key, **fitted}) - share(t, key)) * len(t.replace(" ", ""))
    rnd, ctrl = random.Random(seed), []
    for _ in range(draws):
        limited = {s: rnd.sample(LETTERS, 3) for s in miss}
        g = 0.0
        for name, t in ts.items():
            fitted = fit_missing(key, [x for n, x in ts.items() if n != name], limited)
            g += (share(t, {**key, **fitted}) - share(t, key)) * len(t.replace(" ", ""))
        ctrl.append(g)
    letters = sum(len(t.replace(" ", "")) for t in ts.values())
    return {"missing": miss, "fitted_all": fit_missing(key, list(ts.values()), full), "held_out_gain": round(gain / letters, 4),
            "random_gain_mean": round(sum(ctrl) / len(ctrl) / letters, 4), "random_gain_max": round(max(ctrl) / letters, 4),
            "p": (sum(c >= gain for c in ctrl) + 1) / (draws + 1)}


def timeline(known_rows: list[dict], readings: dict, members: list[str]) -> list[dict]:
    """Earlier members (Round 26) and the members added here, in date order."""
    out = {t["image"]: {"image": t["image"], "date": f"{t['image'][5:9]}-{t['image'][9:11]}-{t['image'][11:13]}", "signature": t["signature"], "reading": t["reading"], "added": "earlier"} for t in known_rows}
    for i in members:
        out.setdefault(i, {"image": i, "date": f"{i[5:9]}-{i[9:11]}-{i[11:13]}", "signature": i.split("-", 1)[1][:-4] if "-" in i else "",
                           "reading": readings.get(i, ""), "added": "Round 47-48"})
    return sorted(out.values(), key=lambda e: e["image"][5:13])


def sign_test_b() -> dict:
    from math import comb

    ext, better, worse = {**key2119(), **json.loads(RESULT.read_text())["missing"]["fitted_all"]}, 0, 0
    for t in texts().values():
        if "1" in t:
            b, x = share(t, {**ext, "1": "B"}), share(t, {**ext, "1": "X"})
            better, worse = better + (b > x), worse + (b < x)
    k = better + worse
    return {"better": better, "worse": worse, "p": sum(comb(k, i) for i in range(better, k + 1)) / 2 ** k}


def rescreen() -> dict:
    """Round 49: every OCR letter-digit ad not yet in the correspondence, under the full key."""
    r = json.loads(RESULT.read_text())
    members = {e["image"] for e in r["timeline"]} | set(r["checked"])
    scr, bar = screen(members, full_key())
    return {"sign_test_1_is_b": sign_test_b(), "screened": round(0.05 / bar), "bar": bar, "top": scr[:TOP],
            "passed": [x["image"] for x in scr[:TOP] if x.get("passes")]}


def run() -> dict:
    fam = json.loads(FAMILY.read_text())["ads"]
    key, tables = key2119(), digit_tables()
    rows = [{"image": i, **judge(t, key, tables, 4800 + j), "reading": " ".join(decode(t, key))} for j, (i, t) in enumerate(fam.items())]
    bar = 0.05 / len(rows)
    for r in rows:
        r["passes"] = r["p"] <= bar and r["rank"] == 1
    known = {t["image"] for f in json.loads((ROOT / "data/results/figaro_correspondence.json").read_text())["families"] for t in f["timeline"]}
    missing = held_out_missing(draws=200)
    ext = {**key, **missing["fitted_all"]}
    readings = {i: " ".join(decode(t, ext)) for i, t in texts().items()}
    fam_rows = next(f for f in json.loads((ROOT / "data/results/figaro_correspondence.json").read_text())["families"] if f["table"] == "2119")["timeline"]
    scr, sbar = screen(set(fam) | known)
    n_screen = round(0.05 / sbar)
    return {"id": "figaro_2119", "bar": bar, "rows": rows, "new_members": [r["image"] for r in rows if r["passes"] and r["image"] not in known],
            "timeline": timeline(fam_rows, readings, [r["image"] for r in rows if r["passes"]] + sorted(json.loads(FAMILY.read_text()).get("checked_screen", {}))),
            "missing": missing, "readings_extended": readings, "checked": sorted(json.loads(FAMILY.read_text()).get("checked_screen", {})),
            "screen": scr[:TOP], "screened": n_screen, "screen_bar": sbar, "screen_passed": [r["image"] for r in scr[:TOP] if r.get("passes")]}


if __name__ == "__main__" and len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "rescreen":
    res = rescreen()
    (ROOT / "data/results/figaro_2119_rescreen.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(res["sign_test_1_is_b"], res["screened"], len(res["passed"]))
    for x in res["top"]:
        print(" ", x["image"], x["share"], x["p"], x["passes"], x["reading"][:90])
elif __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for r in res["rows"]:
        print(r["image"][:16], r["share"], r["p"], r["null_max"], r["best_other_table"], r["rank"], r["passes"], r["reading"][:80])
    print("new members", res["new_members"])
    print("missing symbols", res["missing"])
    print("timeline", len(res["timeline"]), res["timeline"][0]["date"], res["timeline"][-1]["date"])
    print("screened", res["screened"], "bar", res["screen_bar"], "passed", len(res["screen_passed"]))
    for r in res["screen"]:
        print("  screen", r["image"], r["share"], r["p"], r["passes"], r["reading"][:80])
