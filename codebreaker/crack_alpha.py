"""The Workbench crack for text in Cyrillic, Greek, Hebrew or Arabic script (Round 86): the same events as crack.py
(steps, attempts, a finish with a verdict), from attacks/alphabet.py and its three gates."""
import time

from . import alphabets as AB
from .attacks import alphabet as AT
from .validation import READABLE

NAMES = {"caesar": "Caesar shift", "vigenere": "Vigenere", "substitution": "Simple substitution"}


def applies(raw: str) -> bool:
    script, _ = AB.detect_script(raw)
    return script is not None


def _level(text: str) -> tuple[str, str]:
    if text.startswith(READABLE):
        return "readable", "Readable result"
    if text.startswith("Already plain"):
        return "readable", "Already plain text"
    if text.startswith("Structure only"):
        return "partial", "Structure, not yet a reading"
    return "none", "Not cracked"


def run(raw: str, lang: str | None = None):
    start = time.time()
    script, share = AB.detect_script(raw)
    yield {"event": "step", "id": "script", "title": "Find the script", "summary": f"{share:.0%} of the letters are {script}; attacks run on that alphabet, not A-Z."}
    langs = [lang] if lang in AB.LANGS and AB.script_of(lang) == script else None
    r = AT.crack(raw, langs)
    if "best" not in r:
        v = {"level": "none", "label": "Not cracked", "why": r["note"]}
        yield {"event": "finish", "verdict": v, "best": None, "nulls": [], "tried": 0, "readings": 0, "not_applicable": 0, "unfinished": 0, "seconds": round(time.time() - start, 1), "top": []}
        return
    names = ", ".join(AB.LANGS[c][0] for c in r["languages"])
    yield {"event": "step", "id": "attack", "title": "Try every method", "summary": f"Caesar, Vigenere and simple substitution in {names}, each judged against the language's own text.", "planned": len(r["attempts"])}
    rows = []
    for a in sorted(r["attempts"], key=lambda x: -x["score"])[:6]:
        row = {"event": "attempt", "kind": "attempt", "cid": a["kind"], "cipher": NAMES.get(a["kind"], "Already plain text"), "family": "Other alphabets",
               "lang": a["lang"], "method": f"{a['kind']} over the {len(AB.model(a['lang'])['alpha'])}-letter {AB.LANGS[a['lang']][0]} alphabet",
               "key": "", "plaintext": a["text"][:900], "spaced": AB.segment(a["text"][:900], a["lang"]), "seconds": 0, "coverage": a["coverage"], "score": round(a["score"], 3)}
        rows.append(row)
        yield row
    level, label = _level(r["verdict"])
    gates = f" Positive control recovered {r['positive_control']['mean']:.0%} of a planted passage; z={r['z']} against shuffled ciphertext." if "z" in r else ""
    v = {"level": level, "label": label, "why": r["verdict"] + gates}
    yield {"event": "finish", "verdict": v, "best": rows[0], "nulls": [], "tried": len(r["attempts"]), "readings": len(r["attempts"]), "not_applicable": 0, "unfinished": 0,
           "seconds": round(time.time() - start, 1), "top": [{k: x[k] for k in ("cipher", "lang", "coverage", "score", "method", "key")} for x in rows[:5]]}
