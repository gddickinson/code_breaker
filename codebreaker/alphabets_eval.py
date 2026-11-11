"""Controls for the other-alphabet ciphers (Round 86), saved to data/results/alphabets.json.

Positive controls: held-out passages (the last tenth of each corpus, never used for the model) of 150 and 300
letters, encrypted with random keys under Caesar, Vigenere (period 3-7) and simple substitution, solved: share of
letters right. Null: random letters of the alphabet, 300 long, through the full three-gate crack in that language:
how often a 'readable' verdict comes out (it should never)."""
import json

import numpy as np

from . import alphabets as AB
from .attacks import alphabet as AT
from .languages import ROOT

RESULT = ROOT / "data/results/alphabets.json"


def run(trials: int = 8, nulls: int = 3, seed: int = 86) -> dict:
    out = {}
    for lang in AB.available():
        m = AB.model(lang)
        row = {"name": AB.LANGS[lang][0], "alphabet": m["alpha"], "letters": len(m["alpha"]),
               "held_out_letters": len(AB.to_ints(AB.held_out(lang), lang))}
        for kind in AT.KINDS:
            for n in (150, 300):
                row[f"{kind}_{n}"] = round(AT.positive_control(n, lang, kind, trials=trials, seed=seed)["mean"], 3)
        rnd = np.random.default_rng(seed)
        readable = 0
        for _ in range(nulls):
            noise = AB.to_text(rnd.integers(0, len(m["alpha"]), 300), lang)
            readable += AT.crack(noise, [lang])["verdict"].startswith("Readable")
        row["random_letters_readable"] = f"{readable} of {nulls}"
        out[lang] = row
    return {"id": "alphabets", "languages": out}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1, ensure_ascii=False))
    for k, v in r["languages"].items():
        print(k, {x: y for x, y in v.items() if x != "alphabet"})
