"""Sign tables for deciphered scripts, built only from recorded sources.

Sources: the raw Wikipedia pages in data/sources/scripts (listed with URLs and dates in sources.json) and the Unicode
character names shipped with Python (unicodedata, Unicode 15). Each sign records where its value came from. Values are
conventional transliterations, not pronunciations; Egyptian writes consonants only."""
import json
import re
import unicodedata
from functools import lru_cache

from ..languages import ROOT
from .wikitext import clean, rows

SRC = ROOT / "data/sources/scripts"
SCRIPTS = {
    "egyptian": ("Egyptian hieroglyphs", "EGYPTIAN HIEROGLYPH ", (0x13000, 0x1342F)),
    "linear_b": ("Linear B", "LINEAR B ", (0x10000, 0x100FA)),
    "runic": ("Runes", "RUNIC ", (0x16A0, 0x16F8)),
    "ogham": ("Ogham", "OGHAM ", (0x1680, 0x169C)),
    "phoenician": ("Phoenician", "PHOENICIAN ", (0x10900, 0x1091F)),
    "gothic": ("Gothic", "GOTHIC ", (0x10330, 0x1034A)),
    "ugaritic": ("Ugaritic", "UGARITIC ", (0x10380, 0x1039F)),
    "old_persian": ("Old Persian cuneiform", "OLD PERSIAN ", (0x103A0, 0x103D5)),
    "cuneiform": ("Sumero-Akkadian cuneiform", "CUNEIFORM ", (0x12000, 0x1254F)),
}


def _page(name: str) -> str:
    return (SRC / f"wp_{name}.txt").read_text()


def gardiner(ch: str) -> str:
    """'EGYPTIAN HIEROGLYPH A001' -> 'A1'; 'EGYPTIAN HIEROGLYPH AA001' -> 'Aa1'; suffix letters kept."""
    m = re.match(r"EGYPTIAN HIEROGLYPH ([A-Z]+)0*(\d+)([A-Z]*)$", unicodedata.name(ch, ""))
    if not m:
        return ""
    cat = m.group(1) if len(m.group(1)) == 1 else m.group(1)[0] + m.group(1)[1:].lower()
    return f"{cat}{m.group(2)}{m.group(3)}"


def _egyptian() -> dict:
    out = {}
    for r in rows(_page("egyptian_transliteration")):
        c = [clean(x) for x in r]
        if len(c) >= 15 and len(c[0]) == 1 and 0x13000 <= ord(c[0]) <= 0x1342F:
            vals = [v.strip(" ()") for v in re.split(r"\s+(?=\()", c[5]) if v.strip(" ()")]
            out[c[0]] = {"values": vals, "kind": "uniliteral", "mdc": c[7], "say": c[-1], "source": "Transliteration of Ancient Egyptian (Gardiner 1957 column)"}
    for page, kind in (("egyptian_bi", "biliteral"), ("egyptian_tri", "triliteral")):
        for r in rows(_page(page)):
            c = [clean(x) for x in r]
            code = next((x for x in c if re.fullmatch(r"U\+13[0-9A-F]{3}", x)), None)
            if not code:
                continue
            ch = chr(int(code[2:], 16))
            vals = [v.strip() for v in c[c.index(code) + (2 if kind == "biliteral" else 2)].split(",") if v.strip()]
            if ch not in out and vals:
                out[ch] = {"values": vals, "kind": kind, "source": f"Egyptian {kind} signs"}
    return out


def _grid(page: str, block: tuple[int, int]) -> dict:
    """Tables with a row of glyphs followed by a row of transliterations (Elder Futhark)."""
    out, rs = {}, rows(_page(page))
    for a, b in zip(rs, rs[1:]):
        ca, cb = [clean(x) for x in a], [clean(x) for x in b]
        if ca and ca[0] == "rune" and cb and cb[0] == "transliteration":
            for g, v in zip(ca[1:], cb[1:]):
                if len(g) == 1 and block[0] <= ord(g) <= block[1] and v:
                    out[g] = v
    return out


def _column(page: str, block: tuple[int, int], offset: int) -> dict:
    """Tables with one sign per row: the value sits offset cells after the glyph."""
    out = {}
    for r in rows(_page(page)):
        c = [clean(x) for x in r]
        i = next((k for k, x in enumerate(c) if len(x) == 1 and block[0] <= ord(x) <= block[1]), None)
        if i is not None and i + offset < len(c) and c[i + offset] and c[i] not in out:
            out[c[i]] = c[i + offset].split(" (")[0].strip()
    return out


def _from_name(script: str, ch: str) -> str:
    name = unicodedata.name(ch, "")
    rest = name[len(SCRIPTS[script][1]):]
    if script == "linear_b":
        m = re.match(r"SYLLABLE B\d+ (\S+)$", rest)
        if m:
            return m.group(1).lower()
        m = re.match(r"(?:IDEOGRAM|MONOGRAM) B\d+\w* (.+)$", rest)
        if m:
            return f"[{m.group(1).lower()}]"
        m = re.match(r"SYMBOL B(\d+)", rest)
        return f"*{int(m.group(1))}" if m else ""
    if script == "old_persian":
        return rest.split("SIGN ", 1)[-1].lower() if rest.startswith("SIGN ") and len(rest.split()) == 2 else rest.lower()
    if script == "cuneiform":
        return rest.split("SIGN ", 1)[-1].lower() if rest.startswith("SIGN ") else ""
    if script == "runic":
        tok = rest.split()[-1]
        return tok.lower() if rest.startswith("LETTER") and len(tok) <= 2 and tok.isalpha() else ""
    return ""


@lru_cache(maxsize=1)
def tables() -> dict:
    """{script: {char: {"value", "name", "source", ...}}} for every named sign in each script's block."""
    found = {"egyptian": _egyptian(),
             "runic": {k: {"values": [v], "source": "Elder Futhark table"} for k, v in _grid("elder_futhark", SCRIPTS["runic"][2]).items()},
             "ogham": {k: {"values": [v], "source": "Ogham table"} for k, v in _column("ogham", SCRIPTS["ogham"][2], 2).items()},
             "phoenician": {k: {"values": [v], "source": "Phoenician alphabet table"} for k, v in _column("phoenician", SCRIPTS["phoenician"][2], 4).items()},
             "gothic": {k: {"values": [v], "source": "Gothic alphabet table"} for k, v in _column("gothic", SCRIPTS["gothic"][2], 1).items()},
             "ugaritic": {k: {"values": [v], "source": "Ugaritic alphabet table"} for k, v in _column("ugaritic", SCRIPTS["ugaritic"][2], 1).items()}}
    out = {}
    for s, (_, prefix, (lo, hi)) in SCRIPTS.items():
        tab = {}
        for cp in range(lo, hi + 1):
            ch = chr(cp)
            name = unicodedata.name(ch, "")
            if not name.startswith(prefix):
                continue
            e = dict(found.get(s, {}).get(ch, {}))
            if not e:
                v = _from_name(s, ch)
                e = {"values": [v] if v else [], "source": "Unicode character name" if v else ""}
            e["name"] = name.title()
            if s == "egyptian":
                e["code"] = gardiner(ch)
                e.setdefault("kind", "logogram or determinative" if not e["values"] else "")
            tab[ch] = e
        out[s] = tab
    return out


def script_of(ch: str) -> str | None:
    name = unicodedata.name(ch, "")
    return next((s for s, (_, prefix, _) in SCRIPTS.items() if name.startswith(prefix)), None)


def summary() -> dict:
    t = tables()
    return {s: {"title": SCRIPTS[s][0], "signs": len(v), "with_value": sum(bool(e["values"]) for e in v.values())} for s, v in t.items()}


if __name__ == "__main__":
    print(json.dumps(summary(), indent=1))
