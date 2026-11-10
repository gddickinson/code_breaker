"""The visible stages of a crack: inspecting the text, decoding encodings, and worked traces of key attacks."""
import base64
import binascii
import re
from collections import Counter

import numpy as np

from . import analysis
from .attacks.classical import solve_symbols
from .languages import LANGS, detect, model, score
from .segment import segment
from .text import A, letters, to_ints, to_text
from .validation import coverage


NATURAL_SCORE = -5.2  # 95% of real 8-30 letter samples score above -4.7, 99% of random ones below -5.5


def inspect(raw: str) -> dict:
    """What the text is made of, before any statistics."""
    compact = re.sub(r"\s+", "", raw)
    kinds = {"letters": sum(c.isalpha() for c in compact), "digits": sum(c.isdigit() for c in compact), "other": sum(not c.isalnum() for c in compact)}
    words = raw.split()
    notes = []
    n = len(letters(raw))
    if n < 25 and kinds["digits"] < 25:
        notes.append("This is very short. Several different keys can produce plausible text, so treat any reading with caution.")
    if kinds["digits"] and kinds["letters"]:
        notes.append("Letters and digits are mixed, so digits may stand for letters.")
    if len(words) > 1 and kinds["letters"]:
        notes.append(f"Spaces are present: {len(words)} groups. Word breaks may be real, which helps a dictionary search.")
    return {"length": len(compact), "symbols": len(set(compact.upper())), "kinds": kinds, "groups": len(words), "notes": notes, "letters": n}


def plain_check(raw: str) -> list[dict]:
    t = letters(raw)[:500]
    return [{"lang": c, "name": LANGS[c], "coverage": round(coverage(t, c), 3), "score": round(score(t, c), 3)} for c in LANGS] if len(t) >= 8 else []


def printable(b: bytes) -> str | None:
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return s if s and sum(c.isprintable() or c.isspace() for c in s) / len(s) > 0.95 else None


def script_layer(raw: str) -> dict | None:
    """Text in other scripts (Round 76). Signs of a known script whose values are distinct single letters are
    transliterated; otherwise unfamiliar symbols (26 or fewer kinds) are relabelled A, B, C... by first appearance,
    so the substitution attacks can run on them. Returns an encoding entry or None."""
    from .writing.signs import SCRIPTS, script_of, tables
    from .writing.transliterate import PLAIN

    compact = re.sub(r"\s+", "", raw)
    odd = [c for c in compact if ord(c) > 0x2FF]
    if len(odd) < 8 or len(odd) < 0.8 * len(compact):
        return None
    kinds = sorted(set(odd), key=odd.index)
    known = {c: script_of(c) for c in kinds}
    if all(known.values()):
        t = tables()
        vals = {c: PLAIN.get(v, v).upper() for c in kinds for v in (t[known[c]][c].get("values") or ["?"])[:1]}
        if all(re.fullmatch(r"[A-Z]", v) for v in vals.values()) and len(set(vals.values())) == len(vals):
            names = sorted({SCRIPTS[s][0] for s in known.values()})
            return {"name": f"{', '.join(names)} transliterated", "text": "".join(vals.get(c, c) for c in raw), "strict": True}
    if len(kinds) <= 26:
        lab = {c: A[i] for i, c in enumerate(kinds)}
        return {"name": f"{len(kinds)} kinds of symbol relabelled as letters", "text": "".join(lab.get(c, c) for c in raw), "strict": True}
    return None


def encodings(raw: str) -> list[dict]:
    """Reversible encodings that need no key."""
    compact = re.sub(r"\s+", "", raw)
    out = []
    def add(name, text, strict=True):
        if text and len(letters(text)) >= 4:
            out.append({"name": name, "text": text, "strict": strict})
    sl = script_layer(raw)
    if sl:
        add(sl["name"], sl["text"])
    if re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", compact or "!") and len(compact) % 4 == 0 and len(compact) >= 8:
        try:
            add("Base64", printable(base64.b64decode(compact, validate=True)))
        except binascii.Error:
            pass
    if re.fullmatch(r"(?:[0-9a-fA-F]{2})+", compact or "!"):
        add("Hexadecimal bytes", printable(bytes.fromhex(compact)))
    if compact and set(compact) <= set("01") and len(compact) % 8 == 0:
        add("Binary bytes", printable(bytes(int(compact[i:i + 8], 2) for i in range(0, len(compact), 8))))
    nums = re.findall(r"\d+", raw)
    if len(nums) >= 4 and all(32 <= int(n) < 127 for n in nums) and not re.search(r"[A-Za-z]", raw):
        add("Decimal character codes", "".join(chr(int(n)) for n in nums))
    if len(letters(raw)) >= 8:
        add("Reversed text", raw[::-1], False)
        if len(raw.split()) > 2:
            add("Reversed word order", " ".join(reversed(raw.split())), False)
    return out


def natural(text: str) -> dict | None:
    """The language a text reads as, or None. The score limit separates short real text from random letters."""
    t = letters(text)
    if len(t) < 6:
        return None
    best = max(LANGS, key=lambda c: score(t, c))
    return {"lang": best, "name": LANGS[best]} if score(t, best) >= NATURAL_SCORE or coverage(t[:500], best) >= 0.6 else None


def caesar_sweep(raw: str, lang: str) -> dict:
    t = to_ints(raw)
    rows = sorted(((score(to_text((t - k) % 26), lang), k) for k in range(26)), reverse=True)
    best = rows[0][1]
    by = sorted((k, round(s, 3)) for s, k in rows)
    return {"bars": [{"label": str(k), "value": s} for k, s in by], "best": best, "best_text": to_text((t - best) % 26)[:120], "top": [{"shift": k, "score": round(s, 3), "text": to_text((t - k) % 26)[:60]} for s, k in rows[:5]]}


def periods(raw: str) -> dict:
    t = to_ints(raw)
    rows = analysis.period_ic(t) if len(t) > 6 else []
    return {"bars": [{"label": str(r["period"]), "value": round(r["ic"], 4)} for r in rows[:24]], "kasiski": dict(list(analysis.kasiski(letters(raw)).items())[:8]), "ic": round(analysis.ic(t), 4)}


def vigenere_columns(raw: str, lang: str) -> dict | None:
    """Treat each key position as its own Caesar cipher, for the period that fits best."""
    t = to_ints(raw)
    rows = [r for r in (analysis.period_ic(t) if len(t) > 20 else []) if r["period"] >= 2 and len(t) / r["period"] >= 6]
    if not rows:
        return None
    period = max(rows, key=lambda r: r["ic"] - 0.0006 * r["period"])["period"]
    p = np.asarray(model(lang)["letter"], dtype=float)
    p = p / p.sum()
    cols, key = [], []
    for i in range(period):
        c = t[i::period]
        counts = np.bincount(c, minlength=26)
        fit = [float(((np.roll(counts, -k) / max(len(c), 1)) * p).sum()) for k in range(26)]
        k = int(np.argmax(fit))
        key.append(k)
        cols.append({"position": i + 1, "letters": len(c), "shift": k, "key": A[k], "fit": round(fit[k], 4)})
    ks = np.array(key)
    plain = to_text((t - ks[np.arange(len(t)) % period]) % 26)
    return {"period": period, "key": "".join(A[k] for k in key), "columns": cols, "text": plain[:200], "score": round(score(plain, lang), 3)}


def climb(raw: str, lang: str, seed: int = 3) -> list[dict]:
    """A substitution solver stopped early and allowed longer, so the reading can be seen emerging."""
    t = letters(raw)
    out = []
    for iters in (200, 2000, 20000, 120000):
        r = solve_symbols(t, lang, iters=iters, restarts=2, seed=seed)
        out.append({"iterations": iters, "score": round(score(r["plaintext"], lang), 3), "text": r["plaintext"][:110]})
    return out


def frequency_guess(raw: str, lang: str) -> dict:
    """The classroom first step: map the commonest letters onto the commonest of the language."""
    t = letters(raw)
    freq = [c for c, _ in Counter(t).most_common()]
    common = [A[i] for i in np.argsort(-np.asarray(model(lang)["letter"]))]
    m = dict(zip(freq, common))
    return {"pairs": [{"cipher": c, "plain": m[c], "count": t.count(c)} for c in freq[:10]], "text": "".join(m.get(c, c) for c in t)[:120]}


def language_guess(raw: str) -> list[dict]:
    return detect(raw) if len(letters(raw)) > 3 else []


def readable(text: str, lang: str) -> dict:
    t = letters(text)[:500]
    return {"coverage": round(coverage(t, lang), 3), "score": round(score(t, lang), 3), "spaced": segment(t, lang)}
