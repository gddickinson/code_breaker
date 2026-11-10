"""Round 41: the documented key of writer C. H. (Vigenere CEAD, no W) on the writer's five unsolved ads.

An enciphered block often starts mid-ad, so the key may start at any of its four positions, and a printed block may have
lost or gained a letter, so at most one slip of the key is allowed. The best decryption by French quadgram score is
taken. Null: the same search on shuffled copies of each block. Positive control: printed forms of solved C. H. ads,
enciphered with the same key, with one letter dropped at random."""
import json
import random

from ..languages import ROOT, score
from ..validation import coverage
from .figaro_keys import OUT
from .figaro_plainness import abbreviated

RESULT = ROOT / "data/results/figaro_ch.json"
DATA = json.loads((OUT / "ch_transcription.json").read_text())
A, KEY = DATA["system"]["alphabet"], DATA["system"]["key"]


def decrypt(t: str, phase: int = 0, slip_at: int | None = None, slip: int = 0) -> str:
    """Vigenere decryption; from position slip_at on, the key position moves by slip (+1 skips a key letter)."""
    out = []
    for i, c in enumerate(t):
        k = KEY[(i + phase + (slip if slip_at is not None and i >= slip_at else 0)) % len(KEY)]
        out.append(A[(A.index(c) - A.index(k)) % len(A)])
    return "".join(out)


def encrypt(p: str, phase: int = 0) -> str:
    return "".join(A[(A.index(c) + A.index(KEY[(i + phase) % len(KEY)])) % len(A)] for i, c in enumerate(p))


def search(t: str, phases=(0, 1, 2, 3), slips: bool = True) -> dict:
    """Key phases given, with no slip or (if slips) one slip of +1, +2 or +3 key positions anywhere.
    Strict form (Round 41): phase 0, the key restarting at each block, as every reading block suggests."""
    best = None
    for phase in phases:
        options = [(None, 0)] + ([(c, s) for c in range(1, len(t)) for s in (1, 2, 3)] if slips else [])
        for cut, s in options:
            p = decrypt(t, phase, cut, s)
            sc = score(p, "fr")
            if best is None or sc > best["score"]:
                best = {"score": sc, "phase": phase, "slip_at": cut, "slip": s, "plain": p}
    best["coverage"] = coverage(best["plain"], "fr")
    return best


def shuffled(t: str, rnd: random.Random) -> str:
    s = list(t)
    rnd.shuffle(s)
    return "".join(s)


def null(t: str, n: int, seed: int, **kw) -> list[dict]:
    rnd = random.Random(seed)
    return [search(shuffled(t, rnd), **kw) for _ in range(n)]


CONTROL_KW = {}


def control(trials: int = 40, seed: int = 41) -> dict:
    """Printed forms of solved C. H. ads, 20-30 letters, enciphered, one letter dropped; recovered if 80% of letters match."""
    ads = [a for a in json.loads((OUT / "ads.json").read_text()) if a["image"].endswith("-CH.jpg") and a["solved"] in (True, "True") and a["text"]]
    rnd, ok, results, covs = random.Random(seed), 0, [], []
    for _ in range(trials):
        p = abbreviated(rnd.choice(ads)["text"]).upper().replace("W", "V")
        n = rnd.randint(20, 30)
        if len(p) < n + 2:
            continue
        start = rnd.randrange(len(p) - n)
        plain = p[start:start + n]
        ct = encrypt(plain, 0 if CONTROL_KW.get("phases") == (0,) else rnd.randrange(4))
        drop = rnd.randrange(3, n - 3)
        ct = ct[:drop] + ct[drop + 1:]
        got = search(ct, **CONTROL_KW)["plain"]
        expect = plain[:drop] + plain[drop + 1:]
        covs.append(coverage(expect, "fr"))
        right = sum(a == b for a, b in zip(got, expect)) / len(expect)
        results.append(right)
        ok += right >= 0.8
    covs.sort()
    return {"trials": len(results), "recovered": ok, "mean_letters": round(sum(results) / len(results), 3), "true_coverage_median": covs[len(covs) // 2]}


def gates(row: dict, ctrl: dict, blocks: int) -> dict:
    """validation.verdict's gates per block: the control recovers, the score beats the null after a Bonferroni
    correction over the blocks tested, and the reading reaches 0.8 of what true text of this kind covers."""
    g = {"control": ctrl["recovered"] / ctrl["trials"] >= 0.7, "null": row["p_score"] <= 0.05 / blocks,
         "reads": row["coverage"] >= 0.8 * ctrl["true_coverage_median"]}
    return {**g, "passed": all(g.values())}


def run(nulls: int = 200) -> dict:
    global CONTROL_KW
    out = {"id": "figaro_ch"}
    for name, kw, minimum in (("loose", {}, 10), ("strict", {"phases": (0,)}, 6)):
        CONTROL_KW = kw
        ctrl, rows = control(), rows_for(nulls, kw, minimum)
        for r in rows:
            r["gates"] = gates(r, ctrl, len(rows))
        out[name] = {"control": ctrl, "rows": rows}
    CONTROL_KW = {}
    return out


def rows_for(nulls: int, kw: dict, minimum: int) -> list[dict]:
    rows = []
    for image, ad in DATA["ads"].items():
        for j, block in enumerate(ad["blocks"]):
            if len(block) < minimum:
                continue
            k = dict(kw, slips=len(block) >= 10)
            got = search(block, **k)
            ns = null(block, nulls, 4100 + j, **k)
            p_score = (sum(x["score"] >= got["score"] for x in ns) + 1) / (nulls + 1)
            p_cov = (sum(x["coverage"] >= got["coverage"] for x in ns) + 1) / (nulls + 1)
            rows.append({"image": image, "block": block, **got, "score": round(got["score"], 3), "p_score": round(p_score, 4), "p_coverage": round(p_cov, 4),
                         "null_best_coverage": max(x["coverage"] for x in ns)})
    return rows


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, indent=1))
    for name in ("loose", "strict"):
        print(name, res[name]["control"])
        for r in res[name]["rows"]:
            print(" ", r["image"][5:13], r["block"], r["plain"], r["phase"], r["slip_at"], r["slip"], r["score"], r["coverage"], r["p_score"], r["p_coverage"], r["null_best_coverage"], r["gates"]["passed"])
