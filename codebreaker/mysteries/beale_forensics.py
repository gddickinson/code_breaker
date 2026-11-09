"""Beale forensics: alternative key rules, and do the numbers look like a real book cipher?"""
import random
import re

import numpy as np

from ..kernels import book_offset_scan
from ..languages import ROOT, model
from ..text import to_ints
from ..validation import sample_plaintext
from .beale import KEYS, ciphers

SRC = ROOT / "data/sources"
ALL_KEYS = {**KEYS, "The Beale pamphlet itself": "beale_try8"}
RULES = {"first letter": 0, "second letter": 1, "last letter": -1}


def words_of(name: str) -> list[str]:
    raw = (SRC / name).read_text(errors="ignore")
    if name == "beale_try8":
        raw = re.sub(r"<[^>]+>", " ", raw)
    start = re.search(r"\*\*\* START OF.*?\*\*\*", raw)
    end = raw.find("*** END OF")
    body = raw[start.end() if start else 0: end if end > 0 else None]
    if "declaration" in name:
        body = body[body.lower().index("when in the course of human events"):]
    return [w for w in re.findall(r"[A-Za-z]+", body) if len(w) >= 2 or True]


def letters_by_rule(words: list[str], rule: int) -> np.ndarray:
    out = [(w[rule] if -len(w) <= rule < len(w) else w[-1]).upper() for w in words]
    return to_ints("".join(out))


def scan(nums, ini, offsets, n_null=20, seed=0):
    table, r = model("en")["table"], random.Random(seed)
    arr = np.array(nums, dtype=np.int64)
    real = book_offset_scan(arr, ini, table, offsets)
    nulls = []
    for _ in range(n_null):
        s = arr.copy()
        r.shuffle(s)
        nulls.append(float(book_offset_scan(s, ini, table, offsets).max()))
    m, sd = float(np.mean(nulls)), float(np.std(nulls, ddof=1))
    return float(real.max()), int(np.argmax(real)), round((float(real.max()) - m) / sd, 2) if sd else 0.0


def rule_scan(seed=0) -> list[dict]:
    c = ciphers()
    out = []
    for label, f in ALL_KEYS.items():
        w = words_of(f)
        for rule_name, rule in RULES.items():
            ini = letters_by_rule(w, rule)
            for name in ("B1", "B3"):
                nums = c[name]
                offs = min(max(len(ini) - max(nums), 1), 120000)
                score, off, z = scan(nums, ini, offs, seed=seed)
                out.append({"cipher": name, "key_text": label, "rule": rule_name, "offsets": offs, "score": round(score, 3), "z": z, "best_offset": off})
    return sorted(out, key=lambda r: -r["z"])


def rule_control(seed=5) -> dict:
    """Plant a last-letter book cipher in the Constitution; the scan must find it."""
    words = words_of("key_constitution.txt")
    ini = letters_by_rule(words, -1)
    r = random.Random(seed)
    plain, offset = sample_plaintext(520, "en", seed), 300
    where = {}
    for i in range(offset, min(offset + 1500, len(ini))):
        where.setdefault(int(ini[i]), []).append(i - offset + 1)
    nums = [r.choice(where.get(ord(c) - 65) or where[int(ini[offset])]) for c in plain]
    score, off, z = scan(nums, ini, 1500, seed=seed)
    return {"planted_offset": offset, "found_offset": off, "z": z, "found": off == offset}


def stats(nums) -> dict:
    a = np.array(nums, dtype=float)
    last = np.bincount(np.array(nums) % 10, minlength=10)
    d = np.abs(np.diff(a))
    return {"distinct_ratio": len(set(nums)) / len(nums), "share_under_100": float((a <= 100).mean()), "last_digit_chi2": float(((last - len(a) / 10) ** 2 / (len(a) / 10)).sum()),
            "small_steps": float((d <= 3).mean()), "lag1_corr": float(np.corrcoef(a[:-1], a[1:])[0, 1]), "repeat_within_8": float(np.mean([nums[i] in nums[max(0, i - 8):i] for i in range(1, len(nums))]))}


def simulate(n, doc_words, seed) -> dict:
    """An honest book encipherment of English: each letter takes a random matching word."""
    r = random.Random(seed)
    ini = doc_words
    where = {}
    for i, c in enumerate(ini):
        where.setdefault(int(c), []).append(i + 1)
    plain = to_ints(sample_plaintext(n, "en", seed))
    return stats([r.choice(where.get(int(c)) or where[19]) for c in plain])


def human_tests(n_sim=300) -> dict:
    c = ciphers()
    doc = letters_by_rule(words_of("declaration.txt"), 0)
    res = {}
    for name, nums in c.items():
        obs = stats(nums)
        sims = [simulate(len(nums), doc, s) for s in range(n_sim)]
        res[name] = {k: {"observed": round(v, 4), "sim_mean": round(float(np.mean([s[k] for s in sims])), 4), "z": round((v - float(np.mean([s[k] for s in sims]))) / (float(np.std([s[k] for s in sims])) + 1e-9), 1)} for k, v in obs.items()}
    return res


def run() -> dict:
    return {"id": "beale_forensics", "control": rule_control(), "rules": rule_scan(), "human": human_tests()}
