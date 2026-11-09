"""Lost-script lab: what can statistics say about texts in unknown languages?"""
import re
from collections import Counter

from ..analysis import conditional_entropy, entropy
from ..languages import LANGS, ROOT, corpus_text
from ..text import letters, strip_accents

LAB = ROOT / "data/sources/scripts_lab"


def phaistos() -> list[list[str]]:
    raw = (ROOT / "data/sources/research/wp_phaistos.txt").read_text()
    words = []
    for m in re.findall(r'font-size:140%;">([^<]*)</span>', raw[raw.index("'''Side A''':"):raw.index("====Pictorial====")]):
        for w in re.split(r"[|¦]", m):
            signs = [c for c in w if 0x101D0 <= ord(c) <= 0x101FC and ord(c) != 0x101FD]
            if signs:
                words.append(signs)
    return words


def linear_a() -> list[list[str]]:
    raw = (LAB / "lineara.js").read_text(errors="ignore")
    out = []
    for block in re.findall(r'"transliteratedWords": \[(.*?)\]', raw, flags=re.S):
        for w in re.findall(r'"([^"\\]+)"', block):
            parts = w.split("-")
            if len(parts) >= 2 and all(re.fullmatch(r"[A-Z]+[₀-₉]?", p) for p in parts):
                out.append(parts)
    return out


def liber_primus() -> list[list[str]]:
    raw = (LAB / "liberprimus.txt").read_text(errors="ignore")
    return [list(w) for w in re.split(r"[^ᚠ-᛿]+", raw) if w]


def chao1(counts: Counter) -> float:
    """Estimated total inventory, counting signs not yet seen, from singletons and doubletons."""
    f1, f2 = sum(v == 1 for v in counts.values()), sum(v == 2 for v in counts.values())
    return round(len(counts) + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2), 1)


def writing_class(inventory: float) -> str:
    if inventory < 40:
        return "alphabet-sized"
    if inventory < 150:
        return "syllabary-sized"
    return "logographic or mixed"


def profile(words: list[list[str]]) -> dict:
    seq = [s for w in words for s in w]
    c = Counter(seq)
    first = Counter(w[0] for w in words)
    lens = [len(w) for w in words]
    top = first.most_common(1)[0]
    return {"tokens": len(seq), "words": len(words), "signs": len(c), "estimated_inventory": chao1(c), "class": writing_class(chao1(c)), "h1": round(entropy(seq), 3), "h2": round(conditional_entropy(seq), 3),
            "mean_word_length": round(sum(lens) / len(lens), 2), "singleton_share": round(sum(v == 1 for v in c.values()) / len(c), 3), "top_initial_sign": top[0], "top_initial_share": round(top[1] / len(words), 3),
            "distinct_words": len({tuple(w) for w in words}), "repeated_word_share": round(1 - len({tuple(w) for w in words}) / len(words), 3)}


def run() -> dict:
    res = {"id": "scriptlab", "scripts": {"Phaistos Disc": profile(phaistos()), "Linear A": profile(linear_a()), "Liber Primus": profile(liber_primus())}, "baselines": {}}
    for code, name in LANGS.items():
        w = [list(letters(x)) for x in strip_accents(corpus_text(code)).split()[:6000]]
        res["baselines"][name] = profile([x for x in w if x])
    return res
