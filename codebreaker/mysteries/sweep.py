"""Calibrated sweep over the AZdecrypt 'Unsolved' collection."""
import re
from concurrent.futures import ProcessPoolExecutor

from ..analysis import ic, likely_period
from ..attacks.classical import solve_symbols
from ..languages import LANGS, ROOT, score
from ..segment import segment
from ..text import to_ints
from ..validation import null_test, positive_control, verdict

DIR = ROOT / "data/sources/unsolved"
SKIP = ("Beale", "Dorabella", "Kryptos", "D'Agapeyeff", "Taman Shud")  # have their own case files


def tokens(raw: str) -> list[str]:
    """Numeric files split on separators; everything else is one symbol per character."""
    parts = raw.split()
    if len(parts) > 3 and all(re.fullmatch(r"[\d,.;]+", p) for p in parts) and sum(len(p) for p in parts) / len(parts) > 1.2:
        return re.findall(r"\d+", raw)
    return list("".join(parts))


def attempt(path) -> dict:
    t = tokens(path.read_text(errors="ignore"))
    distinct = len(set(t))
    row = {"name": path.stem, "length": len(t), "symbols": distinct}
    if len(t) < 20 or distinct < 2:
        return {**row, "status": "too short", "z": None}
    homo = distinct > 26
    letters_only = all(len(x) == 1 and "A" <= x <= "Z" for x in t)
    if letters_only:
        row["ic"] = round(ic(to_ints("".join(t))), 4)
    best = None
    for code in LANGS:
        nt = null_test(t, code, homo, n_null=7, restarts=3, iters=1500000 if homo else 40000)
        if best is None or nt["z"] > best["z"]:
            best = {**nt, "language": LANGS[code], "code": code}
    pc = positive_control(t, best["code"], homo, restarts=3, iters=1500000 if homo else 40000, trials=2)
    return {**row, "status": "tested", "model": "homophonic" if homo else "substitution", "language": best["language"], "z": best["z"], "score": best["score"], "null_mean": best["null_mean"], "control": pc["mean"],
            "verdict": verdict(pc, best["z"], len(LANGS), best["plaintext"], best["score"], best["code"]), "reading": segment(best["plaintext"][:160], best["code"])}


def run() -> dict:
    files = [p for p in sorted(DIR.glob("*.txt")) if not p.name.startswith("_") and not p.name.startswith(SKIP)]
    with ProcessPoolExecutor(9) as ex:
        rows = list(ex.map(attempt, files))
    rows.sort(key=lambda r: -(r["z"] if r["z"] is not None else -99))
    return {"id": "sweep", "files": len(files), "rows": rows}
