"""Round 91: the second transcriber measured on the transcribed ads, then a review queue for untranscribed ones.

Measured on every ad transcribed by eye (128): character error rate (CER) of the vision model, RapidOCR and Tesseract
(per line); and the calibration of agreement: of the model's characters inside the transcribed stretch, how many are
right when RapidOCR agrees with them and when it does not. Queue: untranscribed scans whose saved OCR (ocr.json) has
cipher-like lines, longest first, read by both and written with disputed characters in brackets to
data/results/figaro_transcription_queue.json and docs/transcription_queue.md, for reading by eye."""
import json
import time

import numpy as np

from . import figaro_lineocr as M
from . import figaro_lineocr_data as D
from . import figaro_second_reader as R
from .figaro_lineocr_eval import rapid_text
from ..languages import ROOT

RESULT = ROOT / "data/results/figaro_second_reader.json"
QUEUE = ROOT / "data/results/figaro_transcription_queue.json"
DOC = ROOT / "docs/transcription_queue.md"


def evaluate(cache: dict, log=print) -> dict:
    truth = D.truth()
    rows, cal = [], {"agreed_right": 0, "agreed_wrong": 0, "disputed_right": 0, "disputed_wrong": 0}
    for i, (n, t) in enumerate(sorted(truth.items())):
        v = R.vlm_read(n, cache) or ""
        rp = rapid_text(n)
        te = "".join(M.tesseract_line(l) for l in D.cut_lines(D.gray(D.IMAGES / n)))
        rows.append({"ad": n, "letters": len(t), "vlm": D.cer(t, v), "rapidocr": D.cer(t, rp), "tesseract": D.cer(t, te)})
        for k, x in R.calibrate(t, v, rp).items():
            cal[k] += x
        if i % 20 == 0:
            R.save(cache)
            log(f"{i} ads read")
    R.save(cache)
    keys = ("vlm", "rapidocr", "tesseract")
    total = sum(r["letters"] for r in rows)
    summary = {k: {"mean_cer": round(float(np.mean([r[k] for r in rows])), 3), "weighted_cer": round(sum(r[k] * r["letters"] for r in rows) / total, 3),
                   "best_on": sum(r[k] == min(r[j] for j in keys) for r in rows), "perfect": sum(r[k] == 0 for r in rows)} for k in keys}
    summary["best_of_vlm_and_rapidocr"] = round(float(np.mean([min(r["vlm"], r["rapidocr"]) for r in rows])), 3)
    held = [r for r in rows if M.held_out(r["ad"])]
    summary["held_out_40"] = {k: round(float(np.mean([r[k] for r in held])), 3) for k in keys}
    a, d = cal["agreed_right"] + cal["agreed_wrong"], cal["disputed_right"] + cal["disputed_wrong"]
    calib = {**cal, "agreed_share": round(a / max(a + d, 1), 3), "agreed_accuracy": round(cal["agreed_right"] / max(a, 1), 4),
             "disputed_accuracy": round(cal["disputed_right"] / max(d, 1), 3)}
    return {"ads": len(rows), "letters": total, "summary": summary, "agreement": calib, "rows": rows}


def candidates(n: int) -> list[str]:
    from .figaro_ocr import cipher_lines

    truth = D.truth()
    ocr = json.loads((ROOT / "data/sources/figaro/ocr.json").read_text())
    scored = []
    for name, text in ocr.items():
        if name in truth or not (D.IMAGES / name).exists():
            continue
        c = "".join(cipher_lines((text or "").splitlines()))
        if len(c) >= 12:
            scored.append((len(c), name))
    return [name for _, name in sorted(scored, reverse=True)[:n]]


def queue(cache: dict, n: int = 60, log=print) -> list[dict]:
    out = []
    for i, name in enumerate(candidates(n)):
        v = R.vlm_read(name, cache) or ""
        rp = rapid_text(name)
        f = R.agreement(v, rp)
        out.append({"ad": name, "model_reading": v.strip(), "rapidocr": rp, "marked": R.marked(v, rp),
                    "agreed_share": round(sum(f) / max(len(f), 1), 3)})
        if i % 20 == 0:
            R.save(cache)
            log(f"queue: {i} ads read")
    R.save(cache)
    return out


def write_doc(q: list[dict], cal: dict) -> None:
    lines = ["# Transcription queue (Round 91)", "",
             f"Untranscribed Le Figaro ads with cipher-like lines, read by the local vision model and by RapidOCR. Characters in [brackets] are disputed "
             f"(RapidOCR reads them differently). On the 128 ads transcribed by eye, agreed characters were right {cal['agreed_accuracy']:.1%} of the time and "
             f"disputed ones {cal['disputed_accuracy']:.0%}. None of this is ciphertext until it has been read by eye from the scan "
             "(data/sources/figaro/images).", "", "| Ad | Agreed | Vision model reading, disputed characters in brackets |", "|---|---|---|"]
    for x in sorted(q, key=lambda x: x["agreed_share"]):
        lines.append(f"| `{x['ad']}` | {x['agreed_share']:.0%} | {x['marked'][:160]} |")
    DOC.write_text("\n".join(lines) + "\n")


def run(n_queue: int = 60, log=print) -> dict:
    t0 = time.time()
    cache = R._cache()
    ev = evaluate(cache, log)
    q = queue(cache, n_queue, log)
    QUEUE.write_text(json.dumps(q, indent=1, ensure_ascii=False))
    write_doc(q, ev["agreement"])
    return {"id": "figaro_second_reader", "model": R.ai_local.status()["vision"], "minutes": round((time.time() - t0) / 60, 1), "queue": len(q), **ev}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps({k: r[k] for k in ("ads", "summary", "agreement", "queue", "minutes")}, indent=1))
