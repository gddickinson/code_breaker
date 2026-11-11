"""Round 40: pool each writer's enciphered text and solve it blind as one substitution.

Many ads mix plain words with enciphered stretches, so plain stretches (runs of 6+ letters covered by French words or
word beginnings, Round 36) are cut out first. Each signature's remaining letters are pooled and solved by quadgram
annealing; the best of 7 seeds by score is kept. Gates, as in validation.verdict: a planted control of the same length
(printed forms of solved ads under a random key) must be recovered; the score must beat shuffled copies solved the same
way; the reading must reach 0.8 of the planted control's French word coverage. Real-data control: solved writers."""
import json
import random
from concurrent.futures import ProcessPoolExecutor

from ..attacks.classical import solve_symbols
from ..languages import ROOT, score
from ..validation import coverage
from .figaro_keys import OUT, cipher_words
from .figaro_plainness import abbreviated, clean, tokens
from ..third_party import need

RESULT = ROOT / "data/results/figaro_pooled.json"
MIN_LETTERS, SEEDS, SHUFFLES, PLAIN_RUN = 150, 7, 3, 6


def plain_mask(t: str) -> list[bool]:
    """Letters inside runs of French words or 4+ letter word beginnings that are at least PLAIN_RUN long."""
    full, stems = tokens()
    n = len(t)
    best, back = [0] * (n + 1), [None] * (n + 1)
    for i in range(1, n + 1):
        best[i], back[i] = best[i - 1], None
        for j in range(max(0, i - 14), i - 2):
            w = t[j:i]
            if (w in full or (len(w) >= 4 and w in stems)) and best[j] + i - j > best[i]:
                best[i], back[i] = best[j] + i - j, j
    covered, i = [False] * n, n
    while i > 0:
        if back[i] is None:
            i -= 1
        else:
            for k in range(back[i], i):
                covered[k] = True
            i = back[i]
    mask, i = [False] * n, 0
    while i < n:
        j = i
        while j < n and covered[j]:
            j += 1
        if j - i >= PLAIN_RUN:
            mask[i:j] = [True] * (j - i)
        i = max(j, i + 1)
    return mask


def cipher_part(t: str) -> str:
    t = clean(t)
    return "".join(c for c, p in zip(t, plain_mask(t)) if not p)


def signature(name: str) -> str:
    return name.split("-", 1)[1][:-4] if "-" in name else ""


def groups(solved: bool) -> dict:
    """Signature -> pooled enciphered letters, from the OCR of solved or unsolved ads."""
    ads = {a["image"].replace("/", "_"): a for a in json.loads(need(OUT / "ads.json").read_text())}
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    out = {}
    for n in sorted(set(otsu) | set(raw)):
        a = ads.get(n)
        if a is None or (a["solved"] in (True, "True")) != solved or not signature(n) or "VTA" in n:
            continue
        sets = [e for s in (otsu, raw) for e in s.get(n, {}).values() if e]
        t = "".join(max((cipher_words(e) for e in sets), key=lambda w: sum(map(len, w)), default=[]))
        out.setdefault(signature(n), []).append(cipher_part(t))
    return {k: "".join(v) for k, v in out.items() if len("".join(v)) >= MIN_LETTERS}


def _solve(a):
    text, seed = a
    r = solve_symbols(list(text.upper()), "fr", seed=seed, iters=100000, restarts=8)
    return score(r["plaintext"], "fr"), r["plaintext"]


def best_of(text: str, ex) -> tuple[float, str]:
    return max(ex.map(_solve, [(text, s) for s in range(SEEDS)]), key=lambda x: x[0])


def planted(n: int, seed: int) -> tuple[str, str]:
    ads = [a for a in json.loads(need(OUT / "ads.json").read_text()) if a["solved"] in (True, "True") and a["text"]]
    rnd = random.Random(seed)
    plain = ""
    while len(plain) < n:
        plain += abbreviated(rnd.choice(ads)["text"])
    plain = plain[:n]
    k = list("abcdefghijklmnopqrstuvwxyz")
    rnd.shuffle(k)
    return plain, "".join(dict(zip("abcdefghijklmnopqrstuvwxyz", k))[c] for c in plain)


def judge(sig: str, text: str, ex, seed: int = 40) -> dict:
    rnd = random.Random(seed)
    s, reading = best_of(text, ex)
    nulls = []
    for _ in range(SHUFFLES):
        sh = list(text)
        rnd.shuffle(sh)
        nulls.append(best_of("".join(sh), ex)[0])
    plain, ct = planted(len(text), seed)
    ps, pread = best_of(ct, ex)
    acc = sum(a == b for a, b in zip(pread.lower(), plain)) / len(plain)
    cov, pcov = coverage(reading, "fr"), coverage(pread, "fr")
    gates = {"control": acc >= 0.7, "null": s > max(nulls) + 0.15, "reads": cov >= 0.8 * pcov}
    return {"signature": sig, "letters": len(text), "score": round(s, 3), "null_max": round(max(nulls), 3), "control_accuracy": round(acc, 3),
            "coverage": cov, "control_coverage": pcov, **gates, "passed": all(gates.values()), "reading": reading[:300].lower()}


def run(workers: int = 7) -> dict:
    out = {"id": "figaro_pooled", "solved_writers": [], "unsolved_writers": []}
    with ProcessPoolExecutor(workers) as ex:
        for sig, text in sorted(groups(True).items(), key=lambda x: -len(x[1])):
            out["solved_writers"].append(judge(sig, text, ex))
        for sig, text in sorted(groups(False).items(), key=lambda x: -len(x[1])):
            out["unsolved_writers"].append(judge(sig, text, ex))
    out["passed"] = [r["signature"] for r in out["unsolved_writers"] if r["passed"]]
    return out


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for k in ("solved_writers", "unsolved_writers"):
        print(k)
        for r in res[k]:
            print(" ", r["signature"], r["letters"], r["score"], r["null_max"], r["control_accuracy"], r["coverage"], r["control_coverage"], r["passed"], r["reading"][:90])
