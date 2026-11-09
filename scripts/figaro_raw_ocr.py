"""OCR every downloaded Le Figaro image, unsolved and control, keeping all lines from both engines."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

from codebreaker.languages import ROOT
from codebreaker.mysteries.figaro_ocr import raw_read

OUT = ROOT / "data/sources/figaro"
PATH = OUT / "ocr_raw.json"


def job(p):
    try:
        return p.name, raw_read(str(p))
    except Exception as exc:
        return p.name, {"error": repr(exc), "tesseract": [], "rapid": []}


if __name__ == "__main__":
    done = json.loads(PATH.read_text()) if PATH.exists() else {}
    files = [p for d in ("images", "control") for p in sorted((OUT / d).glob("*.jpg")) if p.name not in done]
    with ProcessPoolExecutor(5) as ex:
        for i, (name, r) in enumerate(ex.map(job, files, chunksize=6)):
            done[name] = r
            if i % 100 == 0:
                PATH.write_text(json.dumps(done, ensure_ascii=False))
                print(i, flush=True)
    PATH.write_text(json.dumps(done, ensure_ascii=False))
    print("complete", len(done), flush=True)
