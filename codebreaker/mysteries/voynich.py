"""Voynich manuscript: structural statistics compared with natural languages and shuffles."""
import random
import re
from collections import Counter

import numpy as np

from ..analysis import conditional_entropy, entropy
from ..attacks.classical import solve_symbols
from ..languages import LANGS, ROOT, corpus_text
from ..text import letters, strip_accents

FILE = ROOT / "data/sources/vms_ZL3b-n.txt"
MULTI = ["cth", "ckh", "cph", "cfh", "ch", "sh", "iin", "ee"]


def parse() -> list[dict]:
    """Return one record per text line: folio, Currier language, illustration, and words."""
    out, meta = [], {}
    for line in FILE.read_text(errors="ignore").splitlines():
        if line.startswith("#"):
            continue
        m = re.match(r"<(f\w+)>\s+<!(.*?)>", line)
        if m:
            meta = dict(re.findall(r"\$(\w)=(\w+)", m.group(2)))
            continue
        m = re.match(r"<(f\w+)\.(\d+)[^>]*>\s*(.*)", line)
        if not m:
            continue
        text = re.sub(r"\{[^}]*\}", "", re.sub(r"<[^>]*>|@\d+;?", "", m.group(3)))
        text = text.replace(",", ".")
        words = [w for w in text.split(".") if w and re.fullmatch(r"[a-z]+", w)]
        if words:
            out.append({"folio": m.group(1), "lang": meta.get("L", "?"), "section": meta.get("I", "?"), "words": words})
    return out


def glyphs(words: list[str], merge: bool) -> list[str]:
    s = ".".join(words)
    if not merge:
        return [c for c in s if c != "."]
    pat = "|".join(MULTI) + "|."
    return [g for g in re.findall(pat, s) if g != "."]


def profile(symbols: list[str], words: list[str]) -> dict:
    lens = [len(w) for w in words]
    wc = Counter(words)
    freq = np.array(sorted(wc.values(), reverse=True), dtype=float)
    r = np.arange(1, len(freq) + 1)
    top = min(len(freq), 2000)
    slope = float(np.polyfit(np.log(r[:top]), np.log(freq[:top]), 1)[0])
    rep = sum(a == b for a, b in zip(words, words[1:])) / max(len(words) - 1, 1)
    return {"tokens": len(symbols), "alphabet": len(set(symbols)), "h1": round(entropy(symbols), 3), "h2": round(conditional_entropy(symbols), 3),
            "word_count": len(words), "vocabulary": len(wc), "mean_word_length": round(float(np.mean(lens)), 2), "zipf_slope": round(slope, 3),
            "adjacent_word_repeat_rate": round(rep, 4)}


def language_baseline(code: str, n_words: int, seed: int = 0) -> dict:
    words = [letters(w) for w in strip_accents(corpus_text(code)).split()]
    words = [w for w in words if w]
    r = random.Random(seed)
    s = r.randrange(0, max(1, len(words) - n_words))
    w = words[s: s + n_words]
    return profile(list("".join(w)), w)


def run() -> dict:
    recs = parse()
    words = [w for r in recs for w in r["words"]]
    res = {"id": "voynich", "lines": len(recs), "folios": len({r["folio"] for r in recs})}
    res["eva"] = profile(glyphs(words, False), words)
    res["glyph_merged"] = profile(glyphs(words, True), words)
    for lg in ("A", "B"):
        sub = [w for r in recs if r["lang"] == lg for w in r["words"]]
        res[f"currier_{lg}"] = profile(glyphs(sub, False), sub)
    a, b = Counter(w for r in recs if r["lang"] == "A" for w in r["words"]), Counter(w for r in recs if r["lang"] == "B" for w in r["words"])
    def share(c, w):
        return c[w] / sum(c.values()) * 1000
    tops = sorted(set(list(dict(a.most_common(150))) + list(dict(b.most_common(150)))), key=lambda w: -abs(share(a, w) - share(b, w)))[:12]
    res["a_b_diff"] = [{"word": w, "A_per_1000": round(share(a, w), 1), "B_per_1000": round(share(b, w), 1)} for w in tops]
    res["languages"] = {LANGS[c]: language_baseline(c, min(len(words), 30000)) for c in LANGS}
    shuf = list(glyphs(words, False))
    random.Random(1).shuffle(shuf)
    res["shuffled_h2"] = round(conditional_entropy(shuf), 3)
    sample = glyphs(words[:1200], True)
    alpha = sorted(set(sample))
    res["solver_trial"] = []
    for code in LANGS:
        real = solve_symbols(sample, code, len(alpha) > 26, iters=250000, restarts=3)
        s = list(sample)
        random.Random(2).shuffle(s)
        null = solve_symbols(s, code, len(alpha) > 26, iters=250000, restarts=3)
        res["solver_trial"].append({"language": LANGS[code], "score": real["score"], "shuffled_score": null["score"], "excerpt": real["plaintext"][:90]})
    return res
