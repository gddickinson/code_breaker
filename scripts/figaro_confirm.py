"""Run the three gates on the hand-transcribed ads, with independent seeds."""
import json

from codebreaker.attacks.classical import solve_symbols
from codebreaker.languages import ROOT, score
from codebreaker.segment import segment
from codebreaker.text import letters
from codebreaker.validation import coverage, null_test, positive_control, verdict

d = json.loads((ROOT / "data/mysteries/figaro_hand_readings.json").read_text())
out = {}
if __name__ == "__main__":
    for name, r in d.items():
        seq = list(letters(r["ciphertext"]))
        nt = null_test(seq, "fr", False, n_null=20, seed=5, iters=80000, restarts=8)
        pc = positive_control(seq, "fr", False, iters=80000, restarts=8, trials=4)
        v = verdict(pc, nt["z"], 73 * 2, nt["plaintext"], nt["score"], "fr")
        seeds = [solve_symbols(seq, "fr", False, restarts=8, iters=80000, seed=s)["plaintext"] for s in (11, 22, 33)]
        out[name] = {**r, "letters": len(seq), "z": nt["z"], "control": pc["mean"], "verdict": v, "plaintext": nt["plaintext"], "reading": segment(nt["plaintext"], "fr"), "coverage": coverage(nt["plaintext"], "fr"), "seeds_identical": sum(s == nt["plaintext"] for s in seeds)}
        print(name, len(seq), "z", nt["z"], "ctrl", pc["mean"], "cov", out[name]["coverage"], "seeds", out[name]["seeds_identical"], "\n ", v[:110], "\n ", out[name]["reading"], flush=True)
    (ROOT / "data/results/figaro_confirmed.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
