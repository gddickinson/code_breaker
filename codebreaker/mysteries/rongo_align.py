"""Rongorongo: signs that swap places in identical contexts may be variants of one sign."""
import json
import random
from collections import Counter, defaultdict
from itertools import combinations

import numpy as np

from .scriptlab import LAB, re


def lines():
    d = json.loads((LAB / "rongo_tablets.json").read_text())
    return [[g.lstrip("0") or "0" for u in line.split("-") for g in re.findall(r"\d{1,3}", u)] for tablet in d.values() for line in tablet.values()]


def pair_scores(seqs, min_shared=3):
    """Pairs of signs seen between the same left and right neighbours, by number of shared contexts."""
    ctx = defaultdict(set)
    for s in seqs:
        for i in range(1, len(s) - 1):
            ctx[(s[i - 1], s[i + 1])].add(s[i])
    pairs = Counter()
    for members in ctx.values():
        if 2 <= len(members) <= 12:
            for a, b in combinations(sorted(members), 2):
                pairs[(a, b)] += 1
    return {k: v for k, v in pairs.items() if v >= min_shared}


def lift(scores, freq):
    return {k: v / (freq[k[0]] * freq[k[1]]) ** 0.5 for k, v in scores.items()}


def shuffled(seqs, r):
    all_g = [g for s in seqs for g in s]
    r.shuffle(all_g)
    out, p = [], 0
    for s in seqs:
        out.append(all_g[p:p + len(s)])
        p += len(s)
    return out


def control(seqs, seed=4):
    """Rename half of one frequent sign's occurrences; the pair must rank at the top."""
    r = random.Random(seed)
    c = Counter(g for s in seqs for g in s)
    target = c.most_common(40)[35][0]
    planted = [[("X" if g == target and r.random() < 0.5 else g) for g in s] for s in seqs]
    freq = Counter(g for s in planted for g in s)
    ranked = sorted(lift(pair_scores(planted), freq).items(), key=lambda x: -x[1])
    rank = next((i for i, (k, _) in enumerate(ranked) if k == tuple(sorted((target, "X")))), None)
    return {"sign": target, "rank": rank, "pairs_considered": len(ranked), "passes": rank is not None and rank < max(5, len(ranked) // 50)}


def run(n_null=20) -> dict:
    seqs = lines()
    real = pair_scores(seqs)
    r = random.Random(0)
    freq = Counter(g for s in seqs for g in s)
    null_top = [max(lift(pair_scores(x), freq).values() or [0]) for x in (shuffled(seqs, r) for _ in range(n_null))]
    ranked = sorted(real.items(), key=lambda x: -x[1])
    expected = lambda a, b: freq[a] * freq[b]
    pmi = sorted(({"a": a, "b": b, "shared_contexts": v, "freq_a": freq[a], "freq_b": freq[b], "normalised": round(v / (expected(a, b) ** 0.5), 3)} for (a, b), v in real.items() if v >= 5), key=lambda x: -x["normalised"])
    return {"id": "rongo_align", "pairs": len(real), "top_raw": [{"a": a, "b": b, "shared": v} for (a, b), v in ranked[:10]], "top_normalised": pmi[:15], "null_max_mean": round(float(np.mean(null_top)), 3), "null_max": round(max(null_top), 3), "control": control(seqs)}
