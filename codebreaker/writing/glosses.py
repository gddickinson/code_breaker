"""Word glosses for Egyptian, Mycenaean Greek (Linear B) and Old Norse, from Wiktionary lemma pages (Round 77).

Source: data/sources/glosses/<lang>.json (fetched by scripts/fetch_glosses.py; CC BY-SA 4.0, Wiktionary). A gloss is
the dictionary meaning of a word looked up on its own: no grammar, no word order, no choice between senses. It is
never a translation, and the output says so. Egyptian is written without word breaks, so its consonants are cut into
dictionary words by a longest-cover search, and every cut is shown as one possibility among others.

Positive control and null: the quotations inside the entries (transliterated sentences with a published translation)
are glossed word by word; the share of their words found in the dictionary is compared with the same share for
strings of the same lengths drawn at random from the same letters."""
import json
import random
import re
import unicodedata
from functools import lru_cache

from ..languages import ROOT
from .wikitext import clean

SRC = ROOT / "data/sources/glosses"
LANGS = {"egyptian": "Egyptian", "mycenaean": "Mycenaean Greek", "old_norse": "Old Norse"}
NOTE = "Glosses give each word's dictionary meanings on its own. They are not a translation: grammar, word order and the choice of sense are left to the reader."


def norm(word: str, lang: str) -> str:
    """Spelling variants folded together: Egyptian i/j/yod forms, Old Norse accents kept but case dropped."""
    w = unicodedata.normalize("NFC", word.strip().lower())
    if lang == "egyptian":
        w = w.replace("ı͗", "j").replace("ỉ", "j").replace("i͗", "j").replace("ś", "s").replace(".", "").replace("-", "")
        w = re.sub(r"[()\[\]⸗=]", "", w)
    return w


def senses(section: str) -> list[dict]:
    out, pos = [], ""
    for line in section.splitlines():
        h = re.match(r"^={3,5}\s*([^=]+?)\s*={3,5}$", line)
        if h:
            pos = h.group(1)
            continue
        if re.match(r"^#\s", line):
            labels = re.findall(r"\{\{lb\|[^|}]+\|([^}]*)\}\}", line)
            text = clean(re.sub(r"\{\{lb\|[^}]*\}\}", "", line[1:]))
            if text:
                out.append({"pos": pos, "sense": text, "labels": [l.replace("|", ", ") for l in labels]})
    return out


def forms(title: str, section: str, lang: str) -> set[str]:
    """Spellings under which the entry can be found: its title, Mycenaean transcriptions, Old Norse runic forms."""
    f = {norm(title, lang)}
    if lang == "mycenaean":
        f |= {norm(m, lang) for m in re.findall(r"\|ts=([^|}]+)", section)}
    if lang == "old_norse":
        f |= {m for m in re.findall(r"\{\{alt\|non\|([ᚠ-᛿]+)", section)}
    return {x for x in f if x}


@lru_cache(maxsize=3)
def dictionary(lang: str) -> dict:
    """{spelling: [{"word", "pos", "sense", "labels"}]}."""
    data = json.loads((SRC / f"{lang}.json").read_text())
    out = {}
    for title, sec in data.items():
        ss = senses(sec)
        if not ss:
            continue
        for f in forms(title, sec, lang):
            out.setdefault(f, []).extend({"word": title, **s} for s in ss[:6])
    return out


def segment(consonants: str, lang: str = "egyptian", longest: int = 7) -> list[str]:
    """Cut an unbroken Egyptian transliteration into dictionary words, maximising the letters covered (ties: fewer words)."""
    d, s = dictionary(lang), norm(consonants, lang)
    best = [(0, 0, [])] + [None] * len(s)
    for i in range(len(s)):
        if best[i] is None:
            continue
        cov, n, path = best[i]
        for j in range(i + 1, min(len(s), i + longest) + 1):
            piece = s[i:j]
            c = cov + (len(piece) if piece in d else 0)
            cand = (c, n + 1, path + [piece])
            if best[j] is None or (c, -cand[1]) > (best[j][0], -best[j][1]):
                best[j] = cand
    return best[-1][2] if s else []


def gloss(text: str, lang: str) -> dict:
    """Each word with its dictionary senses; Egyptian text without spaces is segmented first."""
    d = dictionary(lang)
    words = [w for w in re.split(r"[\s\U00010100\U00010101·:;,]+", text) if w]
    if lang == "egyptian" and len(words) == 1 and norm(words[0], lang) not in d:
        words = segment(words[0], lang)
    rows = [{"word": w, "found": norm(w, lang) in d, "senses": d.get(norm(w, lang), [])[:4]} for w in words]
    return {"lang": lang, "words": rows, "found": sum(r["found"] for r in rows), "of": len(rows), "note": NOTE,
            "source": "Wiktionary (CC BY-SA 4.0), lemma pages fetched 2026-11-10"}


def quotations(lang: str, limit: int = 300) -> list[dict]:
    """Published example sentences in the entries: transliteration (tr=) and translation (t=)."""
    data, out = json.loads((SRC / f"{lang}.json").read_text()), []
    for title, sec in data.items():
        for tr, t in re.findall(r"\|tr=([^|\n]+)\n?\|t=([^|\n}]+)", sec):
            tr = clean(tr)
            if len(tr.split()) >= 4:
                out.append({"entry": title, "tr": tr, "t": clean(t)})
    random.Random(77).shuffle(out)
    return out[:limit]


def control(lang: str, trials: int = 20, seed: int = 77) -> dict:
    """Share of words found in real quotations against random strings of the same lengths from the same letters."""
    qs = quotations(lang)
    d, rnd = dictionary(lang), random.Random(seed)
    words = [norm(w, lang) for q in qs for w in re.split(r"[\s,;:]+", q["tr"]) if norm(w, lang)]
    if not words:
        return {"lang": lang, "quotations": 0}
    real = sum(w in d for w in words) / len(words)
    letters = [c for w in words for c in w]
    null = []
    for _ in range(trials):
        fake = ["".join(rnd.choice(letters) for _ in w) for w in words]
        null.append(sum(w in d for w in fake) / len(fake))
    return {"lang": lang, "quotations": len(qs), "words": len(words), "found_real": round(real, 3), "found_random_mean": round(sum(null) / trials, 3),
            "found_random_max": round(max(null), 3)}
