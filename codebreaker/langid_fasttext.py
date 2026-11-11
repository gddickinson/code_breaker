"""fastText language identification as an optional second identifier (Round 93); data/results/langid_fasttext.json.

Model: lid.176.ftz from fasttext.cc (Joulin et al. 2016; CC BY-SA 3.0; 938,013 bytes), loaded with the
fasttext-predict package (MIT), in data/models/fasttext (not committed). Compared with the app's own identifier
(langid.py) on the same held-out snippets of 20, 50 and 200 characters from the same 49 languages; fastText's answer is
restricted to those 49 (its other 127 labels are ignored). Combined: fastText's choice when it gives it 0.5 or more,
the app's otherwise. Caveat: fastText was trained partly on Wikipedia, as the snippets were, so it may have seen some."""
import json
from functools import lru_cache

import numpy as np

from . import langid
from .languages import ROOT

MODEL = ROOT / "data/models/fasttext/lid.176.ftz"
RESULT = ROOT / "data/results/langid_fasttext.json"
CODES = {"no": "nb", "pt": "pb"}  # fastText's codes -> the app's


@lru_cache(maxsize=1)
def _model():
    if not MODEL.exists():
        return None
    import fasttext

    return fasttext.load_model(str(MODEL))


def available() -> bool:
    return _model() is not None


def detect(text: str, top: int = 3) -> list[dict]:
    """fastText's ranking over the app's languages: [{'lang', 'p'}]."""
    m = _model()
    if m is None:
        return []
    labels, probs = m.predict(" ".join(text.split()), k=176)
    out = []
    for l, p in zip(labels, probs):
        c = l.replace("__label__", "")
        c = CODES.get(c, c)
        if c in langid.NAMES:
            out.append({"lang": c, "name": langid.NAMES[c], "p": round(float(p), 4)})
        if len(out) >= top:
            break
    return out


def combined(text: str) -> str:
    f = detect(text, 1)
    if f and f[0]["p"] >= 0.5:
        return f[0]["lang"]
    return langid.detect(text, 1)[0]["lang"]


def lens_name(text: str, p_min: float = 0.8) -> tuple[str | None, str]:
    """The Lens rule: the app's identifier names the language at p >= 0.8; if it does not, fastText may, at p >= 0.8."""
    g = langid.detect(text, 1)
    if g and g[0]["p"] >= p_min:
        return g[0]["lang"], "character statistics"
    f = detect(text, 1)
    if f and f[0]["p"] >= p_min:
        return f[0]["lang"], "fastText"
    return None, ""


def lens_rule(lengths=(20, 50), per_lang: int = 40, seed: int = 93) -> dict:
    """How often a language is named, and how often the name is right, with and without the fastText fallback."""
    rnd = np.random.default_rng(seed)
    out = {}
    for n in lengths:
        c = {"app_named": 0, "app_right": 0, "both_named": 0, "both_right": 0, "snippets": 0}
        for f in sorted(langid.SRC.glob("*.txt")):
            _, test = langid.split(f.stem)
            text = " ".join(test)
            if len(text) < n + 10:
                continue
            for _ in range(per_lang):
                i = int(rnd.integers(0, len(text) - n))
                s = text[i:i + n]
                code, how = lens_name(s)
                c["snippets"] += 1
                if code:
                    c["both_named"] += 1
                    c["both_right"] += code == f.stem
                    if how == "character statistics":
                        c["app_named"] += 1
                        c["app_right"] += code == f.stem
        out[str(n)] = {"app_named_share": round(c["app_named"] / c["snippets"], 3), "app_precision": round(c["app_right"] / max(c["app_named"], 1), 3),
                       "with_fasttext_named_share": round(c["both_named"] / c["snippets"], 3), "with_fasttext_precision": round(c["both_right"] / max(c["both_named"], 1), 3)}
    return out


def evaluate(lengths=(20, 50, 200), per_lang: int = 40, seed: int = 85) -> dict:
    rnd = np.random.default_rng(seed)
    res = {}
    for n in lengths:
        hit = {"app": 0, "fasttext": 0, "combined": 0}
        tot, worst = 0, {}
        for f in sorted(langid.SRC.glob("*.txt")):
            _, test = langid.split(f.stem)
            text = " ".join(test)
            if len(text) < n + 10:
                continue
            ok = {"app": 0, "fasttext": 0, "combined": 0}
            for _ in range(per_lang):
                i = int(rnd.integers(0, len(text) - n))
                s = text[i:i + n]
                fd = detect(s, 1)
                ok["app"] += langid.detect(s, 1)[0]["lang"] == f.stem
                ok["fasttext"] += bool(fd) and fd[0]["lang"] == f.stem
                ok["combined"] += combined(s) == f.stem
            for k in hit:
                hit[k] += ok[k]
            tot += per_lang
            worst[f.stem] = {k: round(v / per_lang, 2) for k, v in ok.items()}
        res[str(n)] = {k: round(v / tot, 3) for k, v in hit.items()}
        res[str(n)]["fasttext_worse_than_app_by_0.2"] = sorted(c for c, v in worst.items() if v["app"] - v["fasttext"] >= 0.2)
        res[str(n)]["app_worse_than_fasttext_by_0.2"] = sorted(c for c, v in worst.items() if v["fasttext"] - v["app"] >= 0.2)
    return {"id": "langid_fasttext", "languages": len(list(langid.SRC.glob("*.txt"))), "snippets_per_language": per_lang, "lengths": res}


if __name__ == "__main__":
    r = evaluate()
    r["lens_rule"] = lens_rule()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))
