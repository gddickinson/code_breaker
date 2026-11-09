"""Autobreak: identify an unknown ciphertext, try the likely attacks, and rank the readings."""
from . import classifier
from .ciphers import REGISTRY
from .languages import LANGS, detect, score
from .segment import segment
from .text import letters
from .validation import coverage


def attempt(cid: str, text: str, lang: str) -> dict | None:
    c = REGISTRY.get(cid)
    if c is None:
        plain = letters(text)
        if len(plain) < 8:
            return None
        return {"cipher": "Plain text", "plaintext": plain, "score": score(plain, lang), "lang": lang}
    if not c.attack:
        return None
    try:
        r = c.attack(text, lang)
    except (ValueError, KeyError, IndexError, ZeroDivisionError):
        return None
    return {"cipher": c.name, "plaintext": r["plaintext"], "score": score(r["plaintext"], lang), "lang": lang, "key": r.get("key"), "method": r.get("method")}


def autobreak(text: str, top: int = 5, langs: tuple = ("en", "fr", "de", "la"), stop_coverage: float = 0.72) -> dict:
    """Try the classifier's top guesses, in each language, and stop early on a clearly readable result."""
    guesses = classifier.classify(text, top)
    if guesses is None:
        return {"guesses": [], "results": [], "best": None, "note": "No classifier is trained. Run scripts/train_classifier.py."}
    out = []
    for g in guesses:
        for lang in langs:
            r = attempt(g["id"], text, lang)
            if r is None:
                continue
            r["probability"] = g["probability"]
            r["coverage"] = coverage(letters(r["plaintext"])[:500], lang)
            r["spaced"] = segment(letters(r["plaintext"])[:500], lang)
            out.append(r)
            if r["coverage"] >= stop_coverage:
                break
        if out and out[-1]["coverage"] >= stop_coverage:
            break
    out.sort(key=lambda r: (-r["coverage"], -r["score"]))
    return {"guesses": guesses, "results": out, "best": out[0] if out else None, "note": "A high word coverage means readable text. Low coverage means the system was not recovered."}


__all__ = ["autobreak", "LANGS", "detect"]
