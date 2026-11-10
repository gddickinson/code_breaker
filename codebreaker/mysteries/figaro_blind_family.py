"""Round 73: the large tier-B families solved blind, as Jane and B were (Round 56), to test the three gates.

The table 2119, table 2402 and Berthe (2217) readings so far use the documented tables, so they rest on a key that was
given, not found. Here each family's scan transcriptions are pooled and the Round 56 pipeline runs without any key:
blind homophonic solve of French (best of 7 seeds), refinement with the printed word breaks, the identical pipeline on
3 copies with the symbols shuffled across the family (word lengths kept), and a planted French control of the same word
count and symbol count. Gates (fixed before running): control >= 70% recovered; refined share above every refined
shuffle; coverage >= 0.8 of the refined planted control's. Also reported, not gated: agreement of the blind key with
the documented key, as the share of symbol occurrences given the same letter."""
import json
from concurrent.futures import ProcessPoolExecutor

from ..languages import ROOT
from . import figaro_2119 as T
from .figaro_2402 import ads as ads2402, key2402
from .figaro_documented import systems as letter_systems
from .figaro_keys import OUT
from .figaro_wordrefine import test

RESULT = ROOT / "data/results/figaro_blind_family.json"
SECTIONS_2119 = ("ads", "checked_screen", "checked_rescreen", "checked_residual", "checked_t42", "checked_early")


def family(name: str) -> tuple[dict, dict]:
    """{ad: [word symbol lists]} and the documented key (symbol -> lowercase letter)."""
    if name == "2119":
        d = json.loads(T.FAMILY.read_text())
        texts = {k: v for s in SECTIONS_2119 for k, v in d.get(s, {}).items()}
        key = T.full_key()
    elif name == "2402":
        texts, key = ads2402(), key2402()
    elif name == "2217":
        sweep = json.loads((OUT / "sweep_transcription.json").read_text())["ads"]
        doc = json.loads((OUT / "documented_transcription.json").read_text())["ads"]
        texts = {k: v["cipher"] for k, v in sweep.items() if v.get("system") == "2217"}
        texts.update({k: v["cipher"] for k, v in doc.items() if isinstance(v, dict) and v.get("table") == "2217"})
        key = next(s for s in letter_systems() if s["id"] == "2217")["map"]
    else:
        raise ValueError(name)
    words = {k: [list(w) for w in t.upper().split()] for k, t in texts.items()}
    return words, {str(k).upper(): str(v).lower() for k, v in key.items()}


def agreement(words: dict, blind: dict, documented: dict) -> float:
    occ = [c for ws in words.values() for w in ws for c in w if c in documented]
    return sum(blind.get(c, "?") == documented[c] for c in occ) / len(occ) if occ else 0.0


def run(names=("2119", "2402", "2217")) -> dict:
    out = {}
    with ProcessPoolExecutor(7) as ex:
        for i, n in enumerate(names):
            words, doc = family(n)
            r = test(f"table {n}", ex, seed=7300 + i, ads=words)
            r["agreement_with_documented"] = round(agreement(words, r["key"], doc), 3)
            r["ads"], r["symbols"] = len(words), sum(len(w) for ws in words.values() for w in ws)
            out[n] = r
    return {"id": "figaro_blind_family", "families": out}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for n, r in res["families"].items():
        print(n, r["ads"], "ads", r["symbols"], "symbols | blind", r["blind_share"], "-> refined", r["refined_share"], "null", r["null"],
              "| planted", r["planted_accuracy"], r["planted_refined_coverage"], "| coverage", r["coverage"], r["gates"], "| agreement", r["agreement_with_documented"])
        for k, t in list(r["readings"].items())[:3]:
            print("   ", k[:14], t[:100])
