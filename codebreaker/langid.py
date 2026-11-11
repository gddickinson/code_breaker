"""Language identification for ordinary text in about 50 languages (Round 85).

Character 1- to 3-gram naive Bayes over the Wikipedia samples in data/sources/langid (scripts/fetch_langid_text.py;
CC BY-SA 4.0). The first 80% of each language's articles train the profile and the last 20% (other articles) are the
test set (evaluate()). Cipher work keeps the 26-letter models in languages.py; this is for real text in any script."""
import json
import math
import re
from collections import Counter
from functools import lru_cache

import numpy as np

from .languages import ROOT

SRC = ROOT / "data/sources/langid"
MODEL = ROOT / "data/models/langid.json"
RESULT = ROOT / "data/results/langid.json"
NAMES = {"ar": "Arabic", "az": "Azerbaijani", "bg": "Bulgarian", "bn": "Bengali", "ca": "Catalan", "cs": "Czech", "da": "Danish", "de": "German",
         "el": "Greek", "en": "English", "eo": "Esperanto", "es": "Spanish", "et": "Estonian", "eu": "Basque", "fa": "Persian", "fi": "Finnish",
         "fr": "French", "ga": "Irish", "gl": "Galician", "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian", "id": "Indonesian", "it": "Italian",
         "ja": "Japanese", "ko": "Korean", "ky": "Kyrgyz", "la": "Latin", "lt": "Lithuanian", "lv": "Latvian", "ms": "Malay", "nb": "Norwegian",
         "nl": "Dutch", "pb": "Portuguese", "pl": "Polish", "ro": "Romanian", "ru": "Russian", "sk": "Slovak", "sl": "Slovene", "sq": "Albanian",
         "sv": "Swedish", "sw": "Swahili", "th": "Thai", "tl": "Tagalog", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu", "vi": "Vietnamese",
         "zh": "Chinese"}
TOP = 4000  # n-grams kept per language and order


def grams(text: str) -> Counter:
    t = " " + re.sub(r"[\d\W_]+", " ", text.lower()).strip() + " "
    c = Counter()
    for n in (1, 2, 3):
        c.update(t[i:i + n] for i in range(len(t) - n + 1) if t[i:i + n].strip())
    return c


def split(code: str) -> tuple[list[str], list[str]]:
    arts = [a for a in (SRC / f"{code}.txt").read_text().splitlines() if a.strip()]
    k = int(len(arts) * 0.8)
    return arts[:k], arts[k:]


def build() -> dict:
    model = {}
    for f in sorted(SRC.glob("*.txt")):
        train, _ = split(f.stem)
        c = grams(" ".join(train))
        total = {n: sum(v for g, v in c.items() if len(g) == n) for n in (1, 2, 3)}
        keep = {}
        for n in (1, 2, 3):
            best = sorted(((g, v) for g, v in c.items() if len(g) == n), key=lambda x: -x[1])[:TOP]
            keep.update({g: math.log(v / total[n]) for g, v in best})
        model[f.stem] = {"logp": keep, "floor": {str(n): math.log(0.5 / max(total[n], 1)) for n in (1, 2, 3)}}
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    MODEL.write_text(json.dumps(model))
    return model


@lru_cache(maxsize=1)
def model() -> dict:
    if not MODEL.exists() or MODEL.stat().st_mtime < max(f.stat().st_mtime for f in SRC.glob("*.txt")):
        return build()
    return json.loads(MODEL.read_text())


def detect(text: str, top: int = 5) -> list[dict]:
    """Languages ranked by fit, with probabilities that sum to 1 over the known languages."""
    m, g = model(), grams(text[:3000])
    if not g:
        return []
    scores = {}
    for code, lm in m.items():
        lp, fl = lm["logp"], lm["floor"]
        scores[code] = sum(v * lp.get(k, fl[str(len(k))]) for k, v in g.items())
    codes = list(scores)
    s = np.array([scores[c] for c in codes])
    p = np.exp((s - s.max()) / max(1.0, sum(g.values()) / 40))  # tempered, so short texts are not overconfident
    p /= p.sum()
    order = np.argsort(-p)[:top]
    return [{"lang": codes[i], "name": NAMES.get(codes[i], codes[i]), "p": round(float(p[i]), 3)} for i in order]


def evaluate(lengths=(20, 50, 200), per_lang: int = 40, seed: int = 85) -> dict:
    """Accuracy on held-out articles cut to each length, and the most frequent confusions."""
    rnd = np.random.default_rng(seed)
    res, conf = {}, Counter()
    for n in lengths:
        hit = tot = 0
        by = {}
        for f in sorted(SRC.glob("*.txt")):
            _, test = split(f.stem)
            text = " ".join(test)
            if len(text) < n + 10:
                continue
            ok = 0
            for _ in range(per_lang):
                i = int(rnd.integers(0, len(text) - n))
                guess = detect(text[i:i + n], 1)[0]["lang"]
                ok += guess == f.stem
                if guess != f.stem and n == 50:
                    conf[(f.stem, guess)] += 1
            by[f.stem] = round(ok / per_lang, 3)
            hit, tot = hit + ok, tot + per_lang
        res[str(n)] = {"accuracy": round(hit / tot, 3), "by_language": by}
    return {"id": "langid", "languages": len(list(SRC.glob("*.txt"))), "lengths": res,
            "top_confusions_at_50": [{"true": a, "guessed": b, "count": c} for (a, b), c in conf.most_common(12)]}


if __name__ == "__main__":
    build()
    model.cache_clear()
    r = evaluate()
    RESULT.write_text(json.dumps(r, indent=1))
    print({k: v["accuracy"] for k, v in r["lengths"].items()}, r["top_confusions_at_50"][:8])
