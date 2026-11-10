"""Sign-by-sign transliteration of deciphered scripts, and spelling Latin text in them.

Reading gives every sign's conventional value(s), its Unicode name and, for Egyptian, its Gardiner number and kind
(uniliteral, biliteral, triliteral, or a logogram/determinative with no phonetic value in the tables). Writing spells
Latin letters with one-sound signs only (uniliterals for Egyptian), as modern name-in-hieroglyphs charts do; that is a
convention of ours, not how the ancient scripts were used, and the output says so."""
import unicodedata

from .signs import SCRIPTS, script_of, tables

PLAIN = {"ꜣ": "a", "ꜥ": "a", "ı͗": "i", "ỉ": "i", "ḥ": "h", "ḫ": "kh", "ẖ": "kh", "š": "sh", "ḳ": "q", "ṯ": "tj", "ḏ": "dj", "þ": "th",
         "ʔ/ʾ": "'", "ả": "a", "ʿ": "'", "ś": "s"}


def from_codes(text: str) -> str | None:
    """Text made only of Gardiner numbers (e.g. 'G1 D21-N35') becomes the signs; otherwise None."""
    import re

    codes = [c for c in re.split(r"[\s\-:*]+", text.strip()) if c]
    if not codes or not all(re.fullmatch(r"(?:[A-Z]|Aa)\d{1,3}[A-Za-z]?", c) for c in codes):
        return None
    index = {e["code"]: ch for ch, e in tables()["egyptian"].items() if e.get("code")}
    return "".join(index.get(c, "?") for c in codes)


def read(text: str) -> dict:
    """Tokens for every character, the transliteration per script, and counts. Gardiner numbers are accepted too."""
    coded = from_codes(text)
    text = coded if coded is not None else text
    t, tokens, line = tables(), [], []
    for ch in text:
        s = script_of(ch)
        if s is None:
            tokens.append({"sign": ch, "script": None})
            line.append(ch if not ch.isspace() else " ")
            continue
        e = t[s].get(ch, {})
        vals = e.get("values", [])
        tok = {"sign": ch, "script": s, "name": e.get("name", unicodedata.name(ch, "").title()), "values": vals, "source": e.get("source", "")}
        if s == "egyptian":
            tok.update(code=e.get("code", ""), kind=e.get("kind", ""))
            line.append(vals[0] if vals else f"[{e.get('code', '?')}]")
            line.append(".") if vals else None
        else:
            line.append(vals[0] if vals else "?")
        tokens.append(tok)
    out = "".join(line).replace(".]", "]").replace(". ", " ").strip(".")
    used = sorted({x["script"] for x in tokens if x["script"]})
    return {"tokens": tokens, "transliteration": out, "from_codes": coded, "simple": "".join(PLAIN.get(c, c) for c in out), "scripts": used,
            "signs": sum(1 for x in tokens if x["script"]), "unknown": sum(1 for x in tokens if x["script"] and not x["values"])}


PREFER = {"egyptian": {"a": "\U0001313F", "s": "\U000132F4"}}  # vulture G1 for a, folded cloth S29 for s (usual chart choices)


def alphabet(script: str) -> dict:
    """Latin letter -> sign, using one-sound signs only (Egyptian uniliterals). Signs from a recorded table come
    before signs valued only by their Unicode name, exact letters before letters with diacritics."""
    out = dict(PREFER.get(script, {}))
    items = sorted(tables()[script].items(), key=lambda kv: (kv[1].get("source", "").startswith("Unicode"),
                                                            not any(len(v) == 1 and v.isascii() for v in kv[1].get("values", [])), ord(kv[0])))
    for ch, e in items:
        if script == "egyptian" and e.get("kind") != "uniliteral" or script == "runic" and e.get("source") != "Elder Futhark table":
            continue
        for v in e.get("values", []):
            plain = PLAIN.get(v, v)
            base = unicodedata.normalize("NFD", plain)[0].lower() if plain else ""
            if len(plain) == 1 and base.isalpha() and base not in out:
                out[base] = ch
    return out


SUBSTITUTE = {"egyptian": {"e": "i", "o": "w", "u": "w", "l": "r", "v": "f", "c": "k", "x": "ks", "z": "s", "j": "dj"},
              "runic": {"c": "k", "q": "k", "v": "w", "x": "ks", "y": "j"}, "ogham": {"k": "c", "p": "b", "y": "i", "j": "i", "w": "u", "x": "cs", "v": "f"},
              "phoenician": {"a": "", "e": "", "i": "", "o": "", "u": "", "c": "k", "f": "p", "v": "w", "x": "ks", "j": "y"},
              "gothic": {"c": "k", "y": "i", "x": "ks", "v": "w"}}


def write(text: str, script: str) -> dict:
    if script not in SCRIPTS:
        raise ValueError(f"Unknown script {script}")
    alpha, sub = alphabet(script), SUBSTITUTE.get(script, {})
    out, notes = [], []
    for c in text.lower():
        if c in alpha:
            out.append(alpha[c])
        elif c in sub:
            rep = sub[c]
            out.append("".join(alpha.get(x, "") for x in rep))
            notes.append(f"{c} -> {rep or 'left out'}")
        elif c.isalpha():
            out.append("?")
            notes.append(f"{c}: no sign")
        else:
            out.append(c)
    return {"script": script, "text": "".join(out), "substitutions": sorted(set(notes)), "alphabet": alpha,
            "note": "Spelled letter by letter with one-sound signs: a modern convention, not ancient usage."}


def catalogue(script: str, limit: int = 2000) -> list[dict]:
    """Signs for the palette: Egyptian phonetic signs first, then the rest."""
    t = tables()[script]
    order = {"uniliteral": 0, "biliteral": 1, "triliteral": 2}
    items = sorted(t.items(), key=lambda kv: (order.get(kv[1].get("kind", ""), 3), ord(kv[0])))
    return [{"sign": ch, "values": e.get("values", []), "name": e.get("name", ""), "code": e.get("code", ""), "kind": e.get("kind", "")} for ch, e in items[:limit]]
