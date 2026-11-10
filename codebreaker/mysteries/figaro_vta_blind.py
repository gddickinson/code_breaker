"""Round 38: solve the V. T. A. words blind, with none of the readings, and compare with the key read from context.

All enciphered words are pooled and solved as one homophonic substitution by the project's quadgram annealer in English
(most of the words are English; the French ones act as noise). Seven seeds run; the run with the best quadgram score is
taken, chosen without looking at the readings. The measure is agreement with the context key, per symbol occurrence.
Controls: a planted English and French correspondence of the same size and homophone shape (should agree with its true
key), and the real symbols shuffled (should score clearly worse than the real text)."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor

from ..attacks.classical import solve_symbols
from ..languages import ROOT, corpus_text, score
from . import figaro_vta as V

RESULT = ROOT / "data/results/figaro_vta_blind.json"
LETTERS = "abcdefghiklmnopqrstuwxyz"  # the writer's alphabet: i/j and u/v merged
SEEDS, ITERS, WEIGHT = 7, 8000000, 1.0


def pooled_words() -> list[str]:
    return [w.replace("'", "") for i, a in V.ads().items() if i not in V.SKIP for w in V.scored_words(a)]


def agreement(found: dict, truth: dict, words: list[str]) -> float:
    """Share of symbol occurrences that both keys decode to the same letter."""
    occ = [c for w in words for c in w if c in truth]
    return sum(found.get(c) == truth[c].translate(V.MERGE) for c in occ) / max(len(occ), 1)


def _job(a):
    words, seed = a
    r = solve_symbols([c for w in words for c in w], "en", homophonic=True, seed=seed, iters=ITERS, restarts=4, w=WEIGHT)
    key = {s: l.lower().translate(V.MERGE) for s, l in r["key"].items()}
    return {"seed": seed, "score": round(score(r["plaintext"], "en"), 4), "key": key}


def blind(words: list[str], workers: int = 7) -> list[dict]:
    with ProcessPoolExecutor(workers) as ex:
        return sorted(ex.map(_job, [(words, s) for s in range(SEEDS)]), key=lambda r: -r["score"])


def refine(key: dict, words: list[str], rounds: int = 6) -> dict:
    """Blind second stage: change one symbol at a time when more decoded letters fall in dictionary words (English or
    French, run-together words may split). No readings are used."""
    saved, key = V.SCORING, dict(key)
    V.SCORING = "segmented"
    try:
        total = lambda k: sum(V.covered("".join(k.get(c, "?") for c in w)) for w in words)
        cur = total(key)
        for _ in range(rounds):
            changed = False
            for s in sorted(key, key=lambda s: -sum(w.count(s) for w in words)):
                best_l, best_v = key[s], cur
                for letter in LETTERS:
                    if letter != key[s]:
                        old = key[s]
                        key[s] = letter
                        v = total(key)
                        key[s] = old
                        if v > best_v:
                            best_l, best_v = letter, v
                if best_l != key[s]:
                    key[s], cur, changed = best_l, best_v, True
            if not changed:
                break
    finally:
        V.SCORING = saved
    return key


def planted(seed: int = 3) -> tuple[list[str], dict]:
    """Running English and French text, word lengths as found, homophone counts as in the context key."""
    rnd, real = random.Random(seed), V.homophones(V.full_key())
    words = pooled_words()
    pool = list("abcdefghijklmnopqrstuvwxyz0123456789+")
    rnd.shuffle(pool)
    enc, truth, i = {}, {}, 0
    for letter in LETTERS:
        k = max(1, len(real.get(letter, [])))
        enc[letter] = pool[i:i + k] if i + k <= len(pool) else [pool[(i + j) % len(pool)] for j in range(k)]
        i += k
        for s in enc[letter]:
            truth.setdefault(s, letter)
    en = re.findall(r"[a-z]+", corpus_text("en").lower())
    fr = re.findall(r"[a-z]+", corpus_text("fr").lower())
    start_en, start_fr = rnd.randrange(len(en) - 400), rnd.randrange(len(fr) - 100)
    plain = en[start_en:start_en + len(words) - len(words) // 4] + fr[start_fr:start_fr + len(words) // 4]
    cipher = ["".join(rnd.choice(enc[c]) for c in w.translate(V.MERGE) if c in enc) for w in plain]
    return [c for c in cipher if c], truth


def shuffled(words: list[str], seed: int = 9) -> list[str]:
    rnd, flat = random.Random(seed), list("".join(words))
    rnd.shuffle(flat)
    out, pos = [], 0
    for w in words:
        out.append("".join(flat[pos:pos + len(w)]))
        pos += len(w)
    return out


def disagreements(found: dict, truth: dict, words: list[str]) -> list[dict]:
    uses = {}
    for w in words:
        for c in w:
            uses[c] = uses.get(c, 0) + 1
    return sorted(({"symbol": s, "context": truth[s], "blind": found.get(s), "uses": uses.get(s, 0)} for s in truth if found.get(s) != truth[s].translate(V.MERGE) and uses.get(s)), key=lambda d: -d["uses"])


def run() -> dict:
    words, ctx = pooled_words(), V.full_key()
    runs = blind(words)
    for r in runs:
        r["agreement"] = round(agreement(r["key"], ctx, words), 3)
    best = runs[0]
    refined = refine(best["key"], words)
    pw, truth = planted()
    pruns = blind(pw)
    sw = shuffled(words)
    sruns = blind(sw)
    sref = refine(sruns[0]["key"], sw)
    return {"id": "figaro_vta_blind", "words": len(words), "letters": sum(map(len, words)),
            "runs": [{k: v for k, v in r.items() if k != "key"} for r in runs], "best": best,
            "best_reading": " ".join("".join(best["key"][c] for c in w) for w in words),
            "context_reading": " ".join(V.decode(w, ctx) for w in words),
            "refined": {"agreement": round(agreement(refined, ctx, words), 3), "word_share": round(share(refined, words), 3), "reading": " ".join("".join(refined[c] for c in w) for w in words)},
            "disagreements": disagreements(refined, ctx, words),
            "context_word_share": round(share(ctx, words), 3),
            "planted": {"best_score": pruns[0]["score"], "agreement_with_true_key": round(agreement(pruns[0]["key"], truth, pw), 3),
                        "refined_agreement": round(agreement(refine(pruns[0]["key"], pw), truth, pw), 3)},
            "shuffled_null": {"best_score": sruns[0]["score"], "agreement_with_context_key": round(agreement(sruns[0]["key"], ctx, words), 3), "refined_word_share": round(share(sref, sw), 3)}}


def share(key: dict, words: list[str]) -> float:
    saved = V.SCORING
    V.SCORING = "segmented"
    try:
        return sum(V.covered("".join(key.get(c, "?").translate(V.MERGE) for c in w)) for w in words) / sum(map(len, words))
    finally:
        V.SCORING = saved


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, indent=1))
    for r in res["runs"]:
        print(r)
    print("planted", res["planted"], "shuffled", res["shuffled_null"])
    print("refined", {k: v for k, v in res["refined"].items() if k != "reading"}, "context key word share", res["context_word_share"])
    print(res["disagreements"][:12])
    print(res["refined"]["reading"][:500])
