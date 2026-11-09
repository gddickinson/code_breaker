"""Tamam Shud (Somerton Man) code: is it an initialism, and in which language?"""
import random
import re

import numpy as np

from ..languages import LANGS, ROOT, corpus_text, model
from ..segment import segment
from ..text import letters, to_ints
from ..validation import null_test, positive_control, verdict

LINES = ["WRGOABABD", "MLIAOI", "WTBIMPANETP", "MLIABOAIAQC", "ITTMTSAMSTGAB"]
STRUCK = 1  # line 2 is crossed out in the original
CODE = "".join(l for i, l in enumerate(LINES) if i != STRUCK)


def loglik(counts, probs):
    return float((counts * np.log(probs + 1e-5)).sum())


def distribution_test(n_mc: int = 20000, seed: int = 0) -> list[dict]:
    """Log-likelihood of the observed letters under initial-letter and running-text models."""
    c = np.bincount(to_ints(CODE), minlength=26)
    out = []
    for code, name in LANGS.items():
        m = model(code)
        out.append({"language": name, "initial_letter_loglik": round(loglik(c, m["initial"]), 2), "running_text_loglik": round(loglik(c, m["letter"]), 2),
                    "initial_minus_running": round(loglik(c, m["initial"]) - loglik(c, m["letter"]), 2)})
    return sorted(out, key=lambda r: -r["initial_letter_loglik"])


def calibration(n: int = 4000, seed: int = 0) -> dict:
    """How often does real English running text / real initials give a likelihood gap this large?"""
    r = np.random.default_rng(seed)
    m, size = model("en"), len(CODE)
    obs = loglik(np.bincount(to_ints(CODE), minlength=26), m["initial"]) - loglik(np.bincount(to_ints(CODE), minlength=26), m["letter"])
    def gaps(p):
        g = []
        for _ in range(n):
            x = np.bincount(r.choice(26, size, p=p / p.sum()), minlength=26)
            g.append(loglik(x, m["initial"]) - loglik(x, m["letter"]))
        return np.array(g)

    from_initial, from_running = gaps(m["initial"]), gaps(m["letter"])
    return {"observed_gap": round(obs, 2), "gap_mean_if_initials": round(float(from_initial.mean()), 2), "gap_sd_if_initials": round(float(from_initial.std()), 2),
            "gap_mean_if_running_text": round(float(from_running.mean()), 2), "gap_sd_if_running_text": round(float(from_running.std()), 2),
            "fraction_running_text_at_least_observed": round(float((from_running >= obs).mean()), 4), "fraction_initials_at_most_observed": round(float((from_initial <= obs).mean()), 4)}


def rubaiyat_lines() -> list[str]:
    raw = (ROOT / "data/sources/key_rubaiyat.txt").read_text(errors="ignore")
    body = raw[re.search(r"\*\*\* START OF.*?\*\*\*", raw).end(): raw.find("*** END OF")]
    return [ln.strip() for ln in body.splitlines() if len(ln.split()) >= 4]


def _book_words() -> list[str]:
    return re.findall(r"[A-Za-z'\u2019]+", " ".join(rubaiyat_lines()))


def _longest_match(blocks: list[str], ini: str) -> tuple[int, str]:
    best = (0, "")
    for line in blocks:
        for i in range(len(line)):
            j = i + best[0] + 1
            while j <= len(line) and line[i:j] in ini:
                best = (j - i, line[i:j])
                j += 1
    return best


def rubaiyat_match(n_null: int = 2000, seed: int = 0) -> dict:
    """Longest run matching consecutive word initials, against realistic controls.

    Shuffled code letters are a weak null because real initials share common sequences.
    The stricter null takes blocks of the same sizes from word initials of English novels.
    """
    words = _book_words()
    ini = "".join(w[0].upper() for w in words)
    length, text = _longest_match(LINES, ini)
    pos = ini.index(text) if text else -1
    r = random.Random(seed)
    corpus = "".join(w[0].upper() for w in re.findall(r"[A-Za-z]+", corpus_text("en")))
    def block_null():
        return [corpus[(st := r.randrange(len(corpus) - 20)): st + len(l)] for l in LINES]
    shuffled, english = [], []
    for _ in range(n_null):
        s = list(CODE)
        r.shuffle(s)
        s = "".join(s)
        shuffled.append(_longest_match([s], ini)[0])
        english.append(_longest_match(block_null(), ini)[0])
    return {"length": length, "letters": text, "position": pos, "book_words": " ".join(words[pos: pos + length]), "context": " ".join(words[max(0, pos - 6): pos + length + 6]),
            "shuffled_mean": round(float(np.mean(shuffled)), 2), "shuffled_at_least": round(float(np.mean([x >= length for x in shuffled])), 4),
            "english_initials_mean": round(float(np.mean(english)), 2), "english_at_least": round(float(np.mean([x >= length for x in english])), 4), "initials_in_book": len(ini)}


def run() -> dict:
    res = {"id": "tamam", "lines": LINES, "code": CODE, "length": len(CODE), "distribution": distribution_test(), "calibration": calibration(), "rubaiyat": rubaiyat_match()}
    pc = positive_control(list(CODE), "en", False)
    res["hypotheses"] = []
    for lang in LANGS:
        nt = null_test(list(CODE), lang, False, n_null=20)
        res["hypotheses"].append({"language": LANGS[lang], "z": nt["z"], "score": nt["score"], "null_mean": nt["null_mean"], "plaintext": segment(nt["plaintext"], lang)})
    res["hypotheses"].sort(key=lambda h: -h["z"])
    res["positive_control"] = pc
    top = res["hypotheses"][0]
    code = next(c for c, n in LANGS.items() if n == top["language"])
    res["verdict"] = verdict(pc, top["z"], len(LANGS), top["plaintext"].replace(" ", ""), top["score"], code)
    return res
