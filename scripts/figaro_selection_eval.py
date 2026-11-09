"""Compare ways of choosing between two OCR readings, on ads with known answers."""
import json
import re
from difflib import SequenceMatcher

from codebreaker.languages import ROOT
from codebreaker.mysteries import figaro_keys as K
from codebreaker.text import letters

OUT = ROOT / "data/sources/figaro"

if __name__ == "__main__":
    ads = {a["image"].replace("/", "_"): a for a in json.loads((OUT / "ads.json").read_text())}
    names = [p.name for p in (OUT / "control").glob("*.jpg")]
    sources = [json.loads((OUT / f).read_text()) for f in ("ocr_raw.json", "ocr_otsu.json")]
    rows = [{r["image"]: r for r in K.run_all(s, names)} for s in sources]
    truth = {n: letters(re.sub(r"\([a-z]+\)\s*$|\[|\]|\?", "", ads[n]["text"])) for n in names}

    def pick(strategy):
        out = {}
        for n in names:
            c = [r[n] for r in rows if n in r]
            if c:
                out[n] = strategy(c)
        return out

    def agree(c):
        return c[1] if len(c) == 2 and c[0]["method"] == c[1]["method"] and c[1]["letters"] >= c[0]["letters"] else c[0] if len(c) == 2 and c[0]["method"] == c[1]["method"] else max(c, key=lambda r: r["coverage"])

    strategies = {"first OCR": lambda c: c[0], "Otsu OCR": lambda c: c[-1], "highest coverage": lambda c: max(c, key=lambda r: (r["coverage"], r["letters"])), "highest language score": lambda c: max(c, key=lambda r: r["score"]), "coverage above null": lambda c: max(c, key=lambda r: r["coverage"] - r["null_coverage"]), "agreement then coverage": agree, "writer's own table first": lambda c: max(c, key=lambda r: (r["author_match"], r["coverage"]))}
    res = {}
    for name, f in strategies.items():
        p = pick(f)
        m = [SequenceMatcher(None, truth[n], r["plaintext"]).ratio() for n, r in p.items()]
        res[name] = {"recovered": sum(v >= 0.6 for v in m), "mean_match": round(sum(m) / len(m), 3)}
        print(name, res[name], flush=True)
    print("agree on method:", sum(1 for n in names if n in rows[0] and n in rows[1] and rows[0][n]["method"] == rows[1][n]["method"]), "of", len(names))
    (ROOT / "data/results/figaro_selection.json").write_text(json.dumps(res, indent=1))
