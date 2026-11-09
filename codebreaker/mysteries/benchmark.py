"""Benchmark on real solved ciphers from AZdecrypt: how often do our tools produce readable text?"""
from concurrent.futures import ProcessPoolExecutor

from ..attacks.classical import columnar_search, solve_symbols
from ..autobreak import autobreak
from ..languages import ROOT
from ..segment import segment
from ..text import letters
from ..validation import coverage
from .sweep import tokens

DIR = ROOT / "data/sources/benchmark"
LANGS_TRY = ("en", "fr", "de", "la")


def best_of(tries):
    return max(tries, key=lambda r: r["coverage"])


def judge(result, lang):
    text = letters(result["plaintext"])
    return {**result, "lang": lang, "coverage": coverage(text[:500], lang), "reading": segment(text[:150], lang)}


def substitution(seq):
    return best_of([judge(solve_symbols(seq, lang, len(set(seq)) > 26, restarts=4, iters=(2000000 if len(set(seq)) > 26 else 60000)), lang) for lang in LANGS_TRY])


def bigram(seq):
    joined = "".join(seq)
    pairs = [joined[i:i + 2] for i in range(0, len(joined) - 1, 2)]
    shifted = [joined[i:i + 2] for i in range(1, len(joined) - 1, 2)]
    return best_of([judge(solve_symbols(p, lang, True, restarts=4), lang) for p in (pairs, shifted) for lang in ("en", "de")])


def transposition(seq):
    t = "".join(seq).upper()
    if not letters(t) or len(letters(t)) < 0.9 * len(t):
        return None
    r = judge(columnar_search(t, "en"), "en")
    ab = autobreak(t, top=3, langs=("en",))
    if ab["best"]:
        r = best_of([r, judge(ab["best"], "en")])
    return r


def job(a):
    folder, path = a
    seq = tokens(path.read_text(errors="ignore"))
    if len(seq) < 30:
        return None
    r = {"bigram": bigram, "substitution": substitution, "transposition": transposition, "combined": substitution}[folder](seq)
    if r is None:
        return None
    return {"folder": folder, "name": path.stem, "length": len(seq), "symbols": len(set(seq)), "coverage": r["coverage"], "lang": r["lang"], "reading": r["reading"], "readable": r["coverage"] >= 0.55}


def run() -> dict:
    folders = {"Substitution": "substitution", "Transposition": "transposition", "Bigram_substitution": "bigram", "Substitution_and_transposition": "combined"}
    jobs = [(kind, p) for d, kind in folders.items() for p in sorted((DIR / d).glob("*.txt"))]
    with ProcessPoolExecutor(6) as ex:
        rows = [r for r in ex.map(job, jobs) if r]
    summary = {}
    for k in folders.values():
        sub = [r for r in rows if r["folder"] == k]
        summary[k] = {"files": len(sub), "readable": sum(r["readable"] for r in sub)}
    return {"id": "benchmark", "summary": summary, "rows": sorted(rows, key=lambda r: (r["folder"], -r["coverage"]))}
