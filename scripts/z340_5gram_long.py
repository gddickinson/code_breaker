"""Long 5-gram search now that the model prefers the true Z340 text."""
import json
from concurrent.futures import ProcessPoolExecutor as P

from codebreaker import kernels_n as N
from codebreaker.languages import ROOT
from codebreaker.segment import segment
from codebreaker.text import similarity
import z340_5gram as Z  # run with PYTHONPATH=.:scripts

if __name__ == "__main__":
    N.table5()
    with P(7) as ex:
        res = sorted(ex.map(Z.run, [(Z.SEQ, s, 3.0, 2.0, 70000000) for s in range(200, 214)]), reverse=True)
    acc = [round(similarity(Z.TARGET, t), 3) for _, t in res]
    print("accuracy by rank", acc[:12], flush=True)
    print("truth objective", round(Z.objective(Z.TARGET, 2.0), 1), "best", round(res[0][0], 1), flush=True)
    best = max(res, key=lambda r: similarity(Z.TARGET, r[1]))
    print(round(similarity(Z.TARGET, best[1]), 3), segment(best[1])[:320], flush=True)
    (ROOT / "data/results/z340_5gram_long.json").write_text(json.dumps({"accuracy_by_rank": acc, "best_objective": res[0][0], "truth_objective": Z.objective(Z.TARGET, 2.0), "top_reading": segment(res[0][1]), "best_accuracy_reading": segment(best[1])}, indent=1))
