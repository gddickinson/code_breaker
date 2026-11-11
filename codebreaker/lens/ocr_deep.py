"""The Lens's two readers for Latin-script text (user's suggestion, Round 78b): a fast one for the live view and a
thorough one for captured photos.

live_words: RapidOCR alone (PaddleOCR detection and recognition), about 0.8 s a frame; it finds every line, which
    is what the overlay and tracking need; words that it runs together are acceptable on a moving view.
photo_words: for every line RapidOCR finds, several readings are compared: RapidOCR's own, Tesseract on the stacked
    line crops at two heights, and the words of three full-page Tesseract passes that fall inside the line. The kept
    reading scores best on half dictionary words of the text's language (the app's six word lists; English if the
    language has none) and half agreement with RapidOCR's letters, then confidence. Scored on the user's label."""
import re

import cv2
import numpy as np

from ..languages import LANGS, model
from . import ocr


def _lines(gray: np.ndarray) -> list[tuple]:
    eng = ocr.rapid()
    res, _ = eng(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
    out = []
    for box, txt, conf in res or []:
        b = np.array(box)
        x0, y0 = b.min(0).astype(int)
        x1, y1 = b.max(0).astype(int)
        out.append(((int(x0), int(y0), int(x1 - x0), int(y1 - y0)), txt, float(conf)))
    return out


def _spread(text: str, box, conf: float, line: str) -> list[dict]:
    """A line reading as words, the line box divided by letter count."""
    toks = text.split()
    n, x = max(1, sum(map(len, toks)) + len(toks) - 1), box[0]
    out = []
    for t in toks:
        w = box[2] * len(t) / n
        out.append({"text": t, "box": [round(x), box[1], round(w), box[3]], "conf": round(conf, 1), "line": line})
        x += w + box[2] / n
    return out


def live_words(gray: np.ndarray) -> list[dict]:
    return [w for i, (box, txt, conf) in enumerate(_lines(gray)) for w in _spread(txt, box, conf * 100, str(i))]


def _stacked(gray: np.ndarray, lines: list[tuple], height: int) -> list[list[dict]]:
    """Tesseract once over all line crops stacked at one height; words per line, boxes in picture pixels."""
    gap, crops, spans = height // 2, [], []
    for (x, y, w, h), _, _ in lines:
        pad = max(2, h // 5)
        x0, y0 = max(0, x - pad), max(0, y - pad)
        c = gray[y0:y + h + pad, x0:x + w + pad]
        sc = height / max(1, c.shape[0])
        crops.append(cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 8)).apply(cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)))
        spans.append((x0, sc, (x, y, w, h)))
    canvas = np.full(((height + gap) * len(crops) + gap, max(c.shape[1] for c in crops) + 40), 255, np.uint8)
    for i, c in enumerate(crops):
        canvas[gap + i * (height + gap):gap + i * (height + gap) + c.shape[0], 20:20 + c.shape[1]] = c
    per = [[] for _ in crops]
    for w in ocr.words(canvas, "Latin", 4):
        i = int((w["box"][1] + w["box"][3] / 2 - gap / 2) // (height + gap))
        if 0 <= i < len(per):
            x0, sc, lb = spans[i]
            per[i].append({**w, "box": [round(x0 + (w["box"][0] - 20) / sc), lb[1], round(w["box"][2] / sc), lb[3]], "line": str(i)})
    return [sorted(p, key=lambda w: w["box"][0]) for p in per]


def _vocab(lang: str | None) -> frozenset:
    code = lang if lang in LANGS else "en"
    return frozenset(str(w).lower() for w in model(code)["words"][:40000])


def _score(ws: list[dict], vocab: frozenset, ref: str) -> tuple:
    """Half the share of letters in dictionary words (or numbers), half the agreement of the letters with RapidOCR's
    reading of the line: junk made of short real words ('me em') cannot win on the dictionary alone."""
    from difflib import SequenceMatcher

    toks = [_plain(re.sub(r"[^\w]", "", w["text"])) for w in ws]
    letters = sum(len(t) for t in toks) or 1
    in_dict = sum(len(t) for t in toks if t in vocab or t.isdigit())
    agree = SequenceMatcher(None, "".join(toks), _plain(re.sub(r"[^\w]", "", ref))).ratio()
    conf = float(np.mean([w["conf"] for w in ws])) if ws else 0.0
    accents = sum(1 for w in ws for c in w["text"] if c.isalpha() and not c.isascii())
    # accents only break ties: RapidOCR's reader has none, so an otherwise equal Tesseract reading keeps 'près'
    return (round(0.5 * in_dict / letters + 0.5 * agree, 3), accents, conf)


def _plain(t: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode()


def _dedupe(ws: list[dict]) -> list[dict]:
    """Repeated neighbours from overlapping passes ('BY BY') collapse to one."""
    out = []
    for w in ws:
        if out and out[-1]["text"] == w["text"]:
            continue
        out.append(w)
    return out


def photo_words(gray: np.ndarray) -> list[dict]:
    from ..langid import detect as identify

    lines = _lines(gray)
    if not lines:
        return []
    s = ocr.scale_for(gray)
    page = ocr.merge([ocr._pass(gray, "Latin", k, s * f, psm) for k, f, psm in ocr.PASSES])
    lang = identify(" ".join(t for _, t, _ in lines), 1)
    vocab = _vocab(lang[0]["lang"] if lang else None)
    st = [_stacked(gray, lines, h) for h in (48, 72)]
    out = []
    for i, (box, txt, conf) in enumerate(lines):
        inside = [{**w, "line": str(i)} for w in page if box[1] <= w["box"][1] + w["box"][3] / 2 <= box[1] + box[3]
                  and box[0] - 4 <= w["box"][0] + w["box"][2] / 2 <= box[0] + box[2] + 4]
        cands = [_spread(txt, box, conf * 100, str(i)), st[0][i], st[1][i], sorted(inside, key=lambda w: w["box"][0])]
        cands = [_dedupe(c) for c in cands if c]
        best = max(cands, key=lambda c: _score(c, vocab, txt))
        out += [{**w, "conf": max(w["conf"], 60.0)} if _score(best, vocab, txt)[0] >= 0.6 else w for w in best]
    return out
