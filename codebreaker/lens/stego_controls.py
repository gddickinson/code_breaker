"""Controls for the image hidden-message tests (Round 78b): how they behave on clean images and on known embeddings.

Clean images: 30 crops of the Le Figaro scans (photographed newsprint, decoded to lossless grey) and 80 generated
scenes (signals.raw_detect.scene). Each is also given a random message in its least significant bits at a known rate
(random positions), and once sequentially (the first half of the pixels, as simple tools do). The alarm level for
sample pair analysis is the 99th percentile on clean images (rounded up); detection rates are reported per rate."""
import json

import cv2
import numpy as np

from ..languages import ROOT
from ..signals.raw_detect import scene
from .stego import chi_square, spa

RESULT = ROOT / "data/results/stego_controls.json"
IMAGES = ROOT / "data/sources/figaro/images"
RATES = (0.02, 0.05, 0.1, 0.25, 0.5, 1.0)


def clean_set(seed: int = 78) -> list[np.ndarray]:
    rnd = np.random.default_rng(seed)
    files = sorted(IMAGES.glob("*.jpg"))
    out = []
    for f in rnd.choice(files, min(60, len(files)), replace=False):
        g = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        if g is None or min(g.shape) < 64:
            continue
        h, w = g.shape
        y, x = rnd.integers(0, max(1, h - 256)), rnd.integers(0, max(1, w - 256))
        out.append(g[y:y + 256, x:x + 256])
        if len(out) == 30:
            break
    for k in range(80):
        sc = scene(256, 192, seed + k)
        out.append(cv2.cvtColor(sc, cv2.COLOR_RGB2GRAY) if sc.ndim == 3 else sc.astype(np.uint8))
    return out


def embed(img: np.ndarray, rate: float, rnd: np.random.Generator, sequential: bool = False) -> np.ndarray:
    flat = img.ravel().copy()
    n = int(rate * flat.size)
    idx = np.arange(n) if sequential else rnd.choice(flat.size, n, replace=False)
    flat[idx] = (flat[idx] & 0xFE) | rnd.integers(0, 2, n).astype(np.uint8)
    return flat.reshape(img.shape)


def run(seed: int = 78) -> dict:
    """The lossless generated scenes set the alarm and the detection rates (flat ones skipped, as the analysis does);
    the Le Figaro crops, which were once JPEGs, measure the false alarms that JPEG history causes."""
    rnd, imgs = np.random.default_rng(seed), clean_set(seed)
    jpeg, lossless = imgs[:30], imgs[30:]
    usable = [i for i in lossless if spa(i) is not None]
    clean_spa = [spa(i) for i in usable]
    alarm = float(np.ceil(max(np.quantile(clean_spa, 0.99), 0.01) * 100) / 100)
    rates = {}
    for r in RATES:
        est = [spa(embed(i, r, rnd)) for i in usable]
        est = [e for e in est if e is not None]
        rates[str(r)] = {"detected": round(float(np.mean([e > alarm for e in est])), 3), "estimate_median": round(float(np.median(est)), 3)}
    clean_chi = [chi_square(i, 0.5) for i in usable]
    seq = [chi_square(embed(i, 0.5, rnd, sequential=True), 0.5) for i in usable]
    jp = [spa(i) for i in jpeg]
    jp = [e for e in jp if e is not None]
    jpeg_false = float(np.mean([e > alarm for e in jp])) if jp else None
    return {"id": "stego_controls", "jpeg_history_images": len(jpeg), "false_alarms_on_former_jpegs": None if jpeg_false is None else round(jpeg_false, 3),
            "lossless_images": len(lossless), "usable_lossless": len(usable), "clean_spa_median": round(float(np.median(clean_spa)), 3),
            "clean_spa_p99": round(float(np.quantile(clean_spa, 0.99)), 3), "spa_alarm": alarm, "rates": rates,
            "chi_clean_false_alarms": round(float(np.mean([c > 0.95 for c in clean_chi])), 3),
            "chi_sequential_half_detected": round(float(np.mean([c > 0.95 for c in seq])), 3),
            "note": "Generated scenes stand in for clean lossless photographs; real camera images may differ. Full embedding (rate 1.0) is a blind spot of sample pair analysis."}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
