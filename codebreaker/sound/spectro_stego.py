"""Pictures hidden in sound (Round 82): written into a spectrogram, read back by looking at it.

hide: each column of a picture sets the strength of every frequency in one short-time frame (rows from the top =
high to low frequency, inside a chosen band), with random phase; the frames are overlap-added (inverse STFT) into a
waveform and mixed into a carrier at a chosen level. reveal: the spectrogram as a picture. detect: text in the
spectrogram, by the Lens's fast OCR reader on a high-contrast rendering, both polarities. Controls (spectro_eval.py):
words hidden in noise, synthetic birdsong and a tone sweep at falling levels, and the same carriers with nothing
hidden for the false-alarm rate."""
import base64

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.signal import istft, stft

SR, NPER = 22050, 512
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def text_image(text: str, height: int = 80) -> np.ndarray:
    font = ImageFont.truetype(FONT, int(height * 0.8))
    w = int(font.getlength(text)) + height // 2
    im = Image.new("L", (w, height), 0)
    ImageDraw.Draw(im).text((height // 4, height // 10), text, font=font, fill=255)
    return np.asarray(im)


def hide(img: np.ndarray, seconds: float = 4.0, band=(3000.0, 9000.0), sr: int = SR, seed: int = 0) -> np.ndarray:
    """A waveform whose spectrogram shows img in the band (unit peak). img: grey, bright = loud."""
    rnd = np.random.default_rng(seed)
    hop = NPER // 4
    frames = int(seconds * sr / hop)
    freqs = np.fft.rfftfreq(NPER, 1 / sr)
    rows = np.where((freqs >= band[0]) & (freqs <= band[1]))[0]
    pic = cv2.resize(img.astype(np.float32) / 255.0, (frames, len(rows)), interpolation=cv2.INTER_AREA)[::-1]
    mag = np.zeros((len(freqs), frames), np.float32)
    mag[rows] = pic ** 1.5
    z = mag * np.exp(2j * np.pi * rnd.random(mag.shape))
    _, x = istft(z, sr, nperseg=NPER, noverlap=NPER - hop)
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)


def mix(carrier: np.ndarray, hidden: np.ndarray, level_db: float) -> np.ndarray:
    """hidden added at level_db relative to the carrier's RMS (0 dB = equal RMS)."""
    n = min(len(carrier), len(hidden))
    c, h = carrier[:n], hidden[:n]
    gain = np.sqrt(np.mean(c ** 2) / (np.mean(h ** 2) + 1e-12)) * 10 ** (level_db / 20)
    y = c + gain * h
    return (y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def spectrogram_image(x: np.ndarray, sr: int = SR, height: int = 360) -> np.ndarray:
    """0-255 picture: loudness over frequency (up) and time (across), contrast set by percentiles."""
    _, _, z = stft(x, sr, nperseg=NPER, noverlap=NPER * 3 // 4)
    db = 20 * np.log10(np.abs(z) + 1e-7)
    lo, hi = np.percentile(db, 20), np.percentile(db, 99.5)
    img = np.clip((db - lo) / (hi - lo + 1e-9) * 255, 0, 255).astype(np.uint8)[::-1]
    w = min(2400, max(400, img.shape[1]))
    return cv2.resize(img, (w, height), interpolation=cv2.INTER_AREA)


def png(img: np.ndarray) -> str:
    rgb = cv2.applyColorMap(img, cv2.COLORMAP_MAGMA)
    return "data:image/png;base64," + base64.b64encode(cv2.imencode(".png", rgb)[1].tobytes()).decode()


def structure(x: np.ndarray, sr: int = SR, sigma: float = 4.0) -> float:
    """Large-scale structure in the spectrogram beyond what each frequency and each moment explain: the log power
    with every row's and every column's median removed, smoothed (Gaussian, sigma bins), then its variance. Noise
    leaves only fine grain, which smoothing averages away; a hidden picture leaves shapes the size of letters."""
    _, _, z = stft(x, sr, nperseg=NPER, noverlap=NPER * 3 // 4)
    db = 10 * np.log10(np.abs(z) ** 2 + 1e-12)
    db = db - np.median(db, axis=1, keepdims=True)
    db = db - np.median(db, axis=0, keepdims=True)
    return float(cv2.GaussianBlur(db.astype(np.float32), (0, 0), sigma).var())


def detect(x: np.ndarray, sr: int = SR, min_len: int = 3) -> dict:
    """Words read in the spectrogram (either polarity); only words of min_len+ letters count as a finding."""
    from ..lens.ocr_deep import live_words

    img = spectrogram_image(x, sr)
    words = []
    for view in (img, 255 - img):
        for w in live_words(view):
            core = "".join(c for c in w["text"] if c.isalnum())
            if len(core) >= min_len and sum(c.isalpha() for c in core) >= min_len and w["conf"] >= 70:
                words.append({"text": core, "box": w["box"], "conf": w["conf"]})
    seen, uniq = set(), []
    for w in words:
        if w["text"].upper() not in seen:
            seen.add(w["text"].upper())
            uniq.append(w)
    return {"words": uniq, "image": png(img), "finding": bool(uniq), "structure": round(structure(x, sr), 4)}
