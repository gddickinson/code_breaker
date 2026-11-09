"""Find how an unknown frame is laid out: the pixel format whose rows line up best, and the width at which they do."""
import random

import cv2
import numpy as np

from .raw_formats import FORMATS, encode, luminance

COMMON = [(160, 120), (176, 144), (320, 240), (352, 288), (640, 480), (752, 480), (800, 600), (1024, 768), (1280, 720), (1280, 960), (1920, 1080)]
SAMPLES = 30000


STEP = 60  # a multiple of every byte interleave here (2, 3, 4, 5), so channel layout cannot fake a row


def stride_curve(b: bytes, lo: int = 64, hi: int = 9000, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """For each candidate row length in bytes, how different each byte is from the byte one row on."""
    x = np.frombuffer(b, dtype=np.uint8).astype(np.float32)
    hi = min(hi, len(x) // 3)
    lengths = np.arange(lo, max(hi, lo + 1))
    rnd = np.random.default_rng(seed)
    i = rnd.integers(0, max(len(x) - hi - 1, 1), size=min(SAMPLES, max(len(x) - hi - 1, 1)))
    base = x[i]
    return lengths, np.array([np.mean(np.abs(base - x[i + L])) for L in lengths])


def best_stride(lengths: np.ndarray, cost: np.ndarray) -> tuple[int, float]:
    """The deepest dip against lengths a multiple of STEP away; the smallest nearly as deep, so double rows lose."""
    n, d = len(cost), np.ones(len(cost))
    for k in range(n):
        side = [cost[k + j * STEP] for j in (-3, -2, -1, 1, 2, 3) if 0 <= k + j * STEP < n]
        if len(side) >= 2:
            d[k] = cost[k] / (np.median(side) + 1e-9)
    floor = float(d.min())
    k = int(np.argmax(d <= floor + 0.1 * (1 - floor)))
    lo, hi = max(0, k - 12), min(n, k + 13)
    k = lo + int(np.argmin(cost[lo:hi]))  # the exact row length is the lowest point inside the dip
    return int(lengths[k]), floor


def row_alternation(b: bytes, stride: int) -> float:
    """Byte difference one row down over two rows down. Above 1 means rows alternate, as in a Bayer mosaic."""
    x = np.frombuffer(b, dtype=np.uint8).astype(np.float32)
    if len(x) < 4 * stride:
        return 1.0
    return float(np.mean(np.abs(x[:-2 * stride] - x[stride:-stride])) / (np.mean(np.abs(x[:-2 * stride] - x[2 * stride:])) + 1e-9))


LANES = {"rgb24": 3, "yuyv": 2}


def lanes_smooth(b: bytes, stride: int, period: int) -> float:
    """The roughest byte lane: in a format made of whole-byte channels, every lane must be a smooth picture."""
    x = np.frombuffer(b[: len(b) - len(b) % period], dtype=np.uint8).astype(float) / 255
    return max(smoothness(x[k::period], stride // period) for k in range(period))


def field_smooth(b: bytes, width: int) -> float:
    """Smoothness of the low five bits alone: smooth for RGB565 blue, noisy for the low bits of a 16-bit sensor."""
    v = (np.frombuffer(b[: len(b) - len(b) % 2], dtype="<u2") & 31).astype(float) / 31
    return smoothness(v, width)


def smoothness(lum: np.ndarray, width: int, lag: int = 1) -> float:
    """Neighbouring pixels against random pairs: low for a correct decoding, near 1 for noise."""
    if len(lum) < 3 * width + lag:
        return 1.0
    rnd = np.random.default_rng(3)
    i = rnd.integers(0, len(lum) - width - lag, size=min(SAMPLES, len(lum) - width - lag))
    j = rnd.integers(0, len(lum), size=len(i))
    near = np.mean(np.abs(lum[i] - lum[i + lag])) + np.mean(np.abs(lum[i] - lum[i + width]))
    return float(near / (2 * np.mean(np.abs(lum[i] - lum[j])) + 1e-9))


def bayer_check(lum: np.ndarray, width: int) -> dict | None:
    """A colour mosaic: pixels two apart match much better than adjacent ones, in both directions."""
    if width % 2 or len(lum) < 8 * width:
        return None
    one, two = smoothness(lum, width, 1), smoothness(lum, 2 * width, 2)
    if two > 0.8 * one:
        return None
    h = len(lum) // width
    g = lum[: (h - h % 2) * width].reshape(-1, width)
    means = [float(g[dy::2, dx::2].mean()) for dy in (0, 1) for dx in (0, 1)]
    diag = abs(means[0] - means[3]) < abs(means[1] - means[2])
    return {"adjacent": round(one, 3), "two_apart": round(two, 3), "phase_means": [round(m, 3) for m in means], "patterns": ["GRBG", "GBRG"] if diag else ["RGGB", "BGGR"]}


def detect(b: bytes) -> dict:
    """Find the row length in bytes first, then the pixel format that makes neighbouring pixels smoothest."""
    n = len(b)
    lengths, cost = stride_curve(b)
    stride, depth = best_stride(lengths, cost)
    rows = []
    for fmt, info in FORMATS.items():
        width = stride / info["bytes_per_pixel"]
        if abs(width - round(width)) > 1e-6 or round(width) < 8:
            continue
        width = int(round(width))
        lum = luminance(b, fmt)
        rows.append({"format": fmt, "name": info["name"], "width": width, "height": len(lum) // width, "leftover_bytes": n % stride, "smoothness": round(smoothness(lum, width), 4)})
    for r in rows:
        if r["format"] in LANES and lanes_smooth(b, stride, LANES[r["format"]]) > 0.75:
            r["smoothness"] = round(r["smoothness"] + 1.0, 4)  # a noisy byte lane rules this format out
            r["note"] = "one byte lane is noise"
    lum8, bay = luminance(b, "gray8"), None
    for s_try in [stride]:
        alt = row_alternation(b, s_try)
        if alt > 1.15 and (bay := bayer_check(lum8, s_try)):
            bay["row_alternation"] = round(alt, 3)
            rows.append({"format": "bayer", "name": "Bayer colour mosaic, 8-bit", "width": s_try, "height": n // s_try, "leftover_bytes": n % s_try, "smoothness": 0.0})
            break
    rows.sort(key=lambda r: r["smoothness"])
    pair = {r["format"]: r for r in rows if r["format"] in ("gray16le", "rgb565")}
    if len(pair) == 2 and rows[0]["format"] in pair and abs(pair["gray16le"]["smoothness"] - pair["rgb565"]["smoothness"]) < 0.15 * max(pair["gray16le"]["smoothness"], 1e-9):
        first = "rgb565" if field_smooth(b, pair["rgb565"]["width"]) < 0.6 else "gray16le"
        rows.sort(key=lambda r: (r["format"] != first, r["smoothness"]))
    step = max(1, len(cost) // 400)
    return {"bytes": n, "stride": stride, "dip": round(depth, 3), "curve": [round(float(c), 3) for c in cost[::step]], "curve_start": int(lengths[0]), "curve_step": step, "ranking": rows, "best": rows[0] if rows else None, "bayer": bay}


def scene(w: int, h: int, seed: int) -> np.ndarray:
    """A synthetic picture with smooth shading, shapes, text and sensor noise."""
    rnd = random.Random(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    img = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        img[:, :, c] = 60 + 120 * (0.5 + 0.5 * np.sin(xx / (w / rnd.uniform(1, 3)) + c + rnd.random() * 6) * np.cos(yy / (h / rnd.uniform(1, 3))))
    img = img.astype(np.uint8)
    for _ in range(6):
        cv2.circle(img, (rnd.randrange(w), rnd.randrange(h)), rnd.randrange(8, max(9, h // 4)), tuple(int(rnd.randrange(256)) for _ in range(3)), -1)
    cv2.putText(img, "CODE BREAKER", (w // 10, h // 2), cv2.FONT_HERSHEY_SIMPLEX, max(0.4, w / 600), (250, 250, 250), 2)
    noise = np.random.default_rng(seed).normal(0, 3, img.shape)
    return np.clip(img + noise, 0, 255).astype(np.uint8)


def depth_scene(w: int, h: int, seed: int) -> np.ndarray:
    """An 11-bit depth map like a Kinect's: a floor plane, a wall and a sphere, with invalid pixels at 2047."""
    rnd = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    d = 600 + 0.9 * yy + 0.2 * xx
    cx, cy, r = w * 0.55, h * 0.45, h * 0.22
    inside = (xx - cx) ** 2 + (yy - cy) ** 2 < r * r
    d[inside] = 420 - np.sqrt(np.maximum(r * r - (xx - cx) ** 2 - (yy - cy) ** 2, 0))[inside] * 0.6
    d += rnd.normal(0, 1.5, d.shape)
    d[rnd.random(d.shape) < 0.01] = 2047
    d[:, : w // 16] = 2047
    return np.clip(d, 0, 2047).astype(np.uint16)


def example(kind: str, w: int = 320, h: int = 240, seed: int = 1) -> tuple[bytes, dict]:
    """A generated capture with its true layout, for teaching and controls."""
    if kind == "kinect11":
        return encode(depth_scene(w, h, seed), "kinect11"), {"format": "kinect11", "width": w, "height": h}
    if kind == "bayer":
        return encode(scene(w, h, seed), "bayer", "RGGB"), {"format": "bayer", "width": w, "height": h}
    return encode(scene(w, h, seed), kind), {"format": kind, "width": w, "height": h}


def control(sizes=((320, 240), (640, 480), (752, 480), (176, 144)), seeds=(1, 2)) -> dict:
    rows = []
    for kind in list(FORMATS) + ["bayer"]:
        for (w, h) in sizes:
            for s in seeds:
                data, truth = example(kind, w, h, s)
                got = detect(data)["best"]
                rows.append({"kind": kind, "size": f"{w}x{h}", "seed": s, "format_ok": got["format"] == truth["format"], "width_ok": got["width"] == truth["width"], "got": f"{got['format']} {got['width']}"})
    return {"cases": len(rows), "format_ok": sum(r["format_ok"] for r in rows), "width_ok": sum(r["width_ok"] for r in rows), "both_ok": sum(r["format_ok"] and r["width_ok"] for r in rows), "rows": rows}
