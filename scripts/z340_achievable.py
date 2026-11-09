"""What score can any single key reach on Z340's verified positions? Uses the published solution."""
import json
from collections import Counter, defaultdict

import numpy as np

import z340_5gram as Z
from codebreaker import kernels_n as N
from codebreaker.languages import ROOT, model
from codebreaker.text import similarity, to_ints

if __name__ == "__main__":
    votes = defaultdict(Counter)
    for s, p in zip(Z.SEQ, Z.TARGET):
        votes[s][p] += 1
    key = {s: c.most_common(1)[0][0] for s, c in votes.items()}
    text = "".join(key[s] for s in Z.SEQ)
    res = {"letters_where_key_matches_solution": round(similarity(text, Z.TARGET), 3), "achievable_objective": round(Z.objective(text, 2.0), 1), "solution_objective": round(Z.objective(Z.TARGET, 2.0), 1), "best_found": json.loads((ROOT / "data/results/z340_5gram_long.json").read_text())["best_objective"]}
    print(res)
    (ROOT / "data/results/z340_achievable.json").write_text(json.dumps(res, indent=1))
