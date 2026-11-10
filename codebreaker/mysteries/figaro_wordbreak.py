"""Round 57: other unsolved series whose enciphered words keep printed word breaks, tested with the Round 56 pipeline.

Candidates come from OCR: unsolved ads not in a known family and without a lead, whose tokens are mostly not French
words; pooled by signature. Each series goes through blind solve plus word-aware refinement, with the same pipeline on
shuffled copies and on a planted control with word breaks (figaro_wordrefine.test). OCR damages letters, so a pass is
a reason to transcribe; a failure says little."""
import json
import re
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

from ..languages import ROOT
from .figaro_keys import OUT
from .figaro_wordrefine import test, vocab

RESULT = ROOT / "data/results/figaro_wordbreak.json"
SIGNATURES = ("P", "R", "13", "A", "42", "D", "T", "38", "E", "8", "JN22", "17", "PAUL")
SKIP = ("VTA", "Valentin", "LRG", "LC15")


def led_dates() -> set:
    from .. import leads as L

    out = set()
    for (code,) in L.connect().execute("select code from leads where code like 'figaro-1%'"):
        m = re.match(r"figaro-(\d{4}-\d\d-\d\d)", code)
        if m:
            out.add(m.group(1))
    return out


def candidates(signatures=SIGNATURES) -> dict:
    ads = {a["image"].replace("/", "_"): a for a in json.loads((OUT / "ads.json").read_text())}
    raw, v, led, out = json.loads((OUT / "ocr_raw.json").read_text()), vocab(), led_dates(), defaultdict(dict)
    for n, e in raw.items():
        a = ads.get(n)
        if a is None or a["solved"] in (True, "True") or "-" not in n or f"{n[5:9]}-{n[9:11]}-{n[11:13]}" in led:
            continue
        sig = n.split("-", 1)[1][:-4]
        if sig not in signatures or any(x in sig for x in SKIP):
            continue
        toks = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", " ".join(e.get("tesseract") or []))]
        ciph = [t for t in toks if len(t) >= 2 and t not in v]
        if len(toks) >= 4 and len(ciph) / len(toks) >= 0.6:
            out[sig][n] = [list(t) for t in ciph]
    return {k: x for k, x in out.items() if sum(len(w) for ws in x.values() for w in ws) >= 200}


def run() -> dict:
    rows = []
    with ProcessPoolExecutor(7) as ex:
        for sig, ads in candidates().items():
            r = test(sig, ex, ads=ads)
            rows.append({"signature": sig, "ads": len(ads), "symbols": sum(len(w) for ws in ads.values() for w in ws),
                         **{k: r[k] for k in ("blind_share", "refined_share", "null", "planted_accuracy", "planted_refined_coverage", "coverage", "gates")},
                         "readings": {i: t[:160] for i, t in list(r["readings"].items())[:6]}})
    return {"id": "figaro_wordbreak", "series": len(rows), "passed": [r["signature"] for r in rows if r["gates"]["passed"]], "rows": rows}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(res["series"], res["passed"])
    for r in res["rows"]:
        print(r["signature"], r["ads"], r["symbols"], r["blind_share"], "->", r["refined_share"], max(n["refined"] for n in r["null"]), r["coverage"], round(0.8 * r["planted_refined_coverage"], 3), r["gates"])
