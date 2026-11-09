"""Work done in separate processes, so a slow attack can be stopped when its time runs out."""
import random
import re
import time

from . import crack_steps as S
from .ciphers import REGISTRY
from .text import letters


def attack(cid: str, text: str, lang: str) -> dict | None:
    c, start = REGISTRY[cid], time.time()
    try:
        r = c.attack(text, lang)
        plain = r["plaintext"]
    except Exception as exc:  # a method that cannot apply to this text simply reports that
        return {"kind": "failed", "cipher": c.name, "cid": cid, "lang": lang, "reason": type(exc).__name__}
    if not isinstance(plain, str) or len(letters(plain)) < 4:
        return {"kind": "failed", "cipher": c.name, "cid": cid, "lang": lang, "reason": "no text produced"}
    return {"kind": "attempt", "cid": cid, "cipher": c.name, "family": c.family, "lang": lang, "rank": list(REGISTRY).index(cid), "method": r.get("method") or c.attack_name, "key": str(r.get("key"))[:240], "plaintext": plain[:900], "seconds": round(time.time() - start, 2), **S.readable(plain, lang)}


def shuffled(text: str, seed: int) -> str:
    t = list(letters(text))
    random.Random(seed).shuffle(t)
    return "".join(t)


def null_run(cid: str, text: str, lang: str, seed: int) -> dict:
    try:
        return {"kind": "null", "coverage": S.readable(REGISTRY[cid].attack(shuffled(text, seed), lang)["plaintext"], lang)["coverage"]}
    except Exception:  # treated as no evidence from this shuffle
        return {"kind": "null", "coverage": None}


def symbols(raw: str, lang: str) -> dict:
    """Numbers or unusual symbols, solved as a homophonic substitution of the tokens."""
    from .attacks.classical import solve_symbols
    toks = re.findall(r"\d+", raw) if re.search(r"\d", raw) and not re.search(r"[A-Za-z]", raw) else list(re.sub(r"\s+", "", raw))
    start = time.time()
    r = solve_symbols(toks, lang, homophonic=True, iters=800000, restarts=3)
    return {"kind": "attempt", "cid": "", "cipher": "Homophonic symbols", "family": "Book and homophonic", "lang": lang, "method": r["method"], "key": str(r.get("key"))[:240], "plaintext": r["plaintext"][:900], "seconds": round(time.time() - start, 2), **S.readable(r["plaintext"], lang)}


def word_beam(raw: str) -> dict:
    """A French dictionary search that uses the printed word breaks, for letters mixed with digits."""
    from .mysteries.figaro_digit_words import solve
    start = time.time()
    r = solve(re.sub(r"[^A-Z0-9 ]", "", raw.upper()))
    plain = "".join(r["words"]).replace(".", "")
    return {"kind": "attempt", "cid": "", "cipher": "Word-break dictionary search", "family": "Dictionary", "lang": "fr", "method": "beam search over French words, digits may share letters", "key": "", "plaintext": " ".join(r["words"])[:900], "seconds": round(time.time() - start, 2), **S.readable(plain, "fr")}


def trace(name: str, raw: str, lang: str) -> dict:
    fn = {"caesar": S.caesar_sweep, "vigenere": S.vigenere_columns, "climb": S.climb, "frequency": S.frequency_guess}[name]
    return {"kind": "trace", "name": name, "lang": lang, "data": fn(raw, lang)}


def job(spec: tuple):
    kind, *args = spec
    return {"attack": attack, "null": null_run, "symbols": symbols, "beam": word_beam, "trace": trace}[kind](*args)
