"""Round 72: every unsolved Le Figaro ad of 1885-1895 screened under the C. H. Vigenere key CEAD (no W).

V. E. 3 (Round 71) used the documented C. H. key with the key running on across words, so the key may have had other
users. Fixed before running:
  Ads: the OCR letter blocks of figaro_documented.ad_blocks (plain stretches removed), years 1885-1895.
  Statistic: best quadgram score over phases 0-3 and two key modes (running on across blocks; restarting at each block).
  Null: the same search on copies with the letters shuffled across blocks (block sizes kept). Stage 1: 300 shuffles;
  ads that no shuffle reaches get max(20,000, 2/bar) shuffles, so that the smallest p lies below the bar. Bar: Bonferroni over all ads screened.
  Positive control: French corpus passages of the screened ads' lengths, enciphered with CEAD (random phase and mode),
  with 5% of letters replaced at random (OCR noise), screened the same way.
Extension (all_keys): the three documented Vigenere keys (BCD, CEAD, CD) on every unsolved ad of all years, same
statistic and null, Bonferroni over ads x keys.
Passing ads are machine readings until transcribed from the scan and read by eye."""
import json
import random
import re

from ..languages import ROOT, corpus_text, score
from ..validation import coverage
from . import figaro_ch as CH
from .figaro_documented import ad_blocks, vigenere_systems

RESULT = ROOT / "data/results/figaro_cead_screen.json"
YEARS = (1885, 1895)
STAGE1, STAGE2 = 300, 20000


def read(blocks: list[str]) -> tuple[float, str, str]:
    """Best (score, mode/phase, plain) over phases and the two key modes."""
    best = (-99.0, "", "")
    joined = "".join(blocks)
    for ph in range(4):
        p = CH.decrypt(joined, ph)
        s = score(p, "fr")
        if s > best[0]:
            best = (s, f"running, phase {ph}", p)
        p = " ".join(CH.decrypt(b, ph) for b in blocks)
        s = score(p.replace(" ", ""), "fr")
        if s > best[0]:
            best = (s, f"restart, phase {ph}", p)
    return best


def shuffled(blocks: list[str], rnd: random.Random) -> list[str]:
    flat = list("".join(blocks))
    rnd.shuffle(flat)
    out, pos = [], 0
    for b in blocks:
        out.append("".join(flat[pos:pos + len(b)]))
        pos += len(b)
    return out


def pvalue(blocks: list[str], real: float, n: int, seed: int) -> float:
    rnd = random.Random(seed)
    return (sum(read(shuffled(blocks, rnd))[0] >= real for _ in range(n)) + 1) / (n + 1)


def test(blocks: list[str], seed: int, bar: float) -> dict:
    s, mode, plain = read(blocks)
    p = pvalue(blocks, s, STAGE1, seed)
    stage = 1
    if p <= 1 / (STAGE1 + 1):
        p, stage = pvalue(blocks, s, max(STAGE2, int(2 / bar)), seed + 1), 2  # the null must be able to reach the bar
    return {"score": round(s, 3), "mode": mode, "reading": plain, "coverage": coverage(plain.replace(" ", ""), "fr"),
            "p": p, "stage": stage, "passes": p <= bar}


def ads(years=YEARS) -> dict:
    return {k: [b.replace("W", "V") for b in v] for k, v in ad_blocks().items() if years[0] <= int(k[:4]) <= years[1]}


def all_keys() -> dict:
    """Every documented Vigenere key on every unsolved ad (1875-1900)."""
    a, keys, saved = ads((1800, 1999)), sorted({s["key"] for s in vigenere_systems()}), CH.KEY
    bar, rows = 0.05 / (len(a) * len(keys)), []
    try:
        for j, key in enumerate(keys):
            CH.KEY = key
            rows += [{"image": k, "key": key, "letters": len("".join(v)), **test(v, 7400 + 1000 * j + i, bar)} for i, (k, v) in enumerate(sorted(a.items()))]
    finally:
        CH.KEY = saved
    passed = sorted((r for r in rows if r["passes"]), key=lambda r: r["p"])
    return {"ads": len(a), "keys": keys, "bar": bar, "stage2": sum(r["stage"] == 2 for r in rows),
            "passed": [{k: r[k] for k in ("image", "key", "letters", "mode", "p", "coverage", "reading")} for r in passed]}


def planted(sizes: list[list[int]], seed: int = 72, noise: float = 0.05) -> list[list[str]]:
    rnd = random.Random(seed)
    text = re.sub(r"[^A-Z]", "", corpus_text("fr").upper()).replace("W", "V")
    out = []
    for sz in sizes:
        st = rnd.randrange(len(text) - 400)
        plain = text[st:st + sum(sz)]
        ph, running = rnd.randrange(4), rnd.random() < 0.5
        if running:
            enc = CH.encrypt(plain, ph)
        else:
            enc, pos = "", 0
            for k in sz:
                enc += CH.encrypt(plain[pos:pos + k], ph)
                pos += k
        enc = "".join(rnd.choice(CH.A) if rnd.random() < noise else c for c in enc)
        pos, blocks = 0, []
        for k in sz:
            blocks.append(enc[pos:pos + k])
            pos += k
        out.append(blocks)
    return out


def run(n_control: int = 20) -> dict:
    a = ads()
    bar = 0.05 / len(a)
    rows = [{"image": k, "letters": len("".join(v)), **test(v, 7200 + i, bar)} for i, (k, v) in enumerate(sorted(a.items()))]
    rnd = random.Random(73)
    sizes = [[len(b) for b in a[k]] for k in rnd.sample(sorted(a), n_control)]
    ctrl = [test(b, 9000 + i, bar) for i, b in enumerate(planted(sizes))]
    control = {"planted": n_control, "recovered": sum(c["passes"] for c in ctrl), "letters": [sum(s) for s in sizes],
               "p": [c["p"] for c in ctrl]}
    passed = sorted((r for r in rows if r["passes"]), key=lambda r: r["p"])
    return {"id": "figaro_cead_screen", "ads": len(rows), "bar": bar, "control": control,
            "passed": [{k: r[k] for k in ("image", "letters", "mode", "p", "coverage", "reading")} for r in passed], "rows": rows}


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["all_keys"]:
        res = json.loads(RESULT.read_text())
        res["all_keys"] = all_keys()
        RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
        x = res["all_keys"]
        print(x["ads"], x["keys"], x["bar"], "stage 2:", x["stage2"])
        for r in x["passed"]:
            print(r["image"], r["key"], r["letters"], r["mode"], r["p"], r["coverage"], "|", r["reading"][:80])
        raise SystemExit
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(res["ads"], "ads; bar", res["bar"], "control", res["control"]["recovered"], "of", res["control"]["planted"], res["control"]["letters"])
    for r in res["passed"]:
        print(r["image"], r["letters"], r["mode"], r["p"], r["coverage"], "|", r["reading"][:80])
    near = sorted(res["rows"], key=lambda r: (r["p"], -r["score"]))[len(res["passed"]):len(res["passed"]) + 8]
    print("next best:")
    for r in near:
        print(" ", r["image"], r["letters"], r["mode"], round(r["p"], 4), r["coverage"], "|", r["reading"][:70])
