"""Round 36a: recognise abbreviated plain French (pens, souf, bonh) so plain ads stop entering cipher searches.

Measure: the share of letters covered by French words or by the first 3+ letters of common French words, found by a
best segmentation. Positive control: published readings of solved ads with the bracketed expansions deleted, which is
the abbreviated French the writers printed. Negative controls: the same texts under a random substitution, and shuffled."""
import json
import random
import re
import unicodedata
from functools import lru_cache

from ..languages import ROOT, model
from .figaro_keys import OUT

RESULT = ROOT / "data/results/figaro_plainness.json"
COMMON = 6000  # words whose beginnings count as abbreviations
MAX_TOKEN = 14


@lru_cache(maxsize=1)
def tokens() -> tuple[frozenset, frozenset]:
    words = [str(w).lower() for w in model("fr")["words"][:20000]]
    full = frozenset(w for w in words if len(w) >= 3)
    stems = frozenset(w[:k] for w in words[:COMMON] if len(w) >= 5 for k in range(4, len(w)))
    return full, stems


def clean(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", t)


def abbreviated(text: str) -> str:
    """A published reading back to its printed form: bracketed expansions, the editor's initials and the signature removed."""
    t = re.sub(r"\[[^\]]*\]", "", text)
    t = re.sub(r"\([a-z]{1,3}\)\s*$", "", t.strip())
    t = re.sub(r"^[^-]{1,12}\s-\s", "", t)
    return clean(t)


def stem_coverage(t: str) -> float:
    """Most letters coverable by whole words (3+ letters) and word beginnings (4+ letters), by dynamic programming.
    Shorter tokens let shuffled French reach plain-text levels (tuned on the controls, Round 36)."""
    full, stems = tokens()
    n = len(t)
    if not n:
        return 0.0
    best = [0] * (n + 1)
    for i in range(1, n + 1):
        b = best[i - 1]
        for j in range(max(0, i - MAX_TOKEN), i - 1):
            w = t[j:i]
            if (w in full or (len(w) >= 4 and w in stems)) and best[j] + i - j > b:
                b = best[j] + i - j
        best[i] = b
    return best[n] / n


def substitute(t: str, rnd: random.Random) -> str:
    a = list("abcdefghijklmnopqrstuvwxyz")
    b = a[:]
    rnd.shuffle(b)
    m = dict(zip(a, b))
    return "".join(m[c] for c in t)


def shuffled(t: str, rnd: random.Random) -> str:
    s = list(t)
    rnd.shuffle(s)
    return "".join(s)


def controls(n: int = 400, seed: int = 36) -> dict:
    ads = [a for a in json.loads((OUT / "ads.json").read_text()) if a["solved"] in (True, "True") and a["text"]]
    rnd = random.Random(seed)
    texts = [t for t in (abbreviated(a["text"]) for a in rnd.sample(ads, min(n, len(ads)))) if 30 <= len(t) <= 400]
    plain = [stem_coverage(t) for t in texts]
    sub = [stem_coverage(substitute(t, rnd)) for t in texts]
    shuf = [stem_coverage(shuffled(t, rnd)) for t in texts]
    # The cut: the 99th percentile of substituted and shuffled texts (shuffles stand in for transposition ciphers).
    neg = sorted(sub + shuf)
    cut = neg[int(len(neg) * 0.99)]
    return {"n": len(texts), "cut": round(cut, 3), "plain_above": sum(x > cut for x in plain), "substituted_above": sum(x > cut for x in sub),
            "shuffled_above": sum(x > cut for x in shuf), "plain_median": round(sorted(plain)[len(plain) // 2], 3), "substituted_median": round(sorted(sub)[len(sub) // 2], 3)}


def is_plain(t: str, cut: float) -> bool:
    return stem_coverage(clean(t)) > cut


def run() -> dict:
    c = controls()
    rows = json.loads((OUT / "keys_rows.json").read_text())
    flagged = [{"image": r["image"], "signature": r["signature"], "letters": r["letters"], "stem_coverage": round(stem_coverage(clean(r["raw"])), 3)} for r in rows if len(r["raw"]) >= 20]
    plain = [f for f in flagged if f["stem_coverage"] > c["cut"]]
    by_sig = {}
    for f in flagged:
        s = by_sig.setdefault(f["signature"] or "-", [0, 0])
        s[0] += f["stem_coverage"] > c["cut"]
        s[1] += 1
    return {"id": "figaro_plainness", "control": c, "ads": len(flagged), "plain": len(plain), "by_signature": by_sig, "plain_images": sorted(f["image"] for f in plain)}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, indent=1))
    print(out["control"], out["ads"], out["plain"])
    print({k: v for k, v in sorted(out["by_signature"].items(), key=lambda x: -x[1][1])[:20]})
