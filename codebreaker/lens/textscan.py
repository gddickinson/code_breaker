"""Hidden messages in text (Lens, Round 78b).

Checks: zero-width characters (U+200B, U+200C, U+200D, U+2060, U+FEFF) read as bits; spaces and tabs at line ends
read as bits (as whitespace-steganography tools write them); letters from another alphabet inside words (homoglyphs,
e.g. a Cyrillic 'а' among Latin letters); acrostics (first letters of lines or sentences, every n-th letter of words)
that contain dictionary words, compared with the same reading of the lines shuffled, so a long common word by chance is
not reported as a message."""
import random
import re
import unicodedata

from ..languages import LANGS, model

ZW = {"​": "0", "‌": "1", "‍": "1", "⁠": "0", "﻿": "0"}


def _bits_to_text(bits: str) -> str:
    out = "".join(chr(int(bits[i:i + 8], 2)) for i in range(0, len(bits) - 7, 8))
    return out if out and sum(c.isprintable() for c in out) > 0.8 * len(out) else ""


def zero_width(text: str) -> dict | None:
    found = [c for c in text if c in ZW]
    if not found:
        return None
    bits = "".join(ZW[c] for c in found)
    return {"count": len(found), "kinds": sorted({unicodedata.name(c) for c in found}), "as_text": _bits_to_text(bits)}


def trailing_whitespace(text: str) -> dict | None:
    lines = text.splitlines()
    tails = [re.search(r"[ \t]+$", l).group(0) for l in lines if re.search(r"[ \t]+$", l)]
    if len(tails) < 3:
        return None
    bits = "".join("0" if c == " " else "1" for t in tails for c in t)
    return {"lines": len(tails), "characters": sum(map(len, tails)), "as_text": _bits_to_text(bits)}


def homoglyphs(text: str) -> list[dict]:
    out = []
    for w in re.findall(r"\w{2,}", text):
        scripts = {unicodedata.name(c, "?").split()[0] for c in w if c.isalpha()}
        if len(scripts) > 1:
            odd = [c for c in w if c.isalpha() and unicodedata.name(c, "").split()[0] != "LATIN"]
            out.append({"word": w, "scripts": sorted(scripts), "foreign": "".join(odd)})
    return out[:50]


def _words(lang: str) -> frozenset:
    return frozenset(str(w).upper() for w in model(lang)["words"][:30000] if len(w) >= 4)


def _longest(s: str, vocab: frozenset) -> str:
    best = ""
    for i in range(len(s)):
        for j in range(i + 4, min(len(s), i + 14) + 1):
            if j - i > len(best) and s[i:j] in vocab:
                best = s[i:j]
    return best


def acrostics(text: str, langs=("en", "fr", "de", "it", "es", "la"), shuffles: int = 200, seed: int = 83) -> list[dict]:
    """Readings that hold a dictionary word of 5+ letters, kept only if the shuffled lines rarely hold one as long."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    readings = {"first letters of lines": [l[0] for l in lines if l[0].isalpha()],
                "last letters of lines": [l.rstrip(".,;:!?")[-1] for l in lines if l.rstrip(".,;:!?") and l.rstrip(".,;:!?")[-1].isalpha()],
                "first letters of sentences": [s[0] for s in sentences if s[0].isalpha()]}
    out, rnd = [], random.Random(seed)
    for name, chars in readings.items():
        s = unicodedata.normalize("NFD", "".join(chars)).encode("ascii", "ignore").decode().upper()
        if len(s) < 5:
            continue
        for lang in langs:
            if lang not in LANGS:
                continue
            vocab = _words(lang)
            w = _longest(s, vocab)
            if len(w) < 5:
                continue
            chars2 = list(s)
            hits = 0
            for _ in range(shuffles):
                rnd.shuffle(chars2)
                hits += len(_longest("".join(chars2), vocab)) >= len(w)
            p = (hits + 1) / (shuffles + 1)
            if p <= 0.01:
                out.append({"reading": name, "letters": s, "word": w, "lang": lang, "p": round(p, 4)})
    return out


def scan(text: str) -> list[dict]:
    findings = []
    z = zero_width(text)
    if z:
        findings.append({"kind": "zero_width", "label": f"{z['count']} invisible zero-width characters", "detail": z["as_text"] or ", ".join(z["kinds"])})
    t = trailing_whitespace(text)
    if t:
        findings.append({"kind": "whitespace", "label": f"spaces and tabs at the ends of {t['lines']} lines", "detail": t["as_text"] or f"{t['characters']} characters"})
    for h in homoglyphs(text):
        findings.append({"kind": "homoglyph", "label": f"'{h['word']}' mixes {', '.join(h['scripts'])} letters", "detail": h["foreign"]})
    best = {}
    for a in acrostics(text):  # one word per reading, the longest
        if a["reading"] not in best or len(a["word"]) > len(best[a["reading"]]["word"]):
            best[a["reading"]] = a
    for a in best.values():
        findings.append({"kind": "acrostic", "label": f"{a['reading']} spell '{a['word']}' ({LANGS[a['lang']]}, shuffled lines p={a['p']})", "detail": a["letters"]})
    if len(letters_only(text)) >= 120:  # longer texts: every reading, with the Bonferroni bar of the acrostic finder
        from ..acrostic import find

        for f in find(text, max_letters=300)["findings"][:3]:
            if f["reading"] not in best:
                findings.append({"kind": "acrostic", "label": f"{f['reading']} read as {f['language']} ({f['coverage']:.0%} in words, p={f['p']:.1e})", "detail": f["letters"][:120]})
    return findings


def letters_only(text: str) -> str:
    return "".join(c for c in text if c.isalpha())
