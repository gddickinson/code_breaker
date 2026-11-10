"""Round 69: tier-C ads read under documented systems, transcribed from the scans and retested with a fair null.

Three groups: writer 25 (1894) under Vigenere CD without W (the C. H. search: phase and one slip, against the same search
on shuffled copies); the 'Jeannette' ad of 7 Oct 1881 as reversed text under all 60 letter tables (best of all against
shuffles); and digit-table ads, either dotted number words under the 63 fixed numeric systems of Round 67 (letters printed
in clear kept) or digit-letter words under all 32 digit tables (rank and shuffles). Bonferroni over the ten ads."""
import json
import random
import re

from ..languages import ROOT
from ..validation import coverage
from . import figaro_2119 as T
from . import figaro_ch as CH
from .figaro_digit_family import digit_tables
from .figaro_documented import apply, systems as letter_systems
from .figaro_dotted import systems as numeric_systems

RESULT = ROOT / "data/results/figaro_tierc.json"
VIG = {"1894_18940911-25.jpg": "Vrxv dlgq yrxg frpqgv ddkvtv syg m'gqxrk", "1894_18940920-25.jpg": "Gvrfth flpht dyhe xql qy uhtdk xthu sglplg",
       "1894_18941003-25.jpg": "Eropg xx zqyfucv ork ugvvh rdtfu zgqfugqk"}
REVERSED = {"1881_18811007.jpg": "Nljr sjvpla ladedm lmjdt sivqivqt vq lrjrcl"}
DOTTED = {"1875_18750923-5.jpg": "1.0.4.7 11.4.0.7 13.1.9.24.0.1.24.7 1.20.0.7 5.3.7 7.9.17.3.7.1.8 24.3.9.1 57.1 28 8.4.7.2.1",
          "1889_18891019-CHERY.jpg": "5.7.20.5 r 1m16 25.1.7.8e23116.5 16.14 4.20.5 12.24.20.16 2.16 25.5.16e 12 6.1.20 5.16.7.23.16 17.16.24m16 12.15.1.4.16e",
          "1889_18891108-CHERY.jpg": "6.123 23 16t6.4.16 21 a17f123e 6 12.20.24.16 4.15a8a25.6.a18e 24.16 4e6.4.1.8.16.4.12.5 6 20.15 1.23.12.6 4 12 258 25.16 15.1.7.6.16 2.12.5 15.16 24.1.20 6 12.15.1.4.16",
          "1877_18771006-OPQ.jpg": "19.24.7.4.2.7 8 19 5.8.2 6.13.7.3.6.1"}
DIGIT = {"1890_18900203-LILI.jpg": "d4nn2 k2 w45e 2us2 u45k qs2t e2 w d4nn2 k2 l2s n23mm25s w n 13n2s w 13n2 us4q k 1qq2m u45k 2u2 t25m c40i 32 u 13 n2",
         "1890_18900709-Po.jpg": "71 84v 647 a849 52 a84n484 74 d238 a5830"}
TRIALS = 1000


def vig_test(text: str, seed: int) -> dict:
    saved = CH.KEY
    CH.KEY = "CD"
    try:
        letters = re.sub(r"[^A-Z]", "", text.upper()).replace("W", "V")
        got = CH.search(letters, phases=(0, 1))
        rnd = random.Random(seed)
        null = [CH.search("".join(rnd.sample(letters, len(letters))), phases=(0, 1))["score"] for _ in range(200)]
    finally:
        CH.KEY = saved
    p = (sum(x >= got["score"] for x in null) + 1) / 201
    return {"system": "Vigenere CD, no W", "reading": got["plain"], "coverage": got["coverage"], "p": p}


def _best_letters(words: list[str], sys_) -> tuple[float, str, str]:
    top = (-1.0, "", "")
    for s in sys_:
        d = " ".join(apply(s, w.upper()) for w in words)
        c = coverage(d.replace(" ", "").replace("?", ""), "fr")
        if c > top[0]:
            top = (c, s["id"], d)
    return top


def reversed_test(text: str, seed: int) -> dict:
    sys_ = [s for s in letter_systems() if s["kind"] == "table"]
    words = [w[::-1] for w in reversed(text.lower().split())]
    cov, sid, reading = _best_letters(words, sys_)
    rnd, flat = random.Random(seed), list("".join(words))
    null = []
    for _ in range(200):
        rnd.shuffle(flat)
        pos, sh = 0, []
        for w in words:
            sh.append("".join(flat[pos:pos + len(w)]))
            pos += len(w)
        null.append(_best_letters(sh, sys_)[0])
    return {"system": f"reversed, table {sid}", "reading": reading, "coverage": cov, "p": (sum(x >= cov for x in null) + 1) / 201}


def _dotted_decode(tokens: list[str], key: dict) -> str:
    return " ".join("".join(key.get(p, p.upper() if p.isalpha() else "?") for p in re.findall(r"\d+|[a-z]", t)) for t in tokens)


def _best_numeric(tokens, sys_) -> tuple[float, str, str]:
    top = (-1.0, "", "")
    for name, key in sys_:
        d = _dotted_decode(tokens, key)
        if d.count("?") > 0.2 * len(d.replace(" ", "")):
            continue
        c = coverage(d.replace(" ", "").replace("?", ""), "fr")
        if c > top[0]:
            top = (c, name, d)
    return top


def dotted_test(text: str, seed: int) -> dict:
    sys_, tokens = numeric_systems(), text.split()
    cov, name, reading = _best_numeric(tokens, sys_)
    nums = [n for t in tokens for n in re.findall(r"\d+", t)]
    rnd, null = random.Random(seed), []
    for _ in range(TRIALS):
        sh = nums[:]
        rnd.shuffle(sh)
        it = iter(sh)
        null.append(_best_numeric([re.sub(r"\d+", lambda m: next(it), t) for t in tokens], sys_)[0])
    return {"system": name, "reading": reading, "coverage": cov, "p": (sum(x >= cov for x in null) + 1) / (TRIALS + 1)}


def digit_test(text: str, seed: int) -> dict:
    tables = digit_tables()
    best = max(tables, key=lambda t: T.share(text, t["key"]))
    s = T.share(text, best["key"])
    rnd = random.Random(seed)
    null = []
    for _ in range(TRIALS):
        sh = T.shuffled(text.upper(), rnd)
        null.append(max(T.share(sh, t["key"]) for t in tables))
    return {"system": f"digit table {best['id']}", "reading": " ".join(T.decode(text, best["key"])), "coverage": round(s, 3),
            "p": (sum(x >= s for x in null) + 1) / (TRIALS + 1)}


def run() -> dict:
    rows = []
    for j, (img, t) in enumerate(VIG.items()):
        rows.append({"image": img, **vig_test(t, 6900 + j)})
    for j, (img, t) in enumerate(REVERSED.items()):
        rows.append({"image": img, **reversed_test(t, 6910 + j)})
    for j, (img, t) in enumerate(DOTTED.items()):
        rows.append({"image": img, **dotted_test(t, 6920 + j)})
    for j, (img, t) in enumerate(DIGIT.items()):
        rows.append({"image": img, **digit_test(t, 6930 + j)})
    bar = 0.05 / len(rows)
    for r in rows:
        r["passes"] = r["p"] <= bar
    return {"id": "figaro_tierc", "bar": bar, "rows": rows, "passed": [r["image"] for r in rows if r["passes"]]}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for r in res["rows"]:
        print(r["image"][:22], r["system"], r["coverage"], round(r["p"], 4), r["passes"], "|", r["reading"][:90])
