"""Score candidate Latin models on Caesar, Book I, against a published English translation."""
import json
import random
import re
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def english_chapters():
    raw = (ROOT / "data/corpora/caesar_en.txt").read_text(errors="ignore")
    book = raw[raw.index("BOOK I"):]
    book = book[: book.index("BOOK II")]
    parts = re.split(r"\n([IVXLC]+)\.--", "\n" + book)
    return {roman(parts[i]): " ".join(parts[i + 1].split()) for i in range(1, len(parts) - 1, 2)}


def roman(s):
    v = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    t = 0
    for i, c in enumerate(s):
        t += -v[c] if i + 1 < len(s) and v[s[i + 1]] > v[c] else v[c]
    return t


def latin_chapters():
    raw = (ROOT / "data/corpora/la.txt").read_text(errors="ignore")
    i = raw.index("GALLIA est omnis")
    j = raw.index("COMMENTARIUS SECUNDUS", i)
    blocks = [" ".join(b.split()) for b in re.split(r"\n[ \t]*\n[ \t]*\n", raw[i:j]) if len(b.split()) > 10]
    return {n + 1: re.sub(r"\[[^\]]*\]", " ", b) for n, b in enumerate(blocks)}


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.;:!?])\s+", t) if len(s.strip()) > 3]


def overlap(hyp, ref):
    w = lambda s: Counter(re.findall(r"[a-z]{3,}", s.lower()))
    h, r = w(hyp), w(ref)
    hit = sum((h & r).values())
    p, q = hit / max(sum(h.values()), 1), hit / max(sum(r.values()), 1)
    return 2 * p * q / (p + q + 1e-9)


def translator(mid, prefix=""):
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(mid)
    m = AutoModelForSeq2SeqLM.from_pretrained(mid).eval()

    def run(chapter):
        out = []
        for i in range(0, len(sentences(chapter)), 8):
            batch = [prefix + s[:400] for s in sentences(chapter)[i:i + 8]]
            x = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=256)
            out += tok.batch_decode(m.generate(**x, max_new_tokens=200, num_beams=2), skip_special_tokens=True)
        return " ".join(out)

    return run


CANDS = [("Helsinki-NLP/opus-mt-mul-en", ""), ("Kankanaghosh/latin_english_translation_model", ""), ("Kankanaghosh/latin_english_translation_model", "translate Latin to English: ")]

if __name__ == "__main__":
    en, la = english_chapters(), latin_chapters()
    names = lambda t: set(re.findall(r"\b[A-Z][a-z]{4,}", t))
    pairs = {c: len(names(en[c]) & names(la[c])) for c in set(en) & set(la)}
    print("shared capitalised names by chapter", sorted(pairs.items())[:14], flush=True)
    common = sorted(set(en) & set(la))[:18]
    print("chapters", len(en), len(la), common[:18], flush=True)
    res = {}
    r = random.Random(1)
    for mid, prefix in CANDS:
        t = time.time()
        run = translator(mid, prefix)
        hyps = {c: run(la[c]) for c in common}
        same = sum(overlap(hyps[c], en[c]) for c in common) / len(common)
        off = sum(overlap(hyps[c], en[r.choice([x for x in common if x != c])]) for c in common) / len(common)
        k = mid + (" +prefix" if prefix else "")
        res[k] = {"same_chapter": round(same, 3), "wrong_chapter": round(off, 3), "seconds": round(time.time() - t), "sample_latin": la[common[0]][:220], "sample_output": hyps[common[0]][:320], "sample_ref": en[common[0]][:320]}
        print(k, res[k]["same_chapter"], res[k]["wrong_chapter"], res[k]["seconds"], flush=True); print("  ", res[k]["sample_output"][:280], flush=True)
    (ROOT / "data/results/latin_eval.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
