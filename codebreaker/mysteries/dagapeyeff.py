"""D'Agapeyeff 1939 challenge: digit-pair substitution under several structural hypotheses."""
import re

from ..analysis import entropy
from ..languages import LANGS, ROOT
from ..segment import segment
from ..validation import null_test, positive_control, verdict


def digits() -> str:
    raw = (ROOT / "data/sources/wp_dagapeyeff.txt").read_text()
    block = raw[raw.index("75628"): raw.index("}}", raw.index("75628"))]
    return "".join(re.findall(r"\d", re.sub(r"<[^>]+>", "", block)))


def pairs_of(d: str, start: int = 0) -> list[str]:
    return [d[i:i + 2] for i in range(start, len(d) - 1, 2)]


def ic_pairs(p: list[str]) -> float:
    from collections import Counter
    n = len(p)
    return sum(v * (v - 1) for v in Counter(p).values()) / (n * (n - 1))


def stats(d: str) -> dict:
    a, b = pairs_of(d), pairs_of(d, 1)
    from collections import Counter
    return {"digits": len(d), "digit_counts": dict(sorted(Counter(d).items())), "pairs_frame0_distinct": len(set(a)), "pairs_frame1_distinct": len(set(b)),
            "pair_ic_frame0": round(ic_pairs(a), 4), "pair_ic_frame1": round(ic_pairs(b), 4), "english_letter_ic": 0.066,
            "first_digit_set_frame0": "".join(sorted({x[0] for x in a})), "second_digit_set_frame0": "".join(sorted({x[1] for x in a})),
            "entropy_pairs_frame0": round(entropy(a), 3), "entropy_pairs_frame1": round(entropy(b), 3)}


def null_patterns(p: list[str]):
    """Drop one position in every cycle of length k: the 'nulls' idea d'Agapeyeff's book hints at."""
    yield "no nulls", p
    for k in (2, 3, 4, 5):
        for off in range(k):
            yield f"drop position {off + 1} of every {k}", [x for i, x in enumerate(p) if i % k != off]


def run() -> dict:
    d = digits()
    trimmed = d[:-3] if d.endswith("000") else d
    p = pairs_of(trimmed)
    res = {"id": "dagapeyeff", "stats": stats(trimmed), "trimmed_padding": d.endswith("000"), "hypotheses": []}
    patterns = list(null_patterns(p))
    n_tests = len(patterns) * len(LANGS)
    pc = positive_control(p, "en", False)
    res["positive_control"] = pc
    for name, seq in patterns:
        for lang in LANGS:
            nt = null_test(seq, lang, False, n_null=8)
            res["hypotheses"].append({"pattern": name, "language": LANGS[lang], "z": nt["z"], "score": nt["score"], "null_mean": nt["null_mean"],
                                      "null_sd": nt["null_sd"], "p": nt["p_empirical"], "plaintext": segment(nt["plaintext"], lang)})
    res["hypotheses"].sort(key=lambda h: -h["z"])
    res["tests"] = n_tests
    res["verdict"] = verdict(pc["mean"], res["hypotheses"][0]["z"], n_tests)
    return res
