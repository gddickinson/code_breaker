"""Round 87: every real-material benchmark item through the Workbench crack, blind (no language, no system given).
Writes data/results/realbench.json. Usage: PYTHONPATH=. python scripts/run_realbench.py [budget_seconds]"""
import json
import sys
import time
from collections import defaultdict

from codebreaker.crack import crack
from codebreaker.languages import ROOT
from codebreaker.mysteries.realbench import items
from codebreaker.text import letters, similarity

OUT = ROOT / "data/results/realbench.json"
RIGHT = 0.8  # share of letters right for an answer to count as recovered


def one(item: dict, budget: float) -> dict:
    t0, fin = time.time(), None
    for ev in crack(item["cipher"], budget=budget):
        if ev["event"] == "finish":
            fin = ev
    best = (fin or {}).get("best") or {}
    got = letters(best.get("plaintext", ""))
    acc = max(similarity(got, item["truth"]), similarity(got[::-1], item["truth"]))
    level = (fin or {}).get("verdict", {}).get("level", "none")
    return {"name": item["name"], "tier": item["tier"], "system": item["system"], "letters": len(item["truth"]), "found_by": best.get("cipher", ""),
            "lang": best.get("lang", ""), "accuracy": round(acc, 3), "verdict": level, "recovered": acc >= RIGHT,
            "wrong_but_readable": level == "readable" and acc < RIGHT, "seconds": round(time.time() - t0, 1)}


def summarise(rows: list[dict]) -> dict:
    groups = defaultdict(list)
    for r in rows:
        key = r["system"] if r["tier"] == 1 else ("substitution table" if r["system"].startswith("table") else r["system"])
        groups[key].append(r)
    out = {}
    for k, g in groups.items():
        out[k] = {"items": len(g), "recovered": sum(r["recovered"] for r in g), "called_readable": sum(r["verdict"] == "readable" for r in g),
                  "wrong_but_readable": sum(r["wrong_but_readable"] for r in g), "median_letters": sorted(r["letters"] for r in g)[len(g) // 2]}
    return out


if __name__ == "__main__":
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
    rows = []
    for it in items():
        rows.append(one(it, budget))
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    res = {"id": "realbench", "budget": budget, "right_bar": RIGHT, "summary": summarise(rows), "rows": rows,
           "recovered": sum(r["recovered"] for r in rows), "items": len(rows), "wrong_but_readable": sum(r["wrong_but_readable"] for r in rows)}
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res["summary"], indent=1, ensure_ascii=False))
