"""Round 60: two codebook series described, each against a control.

1. The '38' ads (Sep-Oct 1881): if their numbers (up to 36,427) index an alphabetical word list, a number after an
   elided 'j'' must fall where words begin with a vowel or h. Count hits against the chance rate of such stretches.
2. The 'V' ads of 1896: their code words (galda, milo, larzo, drivo, frata ...) are tabulated, and the share that fit a
   stem + consonant + vowel pattern is compared with the same tokens with letters shuffled."""
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict

from ..languages import ROOT, model
from .figaro_keys import OUT
from .figaro_lc15 import DATA
from .figaro_wordrefine import vocab

RESULT = ROOT / "data/results/figaro_jargon.json"
STEMS = ("lar", "dri", "fra", "mi", "gal", "er", "fle")
PATTERN = re.compile(r"^(%s)[bcdfgjklmnprstvxz][aeo]$" % "|".join(STEMS))


def alphabetical_list() -> list[str]:
    return sorted({unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower() for x in model("fr")["words"][:20000] if str(x).isalpha()})


def elision_test() -> dict:
    words = alphabetical_list()
    nums = [int(n) for t in DATA["codebook_38"].values() for n in re.findall(r"\d{3,}", t)]
    top = max(nums)
    elided = [int(n) for t in DATA["codebook_38"].values() for n in re.findall(r"[Jj]'(\d+)", t)]
    starts = lambda n: words[min(int(n / top * len(words)), len(words) - 1)][0]
    vowel_share = sum(w[0] in "aeiouyh" for w in words) / len(words)
    hits = [{"number": n, "position": round(n / top, 3), "word_there": words[min(int(n / top * len(words)), len(words) - 1)], "vowel_or_h": starts(n) in "aeiouyh"} for n in elided]
    k, m = sum(h["vowel_or_h"] for h in hits), len(hits)
    from math import comb

    p = sum(comb(m, i) * vowel_share ** i * (1 - vowel_share) ** (m - i) for i in range(k, m + 1))
    return {"numbers": len(nums), "max": top, "elided": hits, "hits": k, "of": m, "chance_rate": round(vowel_share, 3), "p": round(p, 3)}


def jargon_table(min_ads: int = 3) -> dict:
    ads = {a["image"].replace("/", "_"): a for a in json.loads((OUT / "ads.json").read_text())}
    raw, v = json.loads((OUT / "ocr_raw.json").read_text()), vocab()
    names = sorted(n for n in raw if n.endswith("-V.jpg") and n.startswith("1896") and ads.get(n, {}).get("solved") not in (True, "True"))
    count, where, near = Counter(), defaultdict(set), defaultdict(Counter)
    for n in names:
        toks = [t.lower() for t in re.findall(r"[A-Za-z]+", " ".join(raw[n].get("tesseract") or []))]
        for i, t in enumerate(toks):
            if len(t) >= 3 and t not in v:
                count[t] += 1
                where[t].add(n)
                for j in (i - 1, i + 1):
                    if 0 <= j < len(toks):
                        near[t][toks[j]] += 1
    codes = [t for t in count if len(where[t]) >= min_ads]
    fit = sum(bool(PATTERN.match(t)) for t in codes) / len(codes)
    rnd, null = random.Random(60), []
    for _ in range(1000):
        sh = ["".join(rnd.sample(t, len(t))) for t in codes]
        null.append(sum(bool(PATTERN.match(t)) for t in sh) / len(sh))
    matrix = defaultdict(list)
    for t in codes:
        m = PATTERN.match(t)
        if m:
            matrix[m.group(1)].append(t)
    return {"ads": len(names), "code_words": len(codes), "pattern_share": round(fit, 3), "null_mean": round(sum(null) / len(null), 3), "null_max": round(max(null), 3),
            "p": (sum(x >= fit for x in null) + 1) / 1001, "by_stem": {k: sorted(v) for k, v in matrix.items()},
            "top": [{"word": t, "count": count[t], "ads": len(where[t]), "neighbours": near[t].most_common(4)} for t in sorted(codes, key=lambda t: -count[t])[:30]]}


def run() -> dict:
    return {"id": "figaro_jargon", "codebook_38": elision_test(), "v_1896": jargon_table()}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res["codebook_38"], indent=1))
    j = res["v_1896"]
    print({k: j[k] for k in ("ads", "code_words", "pattern_share", "null_mean", "null_max", "p")})
    print(j["by_stem"])
