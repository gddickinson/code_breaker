"""Round 45: the V. T. A. key (built from the 1877 ads only) on every unsolved ad with letter-digit words.

From the OCR of each ad, the tokens that are not English or French words are decoded with the key and scored by the
share of letters in dictionary words (segmented, as in Round 37). Null: the key's letters shuffled among its symbols.
Two stages keep it affordable: 200 shuffled keys for every ad, 20,000 for ads at p <= 0.005; Bonferroni over all ads.
The 1877 V. T. A. ads themselves are reported but not counted, since they built the key."""
import json
import random
import re

from ..languages import ROOT
from . import figaro_vta as V
from .figaro_keys import OUT
from ..third_party import need

RESULT = ROOT / "data/results/figaro_vta_sweep.json"
FIRST, SECOND = 200, 20000


def tokens(text: str) -> list[str]:
    v = V.vocabulary()
    toks = re.findall(r"[a-z0-9+]+", text.lower().replace("十", "+"))
    return [t for t in toks if len(t) >= 2 and t.translate(V.MERGE) not in v and not t.isdigit()]


def ads_with_digits() -> dict:
    ads = {a["image"].replace("/", "_"): a for a in json.loads(need(OUT / "ads.json").read_text())}
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    out = {}
    for n in sorted(set(otsu) | set(raw)):
        a = ads.get(n)
        if a is None or a["solved"] in (True, "True"):
            continue
        lines = (raw.get(n, {}).get("tesseract") or []) + (otsu.get(n, {}).get("tesseract") or [])
        t = tokens(" ".join(lines))
        if sum(bool(re.search(r"\d", x)) and bool(re.search(r"[a-z]", x)) for x in t) >= 3:
            out[n] = sorted(set(t), key=t.index)
    return out


def p_value(words: list[str], key: dict, n: int, seed: int) -> tuple[float, float, float]:
    real = V.word_share(words, key)
    rnd = random.Random(seed)
    null = [V.word_share(words, V.shuffled_key(key, rnd)) for _ in range(n)]
    return real, (sum(x >= real for x in null) + 1) / (n + 1), max(null)


def run() -> dict:
    saved = V.SCORING
    V.SCORING = "segmented"
    try:
        key, rows = V.full_key(), []
        for i, (n, words) in enumerate(ads_with_digits().items()):
            real, p, mx = p_value(words, key, FIRST, 4500 + i)
            if p <= 0.005:
                real, p, mx = p_value(words, key, SECOND, 4500 + i)
            rows.append({"image": n, "words": len(words), "share": round(real, 3), "p": p, "null_max": round(mx, 3), "vta_1877": "VTA" in n,
                         "reading": " ".join(V.decode(w, key) for w in words)[:300]})
    finally:
        V.SCORING = saved
    tested = [r for r in rows if not r["vta_1877"]]
    bar = 0.05 / max(len(tested), 1)
    for r in rows:
        r["passes"] = (not r["vta_1877"]) and r["p"] <= bar
    rows.sort(key=lambda r: r["p"])
    return {"id": "figaro_vta_sweep", "ads": len(tested), "bonferroni_bar": bar, "passed": [r["image"] for r in rows if r["passes"]],
            "vta_1877_recovered": sum(r["vta_1877"] and r["p"] <= bar for r in rows), "vta_1877_ads": sum(r["vta_1877"] for r in rows), "rows": rows}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print({k: v for k, v in res.items() if k != "rows"})
    for r in res["rows"][:30]:
        print(r["image"][:24], r["words"], r["share"], r["p"], r["null_max"], r["passes"], r["reading"][:90])
