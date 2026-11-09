"""Beale ciphers: verify B2, reproduce the alphabetical anomaly, attack B1/B3 with key texts."""
import json
import random
import re

import numpy as np

from ..kernels import book_offset_scan
from ..languages import ROOT, corpus_text, model
from ..segment import segment
from ..text import to_ints
from ..validation import null_test, positive_control, verdict

SRC = ROOT / "data/sources"
KEYS = {"Declaration of Independence": "declaration.txt", "US Constitution": "key_constitution.txt", "Common Sense": "key_common_sense.txt",
        "Federalist Papers": "key_federalist.txt", "King James Bible": "key_kjv.txt", "Shakespeare": "key_shakespeare.txt", "Wealth of Nations": "key_wealth.txt"}


def ciphers() -> dict:
    runs = json.loads((ROOT / "data/mysteries/beale_raw.json").read_text())
    return {"B1": next(r for r in runs if r[:2] == [71, 194]), "B2": next(r for r in runs if r[:2] == [115, 73]), "B3": next(r for r in runs if r[:2] == [317, 8])}


def initials(name: str) -> str:
    raw = (SRC / name).read_text(errors="ignore")
    start = re.search(r"\*\*\* START OF.*?\*\*\*", raw)
    end = raw.find("*** END OF")
    body = raw[start.end() if start else 0: end if end > 0 else None]
    if "declaration" in name:
        body = body[body.lower().index("when in the course of human events"):]
    return "".join(w[0].upper() for w in re.findall(r"[A-Za-z'’]+", body.replace("-", " ")))


def decode(nums, init) -> str:
    return "".join(init[n - 1] if n <= len(init) else "?" for n in nums)


def longest_alpha_run(s: str) -> tuple[int, str]:
    best, cur_start = (0, ""), 0
    for i in range(1, len(s) + 1):
        if i == len(s) or s[i] < s[i - 1] or s[i] == "?":
            if i - cur_start > best[0]:
                best = (i - cur_start, s[cur_start:i])
            cur_start = i
    return best


def anomaly(nums, init, n=2000, seed=0) -> dict:
    """How unusual is the longest non-decreasing run, compared with reordered numbers?"""
    run, text = longest_alpha_run(decode(nums, init))
    r = random.Random(seed)
    arr, more = list(nums), 0
    tops = []
    for _ in range(n):
        r.shuffle(arr)
        t = longest_alpha_run(decode(arr, init))[0]
        tops.append(t)
        more += t >= run
    return {"longest_run": run, "text": text, "null_mean": round(float(np.mean(tops)), 2), "null_max": max(tops), "p_empirical": round((more + 1) / (n + 1), 5)}


def key_scan(nums, n_null=40, seed=0) -> list[dict]:
    """Slide each candidate key text under the numbers; compare the best offset with shuffled numbers."""
    r, out = random.Random(seed), []
    arr = np.array(nums, dtype=np.int64)
    table = model("en")["table"]
    for label, f in KEYS.items():
        ini = to_ints(initials(f))
        window = max(len(ini) - int(arr.max()), 1) if len(ini) > arr.max() else 1
        window = min(window, 400000)
        real = book_offset_scan(arr, ini, table, window)
        nulls = []
        for _ in range(n_null):
            s = arr.copy()
            r.shuffle(s)
            nulls.append(float(book_offset_scan(s, ini, table, window).max()))
        best = int(np.argmax(real))
        m, sd = float(np.mean(nulls)), float(np.std(nulls, ddof=1))
        out.append({"key_text": label, "words": len(ini), "offsets_tested": window, "best_offset": best, "best_score": round(float(real[best]), 3),
                    "null_mean": round(m, 3), "null_sd": round(sd, 3), "z": round((float(real[best]) - m) / sd, 2) if sd else 0.0})
    return out


def stats(nums) -> dict:
    a = np.array(nums)
    last = np.bincount(a % 10, minlength=10)
    exp = len(a) / 10
    return {"count": len(a), "distinct": len(set(nums)), "max": int(a.max()), "mean": round(float(a.mean()), 1), "last_digit_counts": last.tolist(),
            "last_digit_chi2": round(float(((last - exp) ** 2 / exp).sum()), 1), "share_at_most_100": round(float((a <= 100).mean()), 3)}


def run() -> dict:
    c = ciphers()
    decl = initials("declaration.txt")
    b2 = decode(c["B2"], decl)
    res = {"id": "beale", "stats": {k: stats(v) for k, v in c.items()}, "b2_decoded": segment(b2.replace("?", "X")[:400].upper()),
           "b2_raw": b2.lower(), "hypotheses": {}}
    res["anomaly_b1"] = anomaly(c["B1"], decl)
    res["anomaly_b3"] = anomaly(c["B3"], decl)
    res["anomaly_b2_control"] = anomaly(c["B2"], decl, 500)
    tests = 0
    for name in ("B1", "B3"):
        scan = key_scan(c[name])
        tests += sum(s["offsets_tested"] for s in scan)
        res["hypotheses"][name] = {"key_scan": scan}
    res["key_scan_control_b2"] = key_scan(c["B2"], 10)[:1]
    for name in ("B1", "B3"):
        syms = c[name]
        pc = positive_control(syms, "en", True, iters=500000, restarts=3)
        nt = null_test(syms, "en", True, n_null=8, iters=500000, restarts=3)
        res["hypotheses"][name]["homophonic"] = {"positive_control": pc, "null_test": nt, "verdict": verdict(pc["mean"], nt["z"])}
    return res
