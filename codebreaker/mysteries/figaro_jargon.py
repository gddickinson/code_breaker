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
from ..third_party import need

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
    ads = {a["image"].replace("/", "_"): a for a in json.loads(need(OUT / "ads.json").read_text())}
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


def v_occurrences() -> list[tuple]:
    """(image, stem, code word, neighbours) for every pattern code word in the 1896 V ads."""
    ads = {a["image"].replace("/", "_"): a for a in json.loads(need(OUT / "ads.json").read_text())}
    raw, out = json.loads((OUT / "ocr_raw.json").read_text()), []
    for n in sorted(raw):
        if not (n.endswith("-V.jpg") and n.startswith("1896")) or ads.get(n, {}).get("solved") in (True, "True"):
            continue
        toks = [t.lower() for t in re.findall(r"[A-Za-z]+", " ".join(raw[n].get("tesseract") or []))]
        for i, t in enumerate(toks):
            m = PATTERN.match(t)
            if m:
                out.append((n, m.group(1), t, toks[max(0, i - 2):i] + toks[i + 1:i + 3]))
    return out


def mutual_information(pairs: list[tuple]) -> float:
    from math import log

    n = len(pairs)
    pxy, px, py = Counter(pairs), Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    return sum(c / n * log((c / n) / (px[a] / n * py[b] / n)) for (a, b), c in pxy.items()) if n else 0.0


def date_tests(trials: int = 2000, seed: int = 61) -> dict:
    """Fixed before looking (Round 61): H1, a stem's variant tracks the publication weekday; H2, it tracks the day of
    the month. Statistic: mutual information between variant and date feature; null: ad dates permuted among ads;
    Bonferroni over stems x 2. Also counted: plain time words beside each stem (descriptive)."""
    import datetime

    occ = v_occurrences()
    images = sorted({o[0] for o in occ})
    date = {i: datetime.date(int(i[5:9]), int(i[9:11]), int(i[11:13])) for i in images}
    feature = {"weekday": lambda d: d.weekday(), "monthday": lambda d: d.day}
    rnd, out = random.Random(seed), {}
    tests = [(s, f) for s in STEMS for f in feature if sum(o[1] == s for o in occ) >= 8]
    for stem, f in tests:
        rows = [(o[0], o[2]) for o in occ if o[1] == stem]
        real = mutual_information([(w, feature[f](date[i])) for i, w in rows])
        null = []
        for _ in range(trials):
            perm = images[:]
            rnd.shuffle(perm)
            remap = dict(zip(images, perm))
            null.append(mutual_information([(w, feature[f](date[remap[i]])) for i, w in rows]))
        out[f"{stem}:{f}"] = {"occurrences": len(rows), "mi": round(real, 3), "null_mean": round(sum(null) / trials, 3), "p": (sum(x >= real for x in null) + 1) / (trials + 1)}
    bar = 0.05 / max(len(tests), 1)
    for v in out.values():
        v["passes"] = v["p"] <= bar
    time_words = {"heure", "heures", "h", "soir", "matin", "midi", "minuit", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"}
    beside = {s: Counter(w for o in occ if o[1] == s for w in o[3] if w in time_words) for s in STEMS}
    return {"tests": out, "bar": bar, "passed": [k for k, v in out.items() if v["passes"]], "time_words_beside": {k: dict(v) for k, v in beside.items() if v}}


def run() -> dict:
    return {"id": "figaro_jargon", "codebook_38": elision_test(), "v_1896": jargon_table(), "v_dates": date_tests()}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res["codebook_38"], indent=1))
    j = res["v_1896"]
    print({k: j[k] for k in ("ads", "code_words", "pattern_share", "null_mean", "null_max", "p")})
    print(j["by_stem"])
    print(json.dumps(res["v_dates"], indent=1))
