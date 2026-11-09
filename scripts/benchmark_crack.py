"""Measure the Workbench crack on every attackable cipher: a known text, a random key, a fixed time allowance."""
import json
import random
import sys

from codebreaker.ciphers import REGISTRY
from codebreaker.ciphers.base import DEMO_PLAIN
from codebreaker.crack import crack
from codebreaker.languages import ROOT
from codebreaker.text import letters, similarity

OUT = ROOT / "data/results/crack_benchmark.json"


def main(budget: float = 20) -> None:
    rows, rng = [], random.Random(77)
    for cid, c in REGISTRY.items():
        if not c.attack or not c.keygen:
            continue
        try:
            key = c.keygen(rng)
            ct = c.encrypt(DEMO_PLAIN, **key)
            truth = c.decrypt(ct, **key)
            end = list(crack(ct, budget, "en"))[-1]
        except Exception as exc:  # recorded, because a cipher the pipeline cannot run is a result too
            rows.append({"cipher": cid, "error": repr(exc)[:160]})
            continue
        best = end["best"] or {}
        rows.append({"cipher": cid, "name": c.name, "family": c.family, "found_by": best.get("cipher"), "accuracy": round(similarity(letters(truth), letters(best.get("plaintext", ""))), 3), "verdict": end["verdict"]["level"], "tried": end["tried"]})
        print(rows[-1], flush=True)
    ok = [r for r in rows if "accuracy" in r]
    out = {"budget": budget, "ciphers": len(rows), "recovered": sum(r["accuracy"] >= 0.9 for r in ok), "called_readable": sum(r["verdict"] == "readable" for r in ok), "wrong_but_readable": sum(r["verdict"] == "readable" and r["accuracy"] < 0.9 for r in ok), "rows": rows}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print({k: v for k, v in out.items() if k != "rows"})


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 20)
