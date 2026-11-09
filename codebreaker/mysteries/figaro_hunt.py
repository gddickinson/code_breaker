"""Hunt the unsolved Le Figaro ads: OCR, then substitution and reversal, with a known-answer control."""
import json
import random
import re
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..attacks.classical import solve_symbols
from ..languages import ROOT
from ..segment import segment
from ..text import letters, similarity
from ..validation import coverage
from .figaro_ocr import read_ad

OUT = ROOT / "data/sources/figaro"
IMG = OUT / "images"
OCR = OUT / "ocr.json"
BASE = "https://www.apprendre-en-ligne.net/crypto/Figaro/"
MIN_LETTERS = 50
READABLE = 0.55


def ocr_job(a):
    name, path = a
    try:
        return name, read_ad(path)["text"]
    except Exception as exc:
        return name, f"!ERROR {exc}"


def ocr_all(paths, workers=4):
    done = json.loads(OCR.read_text()) if OCR.exists() else {}
    todo = [(p.name, str(p)) for p in paths if p.name not in done]
    with ProcessPoolExecutor(workers) as ex:
        for name, text in ex.map(ocr_job, todo, chunksize=8):
            done[name] = text
    OCR.write_text(json.dumps(done, ensure_ascii=False, indent=0))
    return done


def clean(text):
    return letters(text).lower() if not text.startswith("!") else ""


def solve_one(a):
    name, text, seed = a
    seq = [c for c in letters(text)]
    best = None
    for direction, s in (("forward", seq), ("reversed", seq[::-1])):
        if len(set(s)) > 26:
            continue
        r = solve_symbols(s, "fr", False, restarts=6, iters=50000, seed=seed)
        c = coverage(letters(r["plaintext"])[:500], "fr")
        if best is None or c > best["coverage"]:
            best = {"name": name, "direction": direction, "plaintext": r["plaintext"], "score": r["score"], "coverage": c, "letters": len(s)}
    if best is None:
        return None
    r = random.Random(seed)
    nulls = []
    for _ in range(4):
        sh = list(seq)
        r.shuffle(sh)
        q = solve_symbols(sh, "fr", False, restarts=3, iters=30000, seed=seed + 1)
        nulls.append(coverage(letters(q["plaintext"])[:500], "fr"))
    best["null_coverage"] = round(float(np.mean(nulls)), 3)
    best["reading"] = segment(letters(best["plaintext"])[:220], "fr")
    return best


def solve_all(texts, workers=6):
    jobs = [(n, t, 7 + i) for i, (n, t) in enumerate(texts.items()) if len(clean(t)) >= MIN_LETTERS]
    with ProcessPoolExecutor(workers) as ex:
        return [r for r in ex.map(solve_one, jobs, chunksize=4) if r]


def control(n=60, seed=3):
    """Run the whole pipeline on ads whose answers are known: enciphered, simple, long enough."""
    ads = json.loads((OUT / "ads.json").read_text())
    pool = [a for a in ads if a["solved"] and a["note"].startswith("chiffr") and len(letters(a["text"])) >= 90]
    sample = random.Random(seed).sample(pool, min(n, len(pool)))
    d = OUT / "control"
    d.mkdir(exist_ok=True)
    for a in sample:
        f = d / a["image"].replace("/", "_")
        if not f.exists():
            subprocess.run(["curl", "-sS", "-m", "40", "-A", "codebreaker-research/0.1", "-o", str(f), BASE + a["image"]], check=False)
            time.sleep(0.6)
    with ProcessPoolExecutor(4) as ex:
        ocr = dict(ex.map(ocr_job, [(a["image"], str(d / a["image"].replace("/", "_"))) for a in sample], chunksize=4))
    rows = []
    res = {r["name"]: r for r in solve_all(ocr)}
    for a in sample:
        got = res.get(a["image"])
        truth = letters(re.sub(r"\([a-z]+\)\s*$|\[|\]", "", a["text"]))
        o = clean(ocr[a["image"]])
        if got:
            sm = similarity(letters(got["plaintext"])[:len(truth)], truth)
            from difflib import SequenceMatcher as S
            rows.append({"image": a["image"], "ocr_letters": len(o), "truth_letters": len(truth), "coverage": got["coverage"], "null": got["null_coverage"], "match": round(S(None, truth, letters(got["plaintext"])).ratio(), 3), "positional": round(sm, 3)})
    return {"sampled": len(sample), "ocr_long_enough": len(rows), "rows": rows, "median_match": round(float(np.median([r["match"] for r in rows])), 3) if rows else None, "read_ok": sum(r["match"] >= 0.7 for r in rows), "flagged": sum(r["coverage"] >= READABLE for r in rows)}


def run() -> dict:
    ctrl = control()
    texts = ocr_all(sorted(p for p in IMG.glob("*.jpg")))
    rows = solve_all(texts)
    rows.sort(key=lambda r: -r["coverage"])
    (OUT / "hunt_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    usable = sum(len(clean(t)) >= MIN_LETTERS for t in texts.values())
    return {"id": "figaro_hunt", "images": len(texts), "usable_ocr": usable, "tested": len(rows), "control": {k: v for k, v in ctrl.items() if k != "rows"}, "control_rows": ctrl["rows"][:15], "flagged": [r for r in rows if r["coverage"] >= READABLE and r["coverage"] >= r["null_coverage"] + 0.2]}
