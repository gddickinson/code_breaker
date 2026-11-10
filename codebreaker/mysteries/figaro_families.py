"""Round 45: ads that read under one key, put in date order as possible correspondences.

Families come from the transcriptions of Rounds 42 to 45: every ad read under a documented table, and the ads read with
the V. T. A. key after 1877 (signed Valentin). Each family is listed with dates, signatures and readings; a family of
two or more ads under one key, from different signatures or none, is a candidate correspondence."""
import json
from collections import defaultdict

from ..languages import ROOT
from .figaro_keys import OUT

RESULT = ROOT / "data/results/figaro_families.json"
SOURCES = ("documented_transcription.json", "sweep_transcription.json")


def entries() -> list[dict]:
    out = []
    for f in SOURCES:
        for image, ad in json.loads((OUT / f).read_text())["ads"].items():
            sig = image.split("-", 1)[1][:-4] if "-" in image else ""
            out.append({"image": image, "date": f"{image[5:9]}-{image[9:11]}-{image[11:13]}", "signature": sig,
                        "key": ad.get("system") or ad.get("table"), "reading": ad["reading"]})
    rerank = ROOT / "data/results/figaro_rerank.json"
    if rerank.exists():
        data = json.loads((OUT / "rerank_transcription.json").read_text())["letters"]
        for r in json.loads(rerank.read_text())["rows"]:
            if r["any"]["null_p"] <= 0.007:
                sig = r["image"].split("-", 1)[1][:-4]
                out.append({"image": r["image"], "date": f"{r['image'][5:9]}-{r['image'][9:11]}-{r['image'][11:13]}", "signature": sig,
                            "key": r["any"]["system"], "reading": r["any"]["reading"].capitalize() + " (from the transcription " + data[r["image"]] + ")"})
    return out


def common_tables(n: int = 10) -> set:
    """Systems documented for many writers (such as the Caesar shift): shared use there says little about who wrote."""
    from .figaro_keys import TABLES

    return {t["id"] for t in TABLES if len(t["users"]) >= n}


def families() -> dict:
    by = defaultdict(list)
    for e in entries():
        by[e["key"]].append(e)
    return {k: sorted(v, key=lambda e: e["date"]) for k, v in by.items() if len(v) >= 2}


def run() -> dict:
    fams, common = families(), common_tables()
    return {"id": "figaro_families", "families": {k: {"ads": v, "signatures": sorted({e["signature"] or "-" for e in v}), "common_system": k in common,
                                                      "span": [v[0]["date"], v[-1]["date"]]} for k, v in fams.items()}}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for k, f in res["families"].items():
        print(k, f["signatures"], f["span"], "common" if f["common_system"] else "")
        for e in f["ads"]:
            print("  ", e["date"], e["signature"] or "-", e["reading"][:90])
