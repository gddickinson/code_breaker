"""Round 36b: the V. T. A. ads of 1877, pooled as one correspondence under one key.

The ads are plain English with a few enciphered words (and some French ones). The enciphered words use letters, digits
and a cross; several symbols stand for the same letter. Readings ('cribs') come from context, ad by ad. The test that
matters is held out: for each ad, a key voted from the cribs of the other ads alone must turn that ad's enciphered
words into dictionary words far more often than the same key with its letters shuffled among the symbols."""
import json
import random
from collections import Counter, defaultdict
from functools import lru_cache

from ..languages import ROOT, model
from .figaro_keys import OUT

TRANSCRIPTION = OUT / "vta_transcription.json"
RESULT = ROOT / "data/results/figaro_vta.json"
SKIP = {"1877_18770901-VTA.jpg"}  # an address: proper names, no dictionary test

# (ad date, cipher word, reading). Only words whose reading is forced by the plain text around them.
CRIBS = [
    ("0828", "vx5r", "long"), ("0828", "2t+8", "time"), ("0828", "t", "i"), ("0828", "sme85'2", "havent"), ("0828", "q802", "felt"),
    ("0828", "hxdl", "your"), ("0828", "vty4", "lips"), ("0828", "x5", "on"), ("0828", "+h", "my"), ("0828", "4dos", "such"), ("0828", "m", "a"),
    ("0914", "p8ml", "dear"), ("0914", "y82t17", "petite"), ("0914", "osx48", "chose"), ("0914", "n8md2h", "beauty"),
    ("0918", "nlx2s8c4", "brothers"), ("0918", "+mlctmr8", "marriage"),
    ("0927", "hxdl", "your"), ("0927", "et4u2", "visit"), ("0927", "vxe8", "love"), ("0927", "2sm5", "than"),
    ("1003", "flt2u5r", "writing"), ("1003", "2x", "to"), ("1003", "fx52", "wont"), ("1003", "t2", "it"), ("1003", "nd2", "but"), ("1003", "m+", "am"),
    ("1003", "pht5r", "dying"), ("1003", "ft2s", "with"), ("1003", "t8mvxd4h", "jealousy"), ("1003", "fsh", "why"), ("1003", "st+", "him"),
    ("1003", "5x2", "not"), ("1003", "+8", "me"), ("1003", "vxe8", "love"), ("1003", "hxd", "you"), ("1003", "4x", "so"), ("1003", "f8vg", "well"),
    ("1003", "m5p", "and"), ("1003", "2ldvh", "truly"), ("1003", "xf5", "own"), ("1003", "pmlvt5r", "darling"), ("1003", "oxdvp", "could"),
    ("1003", "flt28", "write"), ("1003", "28vg", "tell"), ("1003", "t4", "is"), ("1003", "t5", "in"), ("1003", "s8ml2", "heart"),
    ("1004", "yd2", "put"), ("1004", "t52x", "into"), ("1004", "48mlos", "search"), ("1004", "f8vg", "well"), ("1004", "+m", "ma"),
    ("1004", "os8l7", "chere"), ("1004", "y82t17", "petite"), ("1004", "98", "de"), ("1004", "82", "et"),
    ("1009", "fst28", "white"), ("1009", "qvxf8l4", "flowers"),
    ("1012", "y82t17", "petite"), ("1012", "osx48", "chose"), ("1012", "hxd", "you"), ("1012", "4x", "so"),
    ("1017", "2d", "tu"), ("1017", "ym4", "pas"), ("1017", "osx48", "chose"), ("1017", "5xde8vg74", "nouvelles"),
    ("1020", "hxdl", "your"), ("1020", "+x2s8l4", "mothers"), ("1020", "m2", "at"),
    ("1023", "m2", "at"), ("1023", "mnxd2", "about"),
    ("1031", "nvd8", "blue"), ("1031", "pl843", "dress"), ("1031", "2d84pmh", "tuesday"),
    ("1106", "t5", "in"), ("1106", "ymlo8v", "parcel"), ("1106", "hxd", "you"), ("1106", "y82t17", "petite"), ("1106", "osx48", "chose"),
    ("1109", "+xl5t6r", "morning"),
    ("1111", "+x5pmh", "monday"), ("1111", "qxl", "for"), ("1111", "hxdl", "your"), ("1111", "vd5os", "lunch"), ("1111", "+h", "my"),
    ("1111", "pmlvt5r", "darling"), ("1111", "y82t17", "petite"), ("1111", "osx48", "chose"), ("1111", "t", "i"), ("1111", "vxe8", "love"),
    ("1111", "hxd", "you"), ("1111", "e8lh", "very"), ("1111", "+dos", "much"),
    ("1207", "pmlvt57", "darling"), ("1207", "m5p", "and"), ("1207", "ml7", "are"),
    ("1220", "ad8", "que"), ("1220", "5x2l8", "notre"), ("1220", "m+xdl", "amour"), ("1220", "58", "ne"), ("1220", "28", "te"), ("1220", "l85p7", "rende"),
    ("1222", "ft2s", "with"), ("1222", "m5p", "and"), ("1222", "fm52", "want"), ("1222", "xq", "of"), ("1222", "487t5r", "seeing"),
]
MERGE = str.maketrans("jv", "iu")  # the writer's alphabet does not separate i/j or u/v


def ads() -> dict:
    return json.loads(TRANSCRIPTION.read_text())["ads"]


def words_of(cipher: str) -> list[str]:
    return [w for w in cipher.replace("/", " ").split() if w]


def date(image: str) -> str:
    return image.split("_")[1][4:8]


def key_from(cribs) -> dict:
    """Symbol -> letter by majority over the cribs given. Apostrophes are not symbols."""
    votes = defaultdict(Counter)
    for _, c, p in cribs:
        c = c.replace("'", "")
        if len(c) == len(p):
            for s, l in zip(c, p):
                votes[s][l.translate(MERGE)] += 1
    return {s: v.most_common(1)[0][0] for s, v in votes.items()}


def decode(word: str, key: dict) -> str:
    return "".join(key.get(s, "?") for s in word.replace("'", ""))


@lru_cache(maxsize=1)
def vocabulary() -> frozenset:
    return frozenset(str(w).lower().translate(MERGE) for lang in ("en", "fr") for w in model(lang)["words"] if len(w) >= 2) | {"a", "i"}


def word_share(cwords: list[str], key: dict) -> float:
    """Share of enciphered letters that decode inside dictionary words (English or French)."""
    v, n = vocabulary(), sum(len(w.replace("'", "")) for w in cwords)
    return sum(len(d) for d in (decode(w, key) for w in cwords) if d in v) / n if n else 0.0


def shuffled_key(key: dict, rnd: random.Random) -> dict:
    vals = list(key.values())
    rnd.shuffle(vals)
    return dict(zip(key, vals))


def held_out(trials: int = 2000, seed: int = 36) -> dict:
    rnd, rows = random.Random(seed), []
    for image, ad in ads().items():
        if image in SKIP:
            continue
        others = [c for c in CRIBS if c[0] != date(image)]
        key, cw = key_from(others), words_of(ad["cipher"])
        real = word_share(cw, key)
        null = [word_share(cw, shuffled_key(key, rnd)) for _ in range(200)]
        own = [c for c in CRIBS if c[0] == date(image)]
        agree = sum(a == b.translate(MERGE) for _, c, p in own for a, b in zip(decode(c, key), p) if len(c.replace("'", "")) == len(p))
        total = sum(len(p) for _, c, p in own if len(c.replace("'", "")) == len(p))
        rows.append({"image": image, "words": len(cw), "share": round(real, 3), "null_mean": round(sum(null) / len(null), 3), "null_max": round(max(null), 3),
                     "crib_letters_right": agree, "crib_letters": total, "reading": " ".join(decode(w, key) for w in cw)})
    # Pooled null: every ad's key shuffled independently, many times.
    per_ad = {r["image"]: (words_of(ads()[r["image"]]["cipher"]), key_from([c for c in CRIBS if c[0] != date(r["image"])])) for r in rows}
    letters = {i: sum(len(w.replace("'", "")) for w in cw) for i, (cw, _) in per_ad.items()}
    real_total = sum(r["share"] * letters[r["image"]] for r in rows) / sum(letters.values())
    nulls = []
    for _ in range(trials):
        nulls.append(sum(word_share(cw, shuffled_key(k, rnd)) * letters[i] for i, (cw, k) in per_ad.items()) / sum(letters.values()))
    return {"ads": len(rows), "pooled_share": round(real_total, 3), "null_mean": round(sum(nulls) / len(nulls), 3), "null_max": round(max(nulls), 3),
            "p_value": (sum(x >= real_total for x in nulls) + 1) / (trials + 1), "crib_letters_right": sum(r["crib_letters_right"] for r in rows),
            "crib_letters": sum(r["crib_letters"] for r in rows), "rows": rows}


def scrambled_control(seed: int = 7) -> dict:
    """Negative control: every enciphered word replaced by random symbols of the same length, cribs kept attached.
    If attaching readings to strings could by itself make held-out ads decode, this would pass too."""
    global CRIBS
    rnd = random.Random(seed)
    alphabet = sorted({s for a in ads().values() for w in words_of(a["cipher"]) for s in w.replace("'", "")})
    sub = {}
    def scramble(w):
        return sub.setdefault(w, "".join(rnd.choice(alphabet) for _ in w.replace("'", "")))
    saved_ads, saved_cribs = ads, CRIBS
    fake = {i: {**a, "cipher": " ".join(scramble(w) for w in words_of(a["cipher"]))} for i, a in saved_ads().items()}
    try:
        globals()["ads"] = lambda: fake
        CRIBS = [(d, scramble(c), p) for d, c, p in saved_cribs]
        h = held_out(trials=200)
    finally:
        globals()["ads"], CRIBS = saved_ads, saved_cribs
    return {k: v for k, v in h.items() if k != "rows"}


def positive_control(seed: int = 11) -> dict:
    """A planted correspondence of the same shape: real French and English words, a random key with the same homophone
    counts, and the same share of words used as cribs. The held-out test should read it."""
    global CRIBS
    from .figaro_transposition import phrases

    rnd, real = random.Random(seed), homophones(full_key())
    symbols = sorted({s for a in ads().values() for w in words_of(a["cipher"]) for s in w.replace("'", "")})
    rnd.shuffle(symbols)
    enc, i = {}, 0
    for letter, syms in real.items():
        enc[letter] = symbols[i:i + len(syms)]
        i += len(syms)
    for letter in "abcdefghiklmnopqrstuwxyz":
        if letter not in enc:
            enc[letter] = [symbols[i % len(symbols)]]
            i += 1
    encrypt = lambda w: "".join(rnd.choice(enc[c]) for c in w.translate(MERGE))
    fake, cribs = {}, []
    for j, (image, a) in enumerate(ads().items()):
        if image in SKIP:
            continue
        n = len(words_of(a["cipher"]))
        plain = phrases(1, 6 * n, 500 + j)[0].split()[:n]
        cw = [encrypt(w) for w in plain]
        fake[image] = {"cipher": " ".join(cw)}
        share = sum(c[0] == date(image) for c in CRIBS) / max(n, 1)
        cribs += [(date(image), c, p) for c, p in zip(cw, plain) if rnd.random() < min(share, 1.0)]
    saved_ads, saved_cribs = ads, CRIBS
    try:
        globals()["ads"] = lambda: fake
        CRIBS = cribs
        h = held_out(trials=200)
    finally:
        globals()["ads"], CRIBS = saved_ads, saved_cribs
    return {k: v for k, v in h.items() if k != "rows"}


def gates(h: dict, pc: dict, null_sd: float, tests: int = 1) -> dict:
    """The project's three gates (validation.verdict), applied to the word-level held-out test."""
    z = (h["pooled_share"] - h["null_mean"]) / max(null_sd, 1e-9)
    bar = 4.0 + __import__("math").log10(max(tests, 1))
    g = {"control": pc["crib_letters_right"] / max(pc["crib_letters"], 1) >= 0.7,
         "null": z >= bar, "reads": h["pooled_share"] >= 0.8 * pc["pooled_share"]}
    return {"z": round(z, 1), "bar": bar, **g, "passed": all(g.values())}


def full_key() -> dict:
    return key_from(CRIBS)


def homophones(key: dict) -> dict:
    out = defaultdict(list)
    for s, l in sorted(key.items()):
        out[l].append(s)
    return dict(sorted(out.items()))


def run() -> dict:
    key = full_key()
    h = held_out()
    readings = {i: " ".join(decode(w, key) for w in words_of(a["cipher"])) for i, a in ads().items()}
    pc = positive_control()
    rnd, cw = random.Random(1), {i: (words_of(a["cipher"]), key_from([c for c in CRIBS if c[0] != date(i)])) for i, a in ads().items() if i not in SKIP}
    letters = {i: sum(len(w.replace("'", "")) for w in ws) for i, (ws, _) in cw.items()}
    nulls = [sum(word_share(ws, shuffled_key(k, rnd)) * letters[i] for i, (ws, k) in cw.items()) / sum(letters.values()) for _ in range(500)]
    mean = sum(nulls) / len(nulls)
    sd = (sum((x - mean) ** 2 for x in nulls) / len(nulls)) ** 0.5
    return {"id": "figaro_vta", "key": key, "homophones": homophones(key), "cribs": len(CRIBS), "held_out": h, "positive_control": pc,
            "scrambled_control": scrambled_control(), "gates": gates(h, pc, sd), "readings": readings}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, indent=1))
    h = out["held_out"]
    print({k: v for k, v in h.items() if k != "rows"})
    print("scrambled control", out["scrambled_control"])
    print("positive control", out["positive_control"])
    print("gates", out["gates"])
    print(out["homophones"])
    for i, r in out["readings"].items():
        print("FULL", i[5:13], r)
    for r in h["rows"]:
        print(r["image"][5:13], r["share"], r["null_mean"], r["null_max"], f"{r['crib_letters_right']}/{r['crib_letters']}", r["reading"][:110])
