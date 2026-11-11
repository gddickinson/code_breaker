"""Data for a line reader trained for the Le Figaro cipher ads (Round 88b).

Truth: every by-eye transcription in the project that names its scan (data/sources/figaro/*transcription*.json,
data/mysteries/figaro_hand_readings.json and figaro_digit_hand.json), reduced to lower-case letters and digits: the
reader ignores case, spaces and punctuation, which the ciphers do not need. Lines: each scan is cut into printed lines
between its rules by row ink profiles. Synthetic lines: cipher-like strings, French words and signatures drawn in slab
and modern serif faces like the paper's (Rockwell, SuperClarendon, Georgia, Bodoni, Charter, Times) and degraded like
the scans (blur, ink spread, noise, JPEG, rules). Alignment: a transcription is located in a reader's output by local
edit-distance alignment; the character error rate counts the edits over the transcription's length."""
import json
import random
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..languages import ROOT

IMAGES = ROOT / "data/sources/figaro/images"
ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
H = 32
FONTS = [("Supplemental/Rockwell.ttc", (0, 1)), ("Supplemental/SuperClarendon.ttc", (0, 1, 2)), ("Supplemental/Georgia Bold.ttf", (0,)),
         ("Supplemental/Bodoni 72.ttc", (0, 1)), ("Supplemental/Charter.ttc", (0, 1)), ("Times.ttc", (0, 1))]


def norm(s: str) -> str:
    return "".join(c for c in s.lower() if c in ALPHABET)


def _texts(v) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in ("cipher", "ciphertext", "words"):
            if isinstance(v.get(k), str):
                return v[k]
        if isinstance(v.get("blocks"), list):
            return " ".join(v["blocks"])
    return ""


def truth() -> dict[str, str]:
    """Scan file name -> transcribed cipher text (letters and digits, lower case); the longest if read twice."""
    out = {}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(k, str) and k.endswith(".jpg"):
                    t = norm(_texts(v))
                    if len(t) >= 8 and len(t) > len(out.get(k, "")) and (IMAGES / k).exists():
                        out[k] = t
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for f in sorted((ROOT / "data/sources/figaro").glob("*transcription*.json")) + [ROOT / "data/mysteries/figaro_hand_readings.json", ROOT / "data/mysteries/figaro_digit_hand.json"]:
        if f.exists():
            walk(json.loads(f.read_text()))
    return out


def gray(path) -> np.ndarray:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)


def cut_lines(img: np.ndarray, min_h: int = 12) -> list[np.ndarray]:
    """Printed lines between the rules. Rows inked across most of the width (rules) are dropped; a band of text is
    split between the peaks of its row-ink profile smoothed at letter scale (one peak per printed line), since lines
    are often set with no blank row between them."""
    ink = (img < 128).mean(axis=1)
    text = (ink > 0.02) & (ink < 0.5)
    bands, start = [], None
    for y, t in enumerate(list(text) + [False]):
        if t and start is None:
            start = y
        elif not t and start is not None:
            if y - start >= min_h:
                bands.append((start, y))
            start = None
    xh = x_height(img)
    bands = [(a, b) for a, b in bands if b - a >= 0.8 * xh] or bands  # slivers below a rule that crosses the descenders
    lines = []
    for a, b in bands:
        prof = np.convolve(ink[a:b], np.ones(xh) / xh, mode="same")  # smoothed at the scale of a letter
        peaks = [y for y in range(1, b - a - 1) if prof[y] >= prof[y - 1] and prof[y] >= prof[y + 1] and prof[y] > 0.4 * prof.max()]
        kept = []
        for y in sorted(peaks, key=lambda y: -prof[y]):  # strongest first; one peak per printed line
            if all(abs(y - k) >= 1.6 * xh for k in kept):
                kept.append(y)
        kept.sort()
        cuts = [a] + [a + p0 + int(np.argmin(prof[p0:p1])) for p0, p1 in zip(kept, kept[1:])] + [b]
        lines += [img[max(0, c0 - 2):c1 + 2] for c0, c1 in zip(cuts, cuts[1:]) if c1 - c0 >= min_h]
    return lines


def x_height(img: np.ndarray) -> int:
    """Median height of the ink blobs (mostly lower-case letters), at least 6 pixels."""
    n, _, stats, _ = cv2.connectedComponentsWithStats((img < 128).astype(np.uint8))
    hs = [h for x, y, w, h, area in stats[1:] if 4 <= h <= 60 and area >= 8 and w < 3 * h]
    return max(6, int(np.median(hs))) if hs else 12


def to_input(line: np.ndarray) -> np.ndarray:
    """Height H, width in proportion, ink bright on dark, 0-1 floats."""
    h, w = line.shape
    x = cv2.resize(line, (max(8, int(w * H / h)), H), interpolation=cv2.INTER_AREA)
    return (255 - x).astype(np.float32) / 255.0


def synthetic_text(rnd: random.Random, words: list[str]) -> str:
    kind = rnd.random()
    if kind < 0.35:  # letter cipher, sometimes in groups
        s = "".join(rnd.choice(ALPHABET[:26]) for _ in range(rnd.randint(8, 26)))
    elif kind < 0.55:  # digits and letter-digit mixtures
        pool = ALPHABET[26:] * 3 + ALPHABET[:26] if rnd.random() < 0.5 else ALPHABET[26:]
        s = "".join(rnd.choice(pool) for _ in range(rnd.randint(8, 24)))
    else:  # ad copy: words, sometimes a signature
        s = " ".join(rnd.choice(words) for _ in range(rnd.randint(2, 5)))
        if rnd.random() < 0.4:
            s = rnd.choice(["L. C. 15.—", "C. H. —", "V. E. 3 —", "Jean. —", "A. B. —"]) + " " + s
    if rnd.random() < 0.5:
        s = " ".join(s[i:i + rnd.randint(3, 7)] for i in range(0, len(s), 5)) if " " not in s else s
    return s + rnd.choice(["", ".", " —", ","])


def render(text: str, rnd: random.Random) -> np.ndarray:
    path, faces = rnd.choice(FONTS)
    font = ImageFont.truetype(str(Path("/System/Library/Fonts") / path), rnd.randint(30, 44), index=rnd.choice(faces))
    w = int(font.getlength(text)) + 30
    im = Image.new("L", (w, 64), 255)
    ImageDraw.Draw(im).text((12, 10), text, font=font, fill=0)
    a = np.asarray(im).copy()
    if rnd.random() < 0.5:  # ink spread or thin print
        k = np.ones((2, 2), np.uint8)
        a = cv2.erode(a, k) if rnd.random() < 0.6 else cv2.dilate(a, k)
    scale = rnd.uniform(0.35, 0.7)  # down to scan resolution and back
    small = cv2.resize(a, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (3, 3), rnd.uniform(0.2, 1.0))
    small = np.clip(small.astype(np.float32) * rnd.uniform(0.8, 1.0) + rnd.uniform(0, 40) + np.random.default_rng(rnd.randint(0, 1 << 30)).normal(0, rnd.uniform(2, 14), small.shape), 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, rnd.randint(30, 85)])
    small = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    rows = np.where((small < 140).any(axis=1))[0]
    if len(rows):
        small = small[max(0, rows[0] - rnd.randint(1, 4)):rows[-1] + rnd.randint(2, 5)]
    return small


def local_align(t: str, o: str) -> tuple[int, int, int]:
    """Best match of t inside o by edit distance (free start and end in o): (edits, start, end) in o."""
    n, m = len(t), len(o)
    prev = list(range(n + 1))
    prev_start = [0] * (n + 1)
    best = (n, 0, 0)
    cols = []
    for j in range(1, m + 1):
        cur, cur_start = [0], [j]
        for i in range(1, n + 1):
            sub = prev[i - 1] + (t[i - 1] != o[j - 1])
            opts = ((sub, prev_start[i - 1]), (prev[i] + 1, prev_start[i]), (cur[i - 1] + 1, cur_start[i - 1]))
            v, s = min(opts)
            cur.append(v)
            cur_start.append(s)
        if cur[n] <= best[0]:  # on equal edits the longer match, so a wrong last character is counted
            best = (cur[n], cur_start[n], j)
        prev, prev_start = cur, cur_start
        cols.append(cur)
    return best


def cer(t: str, output: str) -> float:
    """Character error rate of the transcription t as found in a reader's output (both normalised)."""
    t, o = norm(t), norm(output)
    if not t:
        return 0.0
    return min(1.0, local_align(t, o)[0] / len(t)) if o else 1.0


def french_words() -> list[str]:
    from ..languages import corpus_text

    words = re.findall(r"[a-zéèêàçùôîû]{2,12}", corpus_text("fr")[:400000].lower())
    return words[::7] or ["vous", "pense", "toujours"]
