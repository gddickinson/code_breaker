"""Round 74: a style-matched word gate for the table 2119 family, fixed and committed before it was run.

Round 73 solved the family blind (control 100%, beats shuffles, blind key = documented key on 97.7%) but its coverage
fell under the word bar, which comes from a planted control of unabbreviated French. The family writes abbreviated
French mixed with English. Pre-registered change: ONLY the planted control. Its style is measured from the readings
under the documented key, and these parameters only, not the readings themselves, shape the control:
  p_en      share of words that are English and not French;
  run_en    mean length of runs of English words;
  p_abbrev  share of words that are no dictionary word but the start of one;
  cut_len   the lengths of those abbreviated words (sampled from).
The control takes French and English corpus text, switches language in runs that match p_en and run_en, cuts words of
4+ letters with probability p_abbrev / (share of words with 4+ letters) to a sampled length, and enciphers with a random
homophonic key of the family's symbol count. Everything else is Round 73 unchanged: the same blind solve, refinement,
3 shuffled copies, coverage in French, and the gates (control >= 70% letters; refined share above every shuffle;
coverage >= 0.8 of the refined planted control's). Seed fixed at 74. The control's own style is measured and reported (it came out milder before running, 19% English and 11% abbreviated
against 26% and 15%, because short words such as 'on' are French too; this makes the bar stricter, and it was not tuned).
A pass would move the family to tier A only for
leads whose readings were checked by eye."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

from ..languages import ROOT, corpus_text, model
from .figaro_blind_family import family
from .figaro_tierc2 import prefixes
from .figaro_wordrefine import test

RESULT = ROOT / "data/results/figaro_style_gate.json"
SEED = 74


@lru_cache(maxsize=2)
def vocab(lang: str) -> frozenset:
    return frozenset(str(w).upper() for w in model(lang)["words"] if len(w) >= 2) | ({"A", "Y"} if lang == "fr" else {"A", "I"})


def classify(word: str) -> str:
    fr, en = vocab("fr"), vocab("en")
    if word in fr:
        return "fr"
    if word in en:
        return "en"
    return "abbrev" if word in prefixes() else "other"


def style(words: dict, key: dict) -> dict:
    kinds, cuts = [], []
    for ws in words.values():
        for w in ws:
            plain = "".join(key.get(c, "?") for c in w).upper()
            k = classify(plain)
            kinds.append(k)
            if k == "abbrev":
                cuts.append(len(plain))
    runs, cur = [], 0
    for k in kinds + ["fr"]:
        if k == "en":
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    n = len(kinds)
    return {"words": n, "p_en": kinds.count("en") / n, "run_en": sum(runs) / max(len(runs), 1), "p_abbrev": kinds.count("abbrev") / n,
            "p_other": kinds.count("other") / n, "cut_len": cuts}


def planted_style(st: dict, seed: int = SEED):
    """A planted-control generator for figaro_wordrefine.test, matching the measured style."""

    def make(words: list[list[str]]) -> tuple[list[list[str]], str]:
        rnd = random.Random(seed)
        fr = re.findall(r"[a-z]+", corpus_text("fr").lower())
        en = re.findall(r"[a-z]+", corpus_text("en").lower())
        p_switch_back = 1 / st["run_en"]
        p_switch_in = st["p_en"] * p_switch_back / max(1 - st["p_en"], 1e-9)
        i_fr, i_en = rnd.randrange(len(fr) - 5000), rnd.randrange(len(en) - 5000)
        lang, plain = "fr", []
        for _ in words:
            lang = ("en" if rnd.random() < p_switch_in else "fr") if lang == "fr" else ("fr" if rnd.random() < p_switch_back else "en")
            if lang == "fr":
                w, i_fr = fr[i_fr], i_fr + 1
            else:
                w, i_en = en[i_en], i_en + 1
            plain.append(w)
        long_share = sum(len(w) >= 4 for w in plain) / len(plain)
        p_cut = min(1.0, st["p_abbrev"] / max(long_share, 1e-9))
        cut = []
        for w in plain:
            if len(w) >= 4 and rnd.random() < p_cut:
                k = min(rnd.choice(st["cut_len"]), len(w) - 1)
                w = w[:max(k, 2)]
            cut.append(w)
        n_sym = len({c for w in words for c in w})
        letters = sorted({c for w in cut for c in w})
        pool = [f"s{i}" for i in range(max(n_sym, len(letters)))]
        rnd.shuffle(pool)
        enc = {c: [pool[i]] for i, c in enumerate(letters)}
        for extra in pool[len(letters):]:
            enc[rnd.choice("eaisnrtu")].append(extra)
        return [[rnd.choice(enc[c]) for c in w] for w in cut], " ".join(cut)

    return make


def run() -> dict:
    words, key = family("2119")
    st = style(words, key)
    flat = [w for ws in words.values() for w in ws]
    ks = [classify(w.upper()) for w in planted_style(st)(flat)[1].split()]
    control_style = {k: round(ks.count(k) / len(ks), 3) for k in ("fr", "en", "abbrev", "other")}
    with ProcessPoolExecutor(7) as ex:
        r = test("table 2119 (style-matched control)", ex, seed=7300, ads=words, planted=planted_style(st))
    r.pop("readings", None)
    return {"id": "figaro_style_gate", "style": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in st.items() if k != "cut_len"},
            "control_style": control_style, "cut_len_mean": round(sum(st["cut_len"]) / len(st["cut_len"]), 2), **{k: r[k] for k in ("blind_share", "refined_share", "null",
            "planted_accuracy", "planted_refined_coverage", "coverage", "gates")}, "bar": round(0.8 * r["planted_refined_coverage"], 3)}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items()}, indent=1))
