"""Image reconstruction with a known answer, and the example pictures for the Recovery page."""
import random
import string

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..languages import ROOT
from . import figaro_ocr as O
from .recovery import IMAGES, read_with, recovered

STATIC = ROOT / "codebreaker/web/static/recovery"
FONT = "/System/Library/Fonts/Times.ttc"
STAGES = ["damaged", "flatten background", "straighten", "remove noise", "undo blur", "enlarge", "threshold"]


def render(text: str) -> np.ndarray:
    font = ImageFont.truetype(FONT, 44)
    w = int(font.getlength(text)) + 80
    im = Image.new("L", (w, 96), 255)
    ImageDraw.Draw(im).text((40, 20), text, font=font, fill=0)
    return np.array(im)


def degrade(img: np.ndarray, rnd: np.random.Generator, angle: float, sigma: float = 2.0) -> np.ndarray:
    """Tilt, ink spread, uneven paper and sensor noise."""
    h, w = img.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1)
    out = cv2.warpAffine(img, m, (w, h), borderValue=255).astype(float)
    out = cv2.GaussianBlur(out, (0, 0), sigma)
    out = out * (0.62 + 0.3 * np.linspace(0, 1, w)[None, :])
    return np.clip(out + rnd.normal(0, 16, out.shape), 0, 255).astype(np.uint8)


def flatten(img: np.ndarray) -> np.ndarray:
    bg = cv2.GaussianBlur(cv2.dilate(img, np.ones((15, 15))), (0, 0), 25)
    return np.clip(img.astype(float) / np.maximum(bg, 1) * 235, 0, 255).astype(np.uint8)


def skew_angle(img: np.ndarray) -> float:
    """The rotation that lines the ink up best into rows."""
    ink, h, w = 255.0 - img, img.shape[0], img.shape[1]
    ink = np.where(ink > ink.mean() + ink.std(), ink, 0)

    def sharp(a):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), float(a), 1)
        return np.var(cv2.warpAffine(ink, m, (w, h)).sum(axis=1))

    return float(max(np.arange(-6, 6.01, 0.25), key=sharp))


def straighten(img: np.ndarray) -> np.ndarray:
    h, w = img.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), skew_angle(img), 1)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)


def wiener(img: np.ndarray, sigma: float = 2.0, k: float = 0.02) -> np.ndarray:
    """Divide out a Gaussian blur in frequency space, damped where noise would dominate."""
    h, w = img.shape
    fy, fx = np.fft.fftfreq(h)[:, None], np.fft.rfftfreq(w)[None, :]
    psf = np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))
    out = np.fft.irfft2(np.fft.rfft2(img.astype(float)) * psf / (psf ** 2 + k), s=(h, w))
    return np.clip(out, 0, 255).astype(np.uint8)


def pipeline(img: np.ndarray) -> list[np.ndarray]:
    """Each restoration stage, cumulative, starting from the damaged image."""
    a = [img]
    a.append(flatten(a[-1]))
    a.append(straighten(a[-1]))
    a.append(cv2.fastNlMeansDenoising(a[-1], None, 14, 7, 21))
    a.append(wiener(a[-1]))
    a.append(cv2.resize(a[-1], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    a.append(cv2.threshold(a[-1], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1])
    return a


def random_line(rnd: random.Random) -> str:
    return " ".join("".join(rnd.choices(string.ascii_lowercase, k=rnd.randint(3, 7))) for _ in range(6))


def experiment(n: int = 40) -> dict:
    """Random-letter lines, so no language model can help: only the pixels count."""
    rnd, np_rnd = random.Random(8), np.random.default_rng(8)
    totals, clean = {s: 0.0 for s in STAGES}, 0.0
    for t in range(n):
        line = random_line(rnd)
        img = render(line)
        clean += recovered(line, read_with(img, "tesseract"))
        stages = pipeline(degrade(img, np_rnd, rnd.uniform(-4, 4)))
        for name, s in zip(STAGES, stages):
            totals[name] += recovered(line, read_with(s, "tesseract"))
        if t == 0:
            for i, s in enumerate(stages):
                f = 0.33 if i >= 5 else 0.66
                cv2.imwrite(str(STATIC / f"stage{i}.png"), cv2.resize(s, None, fx=f, fy=f, interpolation=cv2.INTER_AREA))
    return {"lines": n, "clean": round(clean / n, 3), "stages": [{"stage": s, "recovered": round(totals[s] / n, 3)} for s in STAGES]}


def gallery() -> list[str]:
    """Real scans through the real cleanup steps."""
    made = []
    for key, name in (("ad25", "1894_18940920-25.jpg"), ("adn", "1884_18840109-N.jpg")):
        cv2.imwrite(str(STATIC / f"{key}_scan.png"), cv2.imread(str(IMAGES / name)))
        for v in ("otsu", "adaptive", "denoise"):
            img = O.variant(str(IMAGES / name), v)
            cv2.imwrite(str(STATIC / f"{key}_{v}.png"), cv2.resize(img, None, fx=0.4, fy=0.4, interpolation=cv2.INTER_AREA))
        made.append(key)
    return made
