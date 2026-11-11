"""Controls for the language model as reader (Round 92); data/results/ai_reader_eval.json.

Items: the 70 solved Le Figaro ads of the Round 87 benchmark (left out of the ad-French model, so its quadgram ranker
has not seen them either). For each, five candidates: the true enciphered text; near misses with about 10% and 30% of
letters wrong (a key with letter pairs swapped); a wrong key (a random substitution of the truth); the truth's letters
shuffled. Ranking: the model's choice against the quadgram score and word coverage under the ad-French model.
Meaning: the model asked whether each candidate is a meaningful message (finding meaning in the wrong ones is the
false-meaning rate). Expansion: the abbreviated text with word breaks, expanded by the model, scored on the words
Müller expanded in brackets; null: the same words with their letters shuffled (expanding them invents a message)."""
import json
import random
import re

from . import ai_reader as R
from .languages import ROOT, score
from .mysteries.figaro_adlang import enciphered_words
from .mysteries.realbench import ADS, _signature, tier2
from .text import A, letters, strip_accents
from .validation import coverage

RESULT = ROOT / "data/results/ai_reader_eval.json"


def near_miss(t: str, share: float, rnd: random.Random) -> str:
    perm = list(A)
    out = t
    while sum(a != b for a, b in zip(out, t)) < share * len(t):
        i, j = rnd.sample(range(26), 2)
        perm[i], perm[j] = perm[j], perm[i]
        out = "".join(perm[A.index(c)] for c in t)
    return out


def candidates(t: str, rnd: random.Random) -> dict:
    p = list(A)
    rnd.shuffle(p)
    sh = list(t)
    rnd.shuffle(sh)
    return {"truth": t, "near 10%": near_miss(t, 0.10, rnd), "near 30%": near_miss(t, 0.30, rnd), "wrong key": "".join(p[A.index(c)] for c in t), "shuffled": "".join(sh)}


def expanded_words(text: str) -> list[str]:
    """Müller's expansions: the full words that had a bracketed part."""
    body = re.split(r"\(\w{1,5}\)", text)[0]
    return [letters(w.replace("[", "").replace("]", "")).lower() for w in re.findall(r"\S*\[[^\]]+\]\S*", body)]


def run(seed: int = 92) -> dict:
    rnd = random.Random(seed)
    ads = {a["image"]: a for a in json.loads(ADS.read_text())}
    items = [x for x in tier2() if x["name"] in ads]
    rank = {"model": 0, "quadgram": 0, "coverage": 0, "model_no_answer": 0}
    mean = {k: {"said_meaningful": 0, "asked": 0} for k in ("truth", "near 10%", "near 30%", "wrong key", "shuffled")}
    exp = {"words": 0, "recovered": 0, "ads": 0, "null_ads": 0, "null_claimed_meaning": 0}
    for x in items:
        c = candidates(x["truth"], rnd)
        names = list(c)
        rnd.shuffle(names)
        k = R.rank([c[n] for n in names], "frad")
        rank["model"] += k is not None and names[k] == "truth"
        rank["model_no_answer"] += k is None
        rank["quadgram"] += max(names, key=lambda n: score(c[n], "frad")) == "truth"
        rank["coverage"] += max(names, key=lambda n: coverage(c[n], "frad")) == "truth"
        for n in mean:
            m = R.meaningful(c[n], "frad")
            if m is not None:
                mean[n]["asked"] += 1
                mean[n]["said_meaningful"] += m["meaningful"]
        ad = ads.get(x["name"])
        want = expanded_words(ad["text"]) if ad else []
        if want:
            abbrev = enciphered_words(ad["text"], _signature(ad["image"]))
            e = R.expand(abbrev)
            got = strip_accents((e or {}).get("expanded", "")).lower()
            exp["ads"] += 1
            exp["words"] += len(want)
            exp["recovered"] += sum(w in letters(got).lower() for w in want if w)
            scrambled = " ".join("".join(rnd.sample(w, len(w))) for w in abbrev.split())
            n_ = R.expand(scrambled)
            exp["null_ads"] += 1
            exp["null_claimed_meaning"] += bool(n_ and n_["expanded"] and n_["expanded"].upper() != "NONE")
    n = len(items)
    return {"id": "ai_reader_eval", "model": R.ai_local.status()["text"], "items": n,
            "ranking_right": {k: v for k, v in rank.items()}, "meaning": mean, "expansion": exp}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))
