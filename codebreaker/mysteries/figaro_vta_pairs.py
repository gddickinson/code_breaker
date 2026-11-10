"""Round 39: do some V. T. A. symbols stand for two neighbouring letters (n = a/b, y = o/p, f = w/y)?

For each ad held out, second values are fitted on the other ads: a symbol gains one extra letter when that puts more
decoded letters inside dictionary words there. The gain is then measured on the held-out ad. The hypothesis restricts
the extra letter to the neighbours of the symbol's letter in the writer's alphabet; the control offers two random
non-neighbouring letters instead, drawn many times. Extra freedom always helps a little, so only beating the control
counts as evidence."""
import json
import random
from itertools import product

from ..languages import ROOT
from . import figaro_vta as V

RESULT = ROOT / "data/results/figaro_vta_pairs.json"
ALPHABET = "abcdefghiklmnopqrstuwxyz"  # i/j and u/v merged, as the writer did
MIN_GAIN = 2  # letters a second value must newly explain in the fitting ads
MAX_OPTIONS = 64  # combinations tried per word


def neighbours(letter: str) -> list[str]:
    i = ALPHABET.index(letter)
    return [ALPHABET[j] for j in (i - 1, i + 1) if 0 <= j < len(ALPHABET)]


def best_cover(word: str, key: dict, extra: dict) -> int:
    """Most covered letters over the choices each two-valued symbol allows."""
    options = [[key.get(c, "?")] + ([extra[c]] if c in extra else []) for c in word.replace("'", "")]
    n = 1
    for o in options:
        n *= len(o)
    if n > MAX_OPTIONS:
        options = [o[:1] for o in options]
    return max(V.covered("".join(p)) for p in product(*options))


def total(words: list[str], key: dict, extra: dict) -> int:
    return sum(best_cover(w, key, extra) for w in words)


def fit(words: list[str], key: dict, candidates: dict) -> dict:
    """Greedy: give each symbol the candidate second letter that most increases covered letters, if by MIN_GAIN."""
    extra, base = {}, total(words, key, {})
    for s in sorted(candidates, key=lambda s: -sum(w.count(s) for w in words)):
        best, gain = None, MIN_GAIN - 1
        uses = [w for w in words if s in w]
        here = total(uses, key, extra)
        for letter in candidates[s]:
            g = total(uses, key, {**extra, s: letter}) - here
            if g > gain:
                best, gain = letter, g
        if best:
            extra[s] = best
    return extra


def held_out(make_candidates, rnd=None) -> dict:
    saved = V.SCORING
    V.SCORING = "segmented"
    try:
        got = base = letters = 0
        fitted = {}
        for image, ad in V.ads().items():
            if image in V.SKIP:
                continue
            key = V.key_from([c for c in V.CRIBS if c[0] != V.date(image)])
            train = [w for i, a in V.ads().items() if i != image and i not in V.SKIP for w in V.scored_words(a)]
            extra = fit(train, key, make_candidates(key, rnd))
            test = V.scored_words(ad)
            got += total(test, key, extra)
            base += total(test, key, {})
            letters += sum(len(w.replace("'", "")) for w in test)
            fitted[image] = extra
        return {"share": round(got / letters, 4), "baseline": round(base / letters, 4), "fitted": fitted}
    finally:
        V.SCORING = saved


def neighbour_candidates(key, rnd=None) -> dict:
    return {s: neighbours(l) for s, l in key.items() if l in ALPHABET}


def random_candidates(key, rnd) -> dict:
    out = {}
    for s, l in key.items():
        if l in ALPHABET:
            others = [x for x in ALPHABET if x != l and x not in neighbours(l)]
            out[s] = rnd.sample(others, 2)
    return out


def run(draws: int = 40, seed: int = 39) -> dict:
    rnd = random.Random(seed)
    hyp = held_out(neighbour_candidates)
    ctrl = [held_out(random_candidates, rnd)["share"] for _ in range(draws)]
    p = (sum(c >= hyp["share"] for c in ctrl) + 1) / (draws + 1)
    full_key = V.full_key()
    saved = V.SCORING
    V.SCORING = "segmented"
    try:
        allwords = [w for i, a in V.ads().items() if i not in V.SKIP for w in V.scored_words(a)]
        extra_all = fit(allwords, full_key, neighbour_candidates(full_key))
    finally:
        V.SCORING = saved
    return {"id": "figaro_vta_pairs", "baseline_share": hyp["baseline"], "neighbour_share": hyp["share"], "random_share_mean": round(sum(ctrl) / len(ctrl), 4),
            "random_share_max": round(max(ctrl), 4), "p_value": round(p, 4), "draws": draws,
            "second_values_all_ads": {s: [full_key[s], l] for s, l in extra_all.items()},
            "stable": {s: sum(s in f for f in hyp["fitted"].values()) for s in extra_all}}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, indent=1))
    print({k: v for k, v in out.items()})
