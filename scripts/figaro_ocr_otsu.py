"""OCR every Le Figaro image with the cleanup that scored best on known answers."""
import json
from concurrent.futures import ProcessPoolExecutor

from codebreaker.languages import ROOT
from codebreaker.mysteries.figaro_ocr import rapid_lines, tesseract_lines, variant

OUT = ROOT / "data/sources/figaro"


def job(p):
    try:
        img = variant(str(p), "otsu")
        return p.name, {"tesseract": tesseract_lines(img, True), "rapid": rapid_lines(img)}
    except Exception as exc:
        return p.name, {"error": repr(exc), "tesseract": [], "rapid": []}


if __name__ == "__main__":
    files = [p for d in ("images", "control") for p in sorted((OUT / d).glob("*.jpg"))]
    done = {}
    with ProcessPoolExecutor(5) as ex:
        for name, r in ex.map(job, files, chunksize=6):
            done[name] = r
    (OUT / "ocr_otsu.json").write_text(json.dumps(done, ensure_ascii=False))
    print("complete", len(done), flush=True)
