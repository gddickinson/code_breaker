"""Round 64: are Ricky McCormick's notes abbreviated English? Four letter-frequency models, fixed before looking.

Models built from the English corpus: (1) plain English; (2) vowel-dropped English, first letter of each word kept;
(3) initial letters of words; (4) any simple substitution of English, compared on the sorted frequency profile (the
letters may be relabelled). Statistic: KL divergence of McCormick's letter frequencies from the model. Null: the same
divergence for 2,000 texts of the same length drawn from the model. A model is rejected when p < 0.05/4."""
import json
import math
import random
import re
from collections import Counter

from ..languages import ROOT, corpus_text

RESULT = ROOT / "data/results/mccormick.json"
SRC = ROOT / "data/sources/unsolved"
A = "abcdefghijklmnopqrstuvwxyz"


def mccormick_letters() -> str:
    t = "".join((SRC / f"Ricky McCormick page {i}.txt").read_text(errors="ignore") for i in (1, 2)).lower()
    return "".join(c for c in t if c in A)


def corpus_words() -> list[str]:
    return re.findall(r"[a-z]+", corpus_text("en").lower())[:200000]


def model_stream(name: str, words: list[str]) -> str:
    if name in ("plain", "substitution"):
        return "".join(words)
    if name == "vowel_dropped":
        return "".join(w[0] + re.sub(r"[aeiou]", "", w[1:]) for w in words)
    if name == "initials":
        return "".join(w[0] for w in words)
    raise ValueError(name)


def freqs(t: str) -> list[float]:
    c, n = Counter(t), len(t)
    return [(c[x] + 0.5) / (n + 13) for x in A]


def kl(p: list[float], q: list[float]) -> float:
    return sum(a * math.log(a / b) for a, b in zip(p, q))


def stat(sample: str, model: list[float], sorted_profile: bool) -> float:
    p = freqs(sample)
    if sorted_profile:
        return kl(sorted(p, reverse=True), sorted(model, reverse=True))
    return kl(p, model)


def run(trials: int = 2000, seed: int = 64) -> dict:
    text = mccormick_letters()
    words = corpus_words()
    rnd, out = random.Random(seed), {}
    for name in ("plain", "vowel_dropped", "initials", "substitution"):
        stream = model_stream(name, words)
        model = freqs(stream)
        sp = name == "substitution"
        real = stat(text, model, sp)
        null = []
        for _ in range(trials):
            i = rnd.randrange(len(stream) - len(text))
            null.append(stat(stream[i:i + len(text)], model, sp))
        p = (sum(x >= real for x in null) + 1) / (trials + 1)
        out[name] = {"kl": round(real, 4), "null_mean": round(sum(null) / trials, 4), "null_max": round(max(null), 4), "p": round(p, 4), "rejected": p < 0.05 / 4,
                     "vowel_share_model": round(sum(stream.count(v) for v in "aeiou") / len(stream), 3)}
    vowels = sum(text.count(v) for v in "aeiou") / len(text)
    groups = [g for i in (1, 2) for g in re.split(r"[^a-z]+", (SRC / f"Ricky McCormick page {i}.txt").read_text(errors="ignore").lower()) if len(g) >= 3]
    ends = Counter(g[-2:] for g in groups)
    eng = Counter(w[-2:] for w in words if len(w) >= 3)
    endings = {"groups": len(groups), "top": ends.most_common(6), "se_share": round(ends["se"] / len(groups), 3),
               "se_share_english": round(eng["se"] / sum(eng.values()), 3)}
    return {"id": "mccormick", "letters": len(text), "vowel_share": round(vowels, 3), "top": Counter(text).most_common(10), "models": out, "endings": endings,
            "not_rejected": [k for k, v in out.items() if not v["rejected"]]}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, indent=1))
    print(res["letters"], res["vowel_share"], res["top"])
    for k, v in res["models"].items():
        print(" ", k, v)
    print("not rejected:", res["not_rejected"])
    print(res["endings"])
