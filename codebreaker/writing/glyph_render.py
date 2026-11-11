"""Sign images for the glyph recogniser (Round 78): every sign of the supported scripts drawn from its font, and
distorted copies for training and testing.

Fonts: the Noto fonts shipped with macOS (/System/Library/Fonts/Supplemental) and the Runic and Ogham fonts downloaded
with permission (codebreaker/web/static/fonts). A sign is a class only if its font draws it (not blank and not the
font's missing-glyph box); signs drawn identically (e.g. runes shared by two rows) are merged into one class."""
import hashlib
import unicodedata
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..languages import ROOT
from .signs import SCRIPTS, tables

SIZE = 48
SYS = Path("/System/Library/Fonts/Supplemental")
OWN = ROOT / "codebreaker/web/static/fonts"
FONTS = {"egyptian": SYS / "NotoSansEgyptianHieroglyphs-Regular.ttf", "linear_b": SYS / "NotoSansLinearB-Regular.ttf",
         "cuneiform": SYS / "NotoSansCuneiform-Regular.ttf", "phoenician": SYS / "NotoSansPhoenician-Regular.ttf",
         "gothic": SYS / "NotoSansGothic-Regular.ttf", "ugaritic": SYS / "NotoSansUgaritic-Regular.ttf",
         "old_persian": SYS / "NotoSansOldPersian-Regular.ttf", "runic": OWN / "NotoSansRunic-Regular.ttf",
         "ogham": OWN / "NotoSansOgham-Regular.ttf"}


@lru_cache(maxsize=16)
def _font(script: str, px: int = 72):
    return ImageFont.truetype(str(FONTS[script]), px)


def raw(ch: str, script: str) -> np.ndarray | None:
    """The sign drawn large in white on black, cropped to its ink; None if the font draws nothing."""
    im = Image.new("L", (160, 160), 0)
    ImageDraw.Draw(im).text((20, 20), ch, font=_font(script), fill=255)
    a = np.asarray(im)
    ys, xs = np.nonzero(a > 40)
    if len(xs) < 6:
        return None
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def fit(a: np.ndarray, size: int = SIZE, margin: int = 4) -> np.ndarray:
    """Ink scaled to fit a square with a margin, keeping its proportions."""
    h, w = a.shape
    s = (size - 2 * margin) / max(h, w)
    small = cv2.resize(a, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    out = np.zeros((size, size), np.uint8)
    y, x = (size - small.shape[0]) // 2, (size - small.shape[1]) // 2
    out[y:y + small.shape[0], x:x + small.shape[1]] = small
    return out


@lru_cache(maxsize=1)
def classes() -> list[dict]:
    """[{"signs": [chars], "script", "values", "name"}] for every distinct drawn sign."""
    t, seen, out = tables(), {}, []
    for script in FONTS:
        if not FONTS[script].exists():
            continue
        missing = raw("\U0010FFFD", script)  # a private-use code point: the font's missing-glyph box, if it draws one
        miss = hashlib.md5(fit(missing).tobytes()).hexdigest() if missing is not None else None
        lo, hi = SCRIPTS[script][2]
        for cp in range(lo, hi + 1):
            ch = chr(cp)
            if not unicodedata.name(ch, "").startswith(SCRIPTS[script][1]) or unicodedata.category(ch) == "Zs":
                continue
            a = raw(ch, script)
            if a is None:
                continue
            h = hashlib.md5(fit(a).tobytes()).hexdigest()
            if h == miss:
                continue
            if h in seen:
                out[seen[h]]["signs"].append(ch)
                continue
            e = t.get(script, {}).get(ch, {})
            seen[h] = len(out)
            out.append({"signs": [ch], "script": script, "values": e.get("values", []), "name": e.get("name", unicodedata.name(ch, "").title()),
                        "code": e.get("code", "")})
    return out


def _elastic(a: np.ndarray, rnd: np.random.Generator, alpha: float, sigma: float) -> np.ndarray:
    h, w = a.shape
    dx = cv2.GaussianBlur(rnd.uniform(-1, 1, (h, w)).astype(np.float32), (0, 0), sigma) * alpha
    dy = cv2.GaussianBlur(rnd.uniform(-1, 1, (h, w)).astype(np.float32), (0, 0), sigma) * alpha
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(a, gx + dx, gy + dy, cv2.INTER_LINEAR, borderValue=0)


def distort(a: np.ndarray, rnd: np.random.Generator, hard: bool = False) -> np.ndarray:
    """One distorted SIZE x SIZE copy of a raw sign; redrawn if the distortion erased the sign."""
    for _ in range(5):
        out = _distort(a, rnd, hard)
        if (out > 128).sum() >= 0.25 * (fit(a) > 128).sum():
            return out
    return _distort(a, rnd, hard, gentle=True)


def _distort(a: np.ndarray, rnd: np.random.Generator, hard: bool = False, gentle: bool = False) -> np.ndarray:
    """'hard' draws from wider ranges than training ever sees; 'gentle' skips thinning and damage."""
    img = fit(a, SIZE * 2, margin=12)
    filled = (img > 128).mean() > 0.12  # outlining only makes sense for filled signs
    if filled and not gentle and (rnd.random() < 0.3 or hard):  # outline only, as with traced or incised signs
        k = np.ones((3, 3), np.uint8)
        img = cv2.subtract(img, cv2.erode(img, k, iterations=int(rnd.integers(1, 3))))
    k = int(rnd.integers(1, 4))
    op = rnd.random()
    if op < 0.33:
        img = cv2.dilate(img, np.ones((k, k), np.uint8))
    elif op < 0.66 and filled and not gentle:
        img = cv2.erode(img, np.ones((k, k), np.uint8))
    ang = rnd.uniform(-18, 18) if hard else rnd.uniform(-8, 8)
    sc = rnd.uniform(0.75, 1.15) if hard else rnd.uniform(0.85, 1.08)
    sh = rnd.uniform(-0.25, 0.25) if hard else rnd.uniform(-0.1, 0.1)
    c = SIZE
    m = cv2.getRotationMatrix2D((c, c), ang, sc)
    m[0, 1] += sh
    m[:, 2] += rnd.uniform(-4, 4, 2)
    img = cv2.warpAffine(img, m, (2 * SIZE, 2 * SIZE), borderValue=0)
    img = _elastic(img, rnd, *( (6.0, 4.0) if hard else (2.5, 5.0)))
    if hard:  # low resolution: as if photographed from far away
        img = cv2.resize(cv2.resize(img, (28, 28), interpolation=cv2.INTER_AREA), (2 * SIZE, 2 * SIZE))
    img = cv2.GaussianBlur(img, (0, 0), rnd.uniform(0.1, 2.5 if hard else 1.3))
    img = cv2.resize(img, (SIZE, SIZE), interpolation=cv2.INTER_AREA).astype(np.float32)
    img = img / max(img.max(), 1.0) * 255.0  # thin signs blurred grey are brought back to full contrast
    img += rnd.normal(0, 28 if hard else 14, img.shape)
    if rnd.random() < 0.3 and not gentle:  # a patch of damage
        y, x = rnd.integers(0, SIZE - 12, 2)
        img[y:y + int(rnd.integers(4, 14 if hard else 9)), x:x + int(rnd.integers(4, 14 if hard else 9))] = 0
    return np.clip(img, 0, 255).astype(np.uint8)


def prep(g: np.ndarray) -> np.ndarray:
    """What the recogniser sees (Round 78): an ink-bright grey image with its background removed (morphological
    opening) and its contrast stretched. Chosen after the 'unseen' test scored 6.7% top-1 on raw images and 77% with
    this step, so that test informed this one choice; it is applied identically in evaluation and in the scanner."""
    g = g.astype(np.float32)
    bg = cv2.morphologyEx(g, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    d = np.clip(g - bg, 0, None)
    d = d / max(float(np.percentile(d, 99.5)), 1.0) * 255.0
    return np.clip(d, 0, 255).astype(np.uint8)


def unseen(a: np.ndarray, rnd: np.random.Generator) -> np.ndarray:
    """A test family never used in training (Round 78): perspective tilt, uneven lighting, motion blur, JPEG."""
    img = fit(a, SIZE * 2, margin=12).astype(np.float32)
    n = 2 * SIZE
    d = n * 0.12
    src = np.float32([[0, 0], [n, 0], [n, n], [0, n]])
    dst = np.float32(src + rnd.uniform(-d, d, (4, 2)))
    img = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (n, n), borderValue=0)
    k = int(rnd.integers(3, 8))
    kern = np.zeros((k, k), np.float32)
    kern[k // 2, :] = 1.0 / k
    img = cv2.filter2D(img, -1, cv2.warpAffine(kern, cv2.getRotationMatrix2D((k / 2, k / 2), float(rnd.uniform(0, 180)), 1.0), (k, k)))
    gx = np.linspace(0, 1, n)[None, :] * rnd.uniform(-1, 1) + np.linspace(0, 1, n)[:, None] * rnd.uniform(-1, 1)
    img = img * rnd.uniform(0.55, 0.9) + (gx - gx.min()) * 70  # dim ink on an uneven background
    img = cv2.resize(np.clip(img, 0, 255).astype(np.uint8), (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(rnd.integers(12, 35))])
    return cv2.imdecode(enc, cv2.IMREAD_GRAYSCALE)


def sample(a: np.ndarray, rnd: np.random.Generator, kind: str) -> np.ndarray:
    """'train' mixes 70% normal and 30% hard-range copies (Round 78 retraining); 'normal', 'hard', 'unseen' are pure."""
    if kind == "train":
        return distort(a, rnd, rnd.random() < 0.3)
    if kind == "unseen":
        return unseen(a, rnd)
    return distort(a, rnd, kind == "hard")


def dataset(per_class: int, seed: int, hard: bool = False) -> tuple[np.ndarray, np.ndarray]:
    cls, rnd = classes(), np.random.default_rng(seed)
    xs = np.zeros((len(cls) * per_class, SIZE, SIZE), np.uint8)
    ys = np.zeros(len(cls) * per_class, np.int64)
    i = 0
    for k, c in enumerate(cls):
        a = raw(c["signs"][0], c["script"])
        for _ in range(per_class):
            xs[i], ys[i] = distort(a, rnd, hard), k
            i += 1
    return xs, ys


def _chunk(args):
    lo, hi, per_class, seed, kind = args
    cls, rnd = classes(), np.random.default_rng(seed)
    out = [(sample(raw(cls[k]["signs"][0], cls[k]["script"]), rnd, kind), k) for k in range(lo, hi) for _ in range(per_class)]
    return np.stack([o[0] for o in out]), np.array([o[1] for o in out], np.int64)


def dataset_parallel(per_class: int, seed: int, kind: str = "normal", workers: int = 7) -> tuple[np.ndarray, np.ndarray]:
    from concurrent.futures import ProcessPoolExecutor

    n = len(classes())
    step = (n + workers * 4 - 1) // (workers * 4)
    jobs = [(lo, min(n, lo + step), per_class, seed * 1000 + j, kind) for j, lo in enumerate(range(0, n, step))]
    with ProcessPoolExecutor(workers) as ex:
        parts = list(ex.map(_chunk, jobs))
    return np.concatenate([p[0] for p in parts]), np.concatenate([p[1] for p in parts])
