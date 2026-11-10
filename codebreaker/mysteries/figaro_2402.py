"""Round 66: the table 2402 family (documented for writers 47 and 74), transcribed and tested like table 2119.

Ten letter-digit ads of 1879-1889 (signed 47, 74, '2 Fev.' or unsigned) read under table 2402. Each is scored by the
share of letters in French or English dictionary words (with the inference R=O from table 2119 not applied: 2402 has
its own key), against 2,000 shuffled copies and against all 32 documented digit tables; Bonferroni over the ads.
Symbols missing from the documented table are inferred on the other ads and tested held out, with random-letter fits
as the control (as in Round 48)."""
import json
import random

from ..languages import ROOT
from . import figaro_2119 as T
from .figaro_digit_family import digit_tables

RESULT = ROOT / "data/results/figaro_2402.json"


def ads() -> dict:
    return json.loads(T.FAMILY.read_text())["table_2402"]


def key2402() -> dict:
    return dict(next(x for x in digit_tables() if x["id"] == "2402")["key"])


def held_out(key: dict, ts: dict, draws: int = 200, seed: int = 66) -> dict:
    miss = sorted({c for t in ts.values() for c in t.upper().replace(" ", "") if c not in key})
    full = {s: list(T.LETTERS) for s in miss}
    letters = sum(len(t.replace(" ", "")) for t in ts.values())

    def gain(choices):
        g = 0.0
        for name, t in ts.items():
            fitted = T.fit_missing(key, [x for n, x in ts.items() if n != name], choices)
            g += (T.share(t, {**key, **fitted}) - T.share(t, key)) * len(t.replace(" ", ""))
        return g / letters

    real, rnd = gain(full), random.Random(seed)
    ctrl = [gain({s: rnd.sample(T.LETTERS, 3) for s in miss}) for _ in range(draws)]
    return {"missing": miss, "fitted_all": T.fit_missing(key, list(ts.values()), full), "held_out_gain": round(real, 4),
            "random_gain_mean": round(sum(ctrl) / draws, 4), "random_gain_max": round(max(ctrl), 4), "p": (sum(c >= real for c in ctrl) + 1) / (draws + 1)}


def run() -> dict:
    ts, key, tables = ads(), key2402(), digit_tables()
    rows = []
    for j, (img, t) in enumerate(ts.items()):
        rnd = random.Random(6600 + j)
        s = T.share(t, key)
        null = [T.share(T.shuffled(t.upper(), rnd), key) for _ in range(2000)]
        others = sorted((T.share(t, x["key"]) for x in tables if x["id"] != "2402"), reverse=True)
        rows.append({"image": img, "share": round(s, 3), "p": (sum(x >= s for x in null) + 1) / 2001, "rank": 1 + sum(o > s for o in others),
                     "reading": " ".join(T.decode(t, key))})
    bar = 0.05 / len(rows)
    for r in rows:
        r["passes"] = r["p"] <= bar and r["rank"] == 1
    miss = held_out(key, ts)
    ext = {**key, **miss["fitted_all"]}
    for r in rows:
        r["reading_extended"] = " ".join(T.decode(ts[r["image"]], ext))
    return {"id": "figaro_2402", "bar": bar, "rows": rows, "passed": [r["image"] for r in rows if r["passes"]], "missing": miss}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for r in res["rows"]:
        print(r["image"][:16], r["share"], r["p"], r["rank"], r["passes"], "|", r["reading_extended"][:110])
    print(res["missing"])
