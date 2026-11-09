"""Measured lessons on recovering text: OCR against hand truth, error spread, key-aware repair."""
import json
import random
import re
from difflib import SequenceMatcher

from ..languages import ROOT, corpus_text, score
from ..text import A, letters
from . import figaro_ocr as O
from .figaro_keys import NOW, shift, vig

HAND = ROOT / "data/mysteries/figaro_hand_readings.json"
IMAGES = ROOT / "data/sources/figaro/images"
FIGARO = ROOT / "data/sources/figaro"
VARIANTS = ["base", "big", "otsu", "adaptive", "denoise"]
ENGINES = ["tesseract", "tesseract + whitelist", "rapidocr"]
# Letters that 19th-century type and OCR confuse, from the misreads seen in the scans.
CONFUSE = {"F": "HST", "H": "BFKN", "I": "LJT", "L": "IT", "C": "EO", "E": "CO", "S": "F", "N": "UH", "U": "NV", "B": "H", "T": "FLI", "O": "CE", "R": "N", "V": "U", "K": "H", "J": "I"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def recovered(truth: str, read: str) -> float:
    """Share of the true characters found, in order, in what the engine read."""
    t, r = norm(truth), norm(read)
    if not t:
        return 0.0
    return sum(b.size for b in SequenceMatcher(None, t, r, autojunk=False).get_matching_blocks()) / len(t)


def read_with(img, engine: str) -> str:
    if engine == "rapidocr":
        return " ".join(O.rapid_lines(img))
    return " ".join(O.tesseract_lines(img, whitelist="whitelist" in engine))


def hand_truth() -> dict:
    return json.loads(HAND.read_text())


def ocr_benchmark() -> dict:
    """Every cleanup and engine, scored on ads whose ciphertext was read by eye."""
    truth, table, samples = hand_truth(), [], {}
    for v in VARIANTS:
        for e in ENGINES:
            scores = {}
            for name, rec in truth.items():
                text = read_with(O.variant(str(IMAGES / name), v), e)
                scores[name] = recovered(rec["ciphertext"], text)
                if v in ("base", "otsu"):
                    samples.setdefault(name, []).append({"variant": v, "engine": e, "text": text.strip(), "recovered": round(scores[name], 3)})
            table.append({"variant": v, "engine": e, "mean": round(sum(scores.values()) / len(scores), 3), "worst": round(min(scores.values()), 3)})
    table.sort(key=lambda x: -x["mean"])
    return {"ads": len(truth), "table": table, "samples": samples}


def french(n: int, length: int, seed: int) -> list[str]:
    text, rnd = letters(corpus_text("fr")), random.Random(seed)
    return [text[i:i + length] for i in (rnd.randrange(len(text) - length) for _ in range(n))]


def _damage(t: str, rate: float, kind: str, rnd: random.Random) -> str:
    out = []
    for c in t:
        if rnd.random() < rate:
            if kind == "deletion":
                continue
            c = rnd.choice(CONFUSE.get(c, A))
        out.append(c)
    return "".join(out)


def _vig_enc(p: str, key: str = "BCDEF", alpha: str = A) -> str:
    ks = [alpha.index(c) for c in key]
    return "".join(alpha[(alpha.index(c) + ks[i % len(ks)]) % len(alpha)] for i, c in enumerate(p))


def error_spread(n: int = 60, length: int = 300) -> dict:
    """How much plaintext survives misread or dropped ciphertext letters, with the key known."""
    rates, rnd, series = [0, 0.01, 0.02, 0.05, 0.1, 0.2], random.Random(11), {}
    enc = {"Caesar": lambda p: shift(p, -3, A), "Vigenere": _vig_enc}
    dec = {"Caesar": lambda c: shift(c, 3, A), "Vigenere": lambda c: vig(c, "BCDEF", A)}
    plains = french(n, length, 5)
    for system, kind in (("Caesar", "deletion"), ("Vigenere", "misread"), ("Vigenere", "deletion")):
        series[f"{system}, {kind}"] = [round(sum(recovered(p, dec[system](_damage(enc[system](p), r, kind, rnd))) for p in plains) / n, 3) for r in rates]
    return {"rates": rates, "series": series, "trials": n, "length": length}


def total(text: str, lang: str = "fr") -> float:
    t = letters(text)
    return score(t, lang) * len(t)


def repair(cipher: str, decrypt, margin: float, max_edits: int = 4) -> tuple[str, list]:
    """Greedily change a letter to one it is often confused with when the decrypt reads clearly better."""
    cur, edits = cipher, []
    for _ in range(max_edits):
        base, best = total(decrypt(cur)), None
        for i, c in enumerate(cur):
            for alt in CONFUSE.get(c, ""):
                trial = cur[:i] + alt + cur[i + 1:]
                gain = total(decrypt(trial)) - base
                if gain > margin and (best is None or gain > best[0]):
                    best = (gain, i, alt, trial)
        if best is None:
            break
        edits.append({"position": best[1], "from": cur[best[1]], "to": best[2], "gain": round(best[0], 1)})
        cur = best[3]
    return cur, edits


def _inject(t: str, k: int, rnd: random.Random) -> str:
    s, spots = list(t), [i for i, c in enumerate(t) if c in CONFUSE]
    for i in rnd.sample(spots, k):
        s[i] = rnd.choice(CONFUSE[s[i]])
    return "".join(s)


def _dec_cd(c: str) -> str:
    return vig(c, "CD", NOW)


def _enc_cd(p: str) -> str:
    return _vig_enc(p.replace("W", "V"), "CD", NOW)


def _best_gain(c: str) -> float:
    base = total(_dec_cd(c))
    return max((total(_dec_cd(c[:i] + alt + c[i + 1:])) - base for i, ch in enumerate(c) for alt in CONFUSE.get(ch, "")), default=0.0)


def calibrate(n: int = 120, length: int = 40) -> float:
    """The acceptance margin: the 95th percentile of the best false gain on clean text."""
    gains = sorted(_best_gain(_enc_cd(p)) for p in french(n, length, 21))
    return gains[int(len(gains) * 0.95)]


def repair_control(n: int = 120, length: int = 40) -> dict:
    """Fix the margin on clean fragments, then test on new damaged and new clean ones."""
    margin, rnd, fixed, before, after = calibrate(n, length), random.Random(3), 0, 0, 0
    for p in french(n, length, 22):
        truth = _enc_cd(p)
        bad = _inject(truth, 2, rnd)
        out, _ = repair(bad, _dec_cd, margin)
        fixed += out == truth
        before += sum(a != b for a, b in zip(bad, truth))
        after += sum(a != b for a, b in zip(out, truth))
    false_edits = sum(bool(repair(_enc_cd(p), _dec_cd, margin)[1]) for p in french(n, length, 23))
    return {"margin": round(margin, 2), "fragments": n, "length": length, "fully_repaired": fixed, "wrong_before": before, "wrong_after": after, "clean_changed": false_edits}


def repair_real() -> dict:
    """The 1894 ad as the OCR gave it, repaired under the key that the decrypt suggests."""
    bad = "GVRFTHFIPHTDYHEXQLQYUHTDKXTHUSGLPHG"
    out, edits = repair(bad, _dec_cd, calibrate(60, 40))
    return {"ocr": bad, "ocr_plain": _dec_cd(bad), "repaired": out, "plain": _dec_cd(out), "edits": edits}


def digit_audit() -> dict:
    """Count ads with letter-digit tokens: the OCR saw them, and the word filter threw them away."""
    otsu, raw = (json.loads((FIGARO / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    hit = []
    for name in otsu:
        lines = [l for src in (otsu, raw) for eng in src.get(name, {}).values() for l in eng]
        mixed = max((sum(1 for t in l.split() if len(t) >= 3 and re.search(r"[a-z]", t) and re.search(r"\d", t)) for l in lines), default=0)
        if mixed >= 3:
            hit.append(name)
    return {"ads_read": len(otsu), "letter_digit_ads": len(hit), "examples": sorted(hit)[:12]}
