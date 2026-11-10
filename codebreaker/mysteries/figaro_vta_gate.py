"""Round 37: a fairer third gate for the V. T. A. key, and whether the result depends on uncertain glyphs.

Scoring 'segmented' lets a decoded word split into dictionary words of 3+ letters (the writer runs words together:
'ietaime', 'bienaimee'); the null, the scrambled control and the planted control are scored the same way. Then every
glyph that the scans leave uncertain (1/l, o/0, t/f, f/h, 9/8, 7/?) is read the other way, singly and all together."""
import json

from ..languages import ROOT
from . import figaro_vta as V

RESULT = ROOT / "data/results/figaro_vta_gate.json"

# (ad, word as transcribed, the other reading of its uncertain glyph)
FLIPS = [
    ("1877_18770828-VTAJ.jpg", "4t508", "4t5o8"), ("1877_18770927-VTA.jpg", "4f508", "4t508"), ("1877_18770927-VTA.jpg", "n8217l", "n82171"),
    ("1877_18770927-VTA.jpg", "8e7l", "8e71"), ("1877_18770927-VTA.jpg", "yxd", "hxd"), ("1877_18771003-VTA.jpg", "l8mp", "18mp"),
    ("1877_18771003-VTA.jpg", "2s8l7", "2s817"), ("1877_18771004-VTA.jpg", "v8217l", "v82171"), ("1877_18771004-VTA.jpg", "os8l7", "os817"),
    ("1877_18771017-VTA.jpg", "p8t7d50l", "p8t7d5ol"), ("1877_18771020-VTA.jpg", "v8217l", "v82171"), ("1877_18771023-VTA.jpg", "2f8vf7", "2f8ve7"),
    ("1877_18771109-VTA.jpg", "qltpmf", "qltpmh"), ("1877_18771220-VTA.jpg", "+mvs8dl7e49", "+mvs8dl7e48"),
]


def with_flips(flips):
    """Transcription and cribs with the given words replaced, for one evaluation."""
    original = V.ads()
    fake = {i: dict(a) for i, a in original.items()}
    cribs = list(V.CRIBS)
    for image, old, new in flips:
        fake[image]["cipher"] = " ".join(new if w == old else w for w in V.words_of(fake[image]["cipher"]))
        cribs = [(d, new if (c == old and d == V.date(image)) else c, p) for d, c, p in cribs]
    return fake, cribs


def evaluate(fake=None, cribs=None, scoring="exact", trials=500) -> dict:
    saved = (V.ads, V.CRIBS, V.SCORING)
    try:
        if fake is not None:
            V.ads = lambda: fake
            V.CRIBS = cribs
        V.SCORING = scoring
        h = V.held_out(trials=trials)
        return {k: v for k, v in h.items() if k != "rows"} | {"rows": [{"image": r["image"], "share": r["share"]} for r in h["rows"]]}
    finally:
        V.ads, V.CRIBS, V.SCORING = saved


def gate_under(scoring: str) -> dict:
    saved = V.SCORING
    try:
        V.SCORING = scoring
        h, pc, sc = V.held_out(trials=1000), V.positive_control(), V.scrambled_control()
        import random

        rnd = random.Random(1)
        cw = {i: (V.scored_words(a), V.key_from([c for c in V.CRIBS if c[0] != V.date(i)])) for i, a in V.ads().items() if i not in V.SKIP}
        letters = {i: sum(len(w.replace("'", "")) for w in ws) for i, (ws, _) in cw.items()}
        nulls = [sum(V.word_share(ws, V.shuffled_key(k, rnd)) * letters[i] for i, (ws, k) in cw.items()) / sum(letters.values()) for _ in range(500)]
        m = sum(nulls) / len(nulls)
        sd = (sum((x - m) ** 2 for x in nulls) / len(nulls)) ** 0.5
        strip = lambda d: {k: v for k, v in d.items() if k != "rows"}
        return {"held_out": strip(h), "positive_control": pc, "scrambled_control": sc, "gates": V.gates(h, pc, sd), "rows": [{"image": r["image"], "share": r["share"]} for r in h["rows"]]}
    finally:
        V.SCORING = saved


def run() -> dict:
    out = {"id": "figaro_vta_gate", "exact": gate_under("exact"), "segmented": gate_under("segmented")}
    base = evaluate(scoring="segmented")["pooled_share"]
    singles = []
    for f in FLIPS:
        e = evaluate(*with_flips([f]), scoring="segmented")
        singles.append({"ad": f[0], "word": f[1], "other": f[2], "pooled_share": e["pooled_share"], "change": round(e["pooled_share"] - base, 3)})
    allf = evaluate(*with_flips(FLIPS), scoring="segmented")
    out["glyphs"] = {"base": base, "singles": singles, "all_flipped": {k: v for k, v in allf.items() if k != "rows"}}
    return out


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, indent=1))
    for s in ("exact", "segmented"):
        o = out[s]
        print(s, "held", o["held_out"]["pooled_share"], "null", o["held_out"]["null_mean"], o["held_out"]["null_max"], "planted", o["positive_control"]["pooled_share"], "scrambled", o["scrambled_control"]["pooled_share"], o["gates"])
    g = out["glyphs"]
    print("glyph base", g["base"], "all flipped", g["all_flipped"]["pooled_share"], g["all_flipped"]["crib_letters_right"], "/", g["all_flipped"]["crib_letters"])
    for x in g["singles"]:
        print(" ", x["ad"][5:13], x["word"], "->", x["other"], x["change"])
