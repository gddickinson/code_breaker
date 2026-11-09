"""Dorabella: attempts across three transcriptions, with short-text controls."""
import ast
import re
from itertools import combinations

from ..languages import LANGS, ROOT
from ..segment import segment
from ..validation import null_test, positive_control, verdict

SRC = ROOT / "data/sources"
LINES = (29, 29)


def azdecrypt() -> str:
    return "".join((SRC / "unsolved/Dorabella.txt").read_text(errors="ignore").split())


def transcriptions() -> dict:
    out = {"AZdecrypt": list(azdecrypt())}
    a = SRC / "dorabella/a_data.py"
    if a.exists():
        t = a.read_text()
        out["Orlando"] = [s.split("/")[0] for row in ast.literal_eval(t[t.index("ROW_SYMBOLS = [") + 14: t.index("SKELETONS = [")].strip()) for s in row]
    b = SRC / "dorabella/b_corpus.py"
    if b.exists():
        out["cipher-lab"] = list("".join(re.findall(r'LINE_\d = "([A-Z]+)"', b.read_text())))
    return out


def disagreement(x, y) -> float:
    return round(sum((x[i] == x[j]) != (y[i] == y[j]) for i, j in combinations(range(len(x)), 2)) / (len(x) * (len(x) - 1) / 2), 4)


def run() -> dict:
    tr = transcriptions()
    names = list(tr)
    pairs = [{"a": a, "b": b, "pair_disagreement": disagreement(tr[a], tr[b])} for a, b in combinations(names, 2)]
    res = {"id": "dorabella", "text": azdecrypt(), "symbols": len(set(azdecrypt())), "agreement": pairs, "hypotheses": [], "controls": {}}
    tests = len(tr) * 2 * len(LANGS)
    for code in LANGS:
        res["controls"][LANGS[code]] = positive_control(tr[names[0]], code, False)
    for name, seq in tr.items():
        for direction, s in (("forward", seq), ("reversed", seq[::-1])):
            for code in LANGS:
                nt = null_test(s, code, False, n_null=16)
                res["hypotheses"].append({"transcription": name, "direction": direction, "language": LANGS[code], "z": nt["z"], "score": nt["score"], "null_mean": nt["null_mean"], "plaintext": segment(nt["plaintext"], code)})
    res["hypotheses"].sort(key=lambda h: -h["z"])
    res["tests"] = tests
    top = res["hypotheses"][0]
    code = next(c for c, n in LANGS.items() if n == top["language"])
    res["verdict"] = verdict(res["controls"][top["language"]], top["z"], tests, top["plaintext"].replace(" ", ""), top["score"], code)
    return res
