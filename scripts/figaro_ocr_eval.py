"""Which OCR cleanup recovers the most Le Figaro ads with known answers?"""
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher

from codebreaker.languages import ROOT
from codebreaker.mysteries import figaro_keys as K
from codebreaker.mysteries.figaro_ocr import rapid_lines, tesseract_lines, variant
from codebreaker.text import letters

OUT = ROOT / "data/sources/figaro"


def read(a):
    p, name, wl = a
    img = variant(str(p), name)
    return p.name, {"tesseract": tesseract_lines(img, wl), "rapid": rapid_lines(img)}


if __name__ == "__main__":
    ads = {a["image"].replace("/", "_"): a for a in json.loads((OUT / "ads.json").read_text())}
    files = sorted((OUT / "control").glob("*.jpg"))
    truth = {f.name: letters(re.sub(r"\([a-z]+\)\s*$|\[|\]|\?", "", ads[f.name]["text"])) for f in files if f.name in ads}
    out = {}
    for name, wl in (("base", False), ("base", True), ("big", False), ("otsu", False), ("otsu", True), ("adaptive", False), ("denoise", False)):
        with ProcessPoolExecutor(5) as ex:
            raw = dict(ex.map(read, [(f, name, wl) for f in files], chunksize=4))
        rows = K.run_all(raw, list(raw))
        m = {r["image"]: SequenceMatcher(None, truth[r["image"]], r["plaintext"]).ratio() for r in rows}
        key = f"{name}{' whitelist' if wl else ''}"
        out[key] = {"long_enough": len(rows), "recovered": sum(v >= 0.6 for v in m.values()), "mean_match": round(sum(m.values()) / max(len(m), 1), 3)}
        print(key, out[key], flush=True)
    (ROOT / "data/results/figaro_ocr_eval.json").write_text(json.dumps(out, indent=1))
