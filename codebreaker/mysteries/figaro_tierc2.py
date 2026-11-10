"""Round 71: the remaining tier-C families retested from scan transcriptions with matched nulls.

Pre-registered before running:
  Berthe (table 2217): each ad is decoded under all documented letter tables; statistic = the best French coverage;
    null = the same best-of-all-tables search on 1,000 shuffled copies (word lengths kept).
  C. H. key (Vigenere CEAD, no W): each block is searched with figaro_ch.search (one slip allowed; phase 0 for the
    C. H. writer, whose key restarts at each block, all four phases for the six V. E. 3 ads of 1889-92, whose key runs on
    across words); statistic = summed quadgram score;
    null = the identical search on 1,000 copies (200 at first: its smallest p, 1/201, sat above the bar) with the letters shuffled across blocks (block lengths kept).
  Short table 2119 ads (abbreviated words, 'MA FEM CHE'): statistic = share of letters in words that are a dictionary
    word or the start (2+ letters) of one, under the fixed full key; null = 2,000 shuffled copies; positive control =
    abbreviated French corpus phrases enciphered with the same key and tested the same way; specificity = the same share
    under the other 31 documented digit tables (reported, should be lower).
Bonferroni over all ads tested."""
import json
import random
import re
from functools import lru_cache

from ..languages import ROOT, corpus_text
from . import figaro_2119 as T
from . import figaro_ch as CH
from .figaro_digit_family import digit_tables
from .figaro_documented import systems as letter_systems
from .figaro_tierc import _best_letters

RESULT = ROOT / "data/results/figaro_tierc2.json"
SRC = ROOT / "data/sources/figaro"
BERTHE = ["1882_18820601-5.jpg", "1882_18820701-5.jpg", "1882_18821224-5.jpg"]
VE3 = ["1889_18891101-VE3.jpg", "1890_18900701-VE3.jpg", "1890_18901026-VE3.jpg", "1891_18910611-VE3.jpg", "1891_18911226-VE3.jpg", "1892_18920721-VE3.jpg"]
VIG = {"1884_18840730-CH.jpg": (0,), "1884_18840805-CH.jpg": (0,), "1886_18860629-CH.jpg": (0,), **{i: (0, 1, 2, 3) for i in VE3}}
SHORT = ["1886_18860531-E.jpg", "1886_18860124-T.jpg", "1886_18860602-T.jpg", "1886_18860613-T.jpg"]


def sources() -> dict:
    sweep = json.loads((SRC / "sweep_transcription.json").read_text())
    sweep = sweep.get("ads", sweep)
    ch = json.loads((SRC / "ch_transcription.json").read_text())
    fam = json.loads((SRC / "letter_digit_family.json").read_text())
    two = {**fam["checked_residual"], **fam["checked_t42"]}
    return {"berthe": {i: sweep[i]["cipher"] for i in BERTHE}, "vig": {i: {**ch["ads"], **ch["other_writers"]}[i]["blocks"] for i in VIG},
            "short": {i: two[i] for i in SHORT}}


def berthe_test(text: str, seed: int, trials: int = 1000) -> dict:
    sys_ = [s for s in letter_systems() if s["kind"] == "table"]
    words = text.lower().split()
    cov, sid, reading = _best_letters(words, sys_)
    rnd, flat, null = random.Random(seed), list("".join(words)), []
    for _ in range(trials):
        rnd.shuffle(flat)
        pos, sh = 0, []
        for w in words:
            sh.append("".join(flat[pos:pos + len(w)]))
            pos += len(w)
        null.append(_best_letters(sh, sys_)[0])
    return {"system": f"table {sid}", "reading": reading, "coverage": round(cov, 3), "p": (sum(x >= cov for x in null) + 1) / (trials + 1)}


def _vig(blocks: list[str], phases) -> tuple[float, str]:
    got = [CH.search(b, phases=phases) for b in blocks]
    return sum(g["score"] for g in got), " ".join(g["plain"] for g in got)


def vig_test(blocks: list[str], phases, seed: int, trials: int = 1000) -> dict:
    blocks = [re.sub(r"[^A-Z]", "", b.upper()).replace("W", "V") for b in blocks]
    real, reading = _vig(blocks, phases)
    rnd, flat, null = random.Random(seed), list("".join(blocks)), []
    for _ in range(trials):
        rnd.shuffle(flat)
        pos, sh = 0, []
        for b in blocks:
            sh.append("".join(flat[pos:pos + len(b)]))
            pos += len(b)
        null.append(_vig(sh, phases)[0])
    return {"system": "Vigenere CEAD, no W", "reading": reading, "score": round(real, 2), "p": (sum(x >= real for x in null) + 1) / (trials + 1)}


def pooled_ve3(vig: dict, trials: int = 1000, seed: int = 7130) -> dict:
    """All six V. E. 3 ads at once: summed score of the per-ad searches against the same with each ad shuffled."""
    ads = [[re.sub(r"[^A-Z]", "", b.upper()) for b in vig[i]] for i in VE3]
    real = sum(_vig(a, (0, 1, 2, 3))[0] for a in ads)
    rnd, null = random.Random(seed), []
    for _ in range(trials):
        null.append(sum(_vig(["".join(rnd.sample(a[0], len(a[0])))], (0, 1, 2, 3))[0] for a in ads))
    return {"image": "V. E. 3 pooled (6 ads)", "family": "C. H. key", "system": "Vigenere CEAD, no W", "score": round(real, 2),
            "reading": "", "p": (sum(x >= real for x in null) + 1) / (trials + 1)}


@lru_cache(maxsize=1)
def prefixes() -> frozenset:
    return frozenset(w[:i] for w in T.vocab() for i in range(2, len(w) + 1)) | {"A", "Y"}


def abbrev_share(words: list[str]) -> float:
    p, n = prefixes(), sum(map(len, words))
    return sum(len(w) for w in words if w in p) / n if n else 0.0


def short_test(text: str, key: dict, seed: int, trials: int = 2000) -> dict:
    real, rnd = abbrev_share(T.decode(text, key)), random.Random(seed)
    null = [abbrev_share(T.decode(T.shuffled(text.upper(), rnd), key)) for _ in range(trials)]
    others = [abbrev_share(T.decode(text, t["key"])) for t in digit_tables() if t["id"] != "2119"]
    return {"system": "table 2119 full key, abbreviated words", "reading": " ".join(T.decode(text, key)), "share": round(real, 3),
            "p": (sum(x >= real for x in null) + 1) / (trials + 1), "best_other_table": round(max(others), 3)}


def planted_short(key: dict, n: int = 12, seed: int = 71) -> list[str]:
    """Abbreviated French phrases (each word cut to 2-4 letters, as in 'MA FEM CHE') enciphered with the same key."""
    inv = {}
    for sym, letter in key.items():
        inv.setdefault(letter, []).append(sym.lower())
    rnd = random.Random(seed)
    words = [w for w in re.findall(r"[A-Z]+", corpus_text("fr").upper()) if all(c in inv for c in w)]
    out = []
    for _ in range(n):
        st = rnd.randrange(len(words) - 20)
        cut = [w if len(w) <= 3 else w[:rnd.randint(2, 4)] for w in words[st:st + 11]]
        out.append(" ".join("".join(rnd.choice(inv[c]) for c in w) for w in cut))
    return out


def run() -> dict:
    src, key, rows = sources(), T.full_key(), []
    for j, (img, t) in enumerate(src["berthe"].items()):
        rows.append({"image": img, "family": "Berthe", **berthe_test(t, 7100 + j)})
    for j, (img, b) in enumerate(src["vig"].items()):
        rows.append({"image": img, "family": "C. H. key", **vig_test(b, VIG[img], 7110 + j)})
    for j, (img, t) in enumerate(src["short"].items()):
        rows.append({"image": img, "family": "table 2119 short", **short_test(t, key, 7120 + j)})
    rows += [pooled_ve3(src["vig"])]
    bar = 0.05 / len(rows)
    for r in rows:
        r["passes"] = r["p"] <= bar
    ctrl = [short_test(t, key, 7200 + j, trials=500)["p"] for j, t in enumerate(planted_short(key))]
    control = {"planted": len(ctrl), "recovered": sum(p <= bar for p in ctrl), "p": ctrl}
    return {"id": "figaro_tierc2", "bar": bar, "rows": rows, "short_control": control, "passed": [r["image"] for r in rows if r["passes"]]}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for r in res["rows"]:
        print(r["image"][:22], r["family"], r["system"], round(r["p"], 4), r["passes"], "|", r["reading"][:90])
    print("control", res["short_control"]["recovered"], "of", res["short_control"]["planted"], "bar", res["bar"])
