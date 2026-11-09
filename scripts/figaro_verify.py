"""Three-gate verification of flagged Le Figaro ads, with full readings and independent seeds."""
import json
from concurrent.futures import ProcessPoolExecutor

from codebreaker.attacks.classical import solve_symbols
from codebreaker.languages import ROOT
from codebreaker.segment import segment
from codebreaker.text import letters
from codebreaker.translate import translate
from codebreaker.validation import null_test, positive_control, verdict

OUT = ROOT / "data/sources/figaro"


def job(a):
    name, direction, text = a
    seq = list(letters(text))
    if direction == "reversed":
        seq = seq[::-1]
    nt = null_test(seq, "fr", False, n_null=16, seed=11, iters=60000, restarts=6)
    pc = positive_control(seq, "fr", False, iters=60000, restarts=6, trials=4)
    v = verdict(pc, nt["z"], 73 * 2, nt["plaintext"], nt["score"], "fr")
    seeds = [solve_symbols(seq, "fr", False, restarts=8, iters=60000, seed=s)["plaintext"] for s in (101, 202, 303)]
    return {"image": name, "direction": direction, "letters": len(seq), "ocr": text, "z": nt["z"], "control": pc["mean"], "verdict": v, "plaintext": nt["plaintext"], "reading": segment(nt["plaintext"], "fr"), "seeds_agree": sum(s == nt["plaintext"] for s in seeds)}


if __name__ == "__main__":
    rows = json.loads((ROOT / "data/results/figaro_hunt.json").read_text())["flagged"]
    ocr = json.loads((OUT / "ocr.json").read_text())
    with ProcessPoolExecutor(6) as ex:
        res = list(ex.map(job, [(r["name"], r["direction"], ocr[r["name"]]) for r in rows]))
    res.sort(key=lambda r: -r["z"])
    ads = {a["image"].replace("/", "_"): a for a in json.loads((OUT / "ads.json").read_text())}
    for r in res:
        a = ads.get(r["image"], {})
        r["date"], r["listed_unsolved"] = a.get("date"), not a.get("solved", True)
        r["english"] = translate(r["reading"], "fr")["translation"]
        print(r["image"], r["date"], "unsolved:", r["listed_unsolved"], r["letters"], "z", r["z"], "ctrl", r["control"], "seeds", r["seeds_agree"], flush=True)
        print("  ", r["verdict"][:80]); print("  FR:", r["reading"]); print("  EN:", r["english"], flush=True)
    (ROOT / "data/results/figaro_verified.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
