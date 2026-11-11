"""Train and measure the Le Figaro line reader (Round 88b); results in data/results/figaro_lineocr.json, model in
data/models/figaro_lines.pt (not committed).

Readers compared on held-out ads (30% by file-name hash, never used for training or labels): Tesseract per line
(psm 7, as used for the labels), RapidOCR on the whole scan (the engine the earlier OCR rounds preferred), the reader
trained on synthetic lines only, and the same reader fine-tuned on silver-labelled real lines from the training ads.
Score: the character error rate of each by-eye transcription as found in the reader's output for its ad (letters and
digits only, case ignored)."""
import json
import time

import numpy as np
import torch

from . import figaro_lineocr as M
from . import figaro_lineocr_data as D
from ..languages import ROOT

RESULT = ROOT / "data/results/figaro_lineocr.json"


def rapid_text(name: str) -> str:
    from .figaro_ocr import prepare, rapid_lines

    return " ".join(rapid_lines(prepare(str(D.IMAGES / name))))


def evaluate(net, names: list[str], truth: dict) -> dict:
    rows = []
    for n in names:
        lines = D.cut_lines(D.gray(D.IMAGES / n))
        t = truth[n]
        r = {"ad": n, "letters": len(t),
             "tesseract": D.cer(t, "".join(M.tesseract_line(l) for l in lines)),
             "rapidocr": D.cer(t, rapid_text(n))}
        for k, model in net.items():
            r[k] = D.cer(t, "".join(M.read_lines(model, lines)))
        rows.append(r)
    keys = [k for k in rows[0] if k not in ("ad", "letters")]
    total = sum(r["letters"] for r in rows)
    summary = {k: {"mean_cer": round(float(np.mean([r[k] for r in rows])), 3),
                   "weighted_cer": round(sum(r[k] * r["letters"] for r in rows) / total, 3),
                   "best_on": sum(r[k] == min(r[j] for j in keys) for r in rows)} for k in keys}
    return {"ads": len(rows), "letters": total, "summary": summary, "rows": rows}


def run(steps: int = 3000, ft_steps: int = 1500, log=print) -> dict:
    t0 = time.time()
    truth = D.truth()
    train = sorted(n for n in truth if not M.held_out(n))
    test = sorted(n for n in truth if M.held_out(n))
    log(f"{len(train)} training ads, {len(test)} held out")
    net = M.train_synthetic(steps=steps, log=log)
    synthetic = M.CRNN().to(M.device())
    synthetic.load_state_dict(net.state_dict())
    pairs = [p for n in train for p in M.silver_labels(n, truth[n])]
    log(f"{len(pairs)} silver-labelled real lines")
    tuned = M.finetune(net, pairs, steps=ft_steps, log=log)
    M.MODEL.parent.mkdir(parents=True, exist_ok=True)
    torch.save(tuned.state_dict(), M.MODEL)
    ev = evaluate({"synthetic_only": synthetic, "fine_tuned": tuned}, test, truth)
    return {"id": "figaro_lineocr", "training_ads": len(train), "held_out_ads": len(test), "real_lines": len(pairs),
            "synthetic_steps": steps, "finetune_steps": ft_steps, "minutes": round((time.time() - t0) / 60, 1), **ev}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r["summary"], indent=1))
