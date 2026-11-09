"""A song as a code: find the syllables, sort them into types, and measure the sequence like a text."""
import base64
import io
import math
from collections import Counter

import cv2
import numpy as np
from scipy.signal import stft

from .audio import resample

SR = 22050


def spectrogram(x: np.ndarray, sr: int, nper: int = 512) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    f, t, z = stft(x, sr, nperseg=nper, noverlap=nper * 3 // 4)
    return f, t, 20 * np.log10(np.abs(z) + 1e-7)


def spectrogram_png(db: np.ndarray, marks: list | None = None, n_frames: int = 0) -> str:
    """Loudness over frequency (up) and time (across), coloured; syllable spans drawn underneath."""
    lo, hi = np.percentile(db, 5), np.percentile(db, 99.7)
    img = np.clip((db - lo) / (hi - lo + 1e-9) * 255, 0, 255).astype(np.uint8)[::-1]
    w = min(img.shape[1], 2400)
    img = cv2.resize(img, (w, 220), interpolation=cv2.INTER_AREA)
    rgb = cv2.applyColorMap(img, cv2.COLORMAP_MAGMA)
    if marks and n_frames:
        bar = np.full((22, w, 3), 20, np.uint8)
        for s, e, label in marks:
            a, b = int(s / n_frames * w), max(int(e / n_frames * w), int(s / n_frames * w) + 1)
            cv2.rectangle(bar, (a, 2), (b, 19), (200, 220, 60), -1)
            if b - a > 9:
                cv2.putText(bar, label, (a + 1, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (20, 20, 20), 1)
        rgb = np.vstack([rgb, bar])
    ok, buf = cv2.imencode(".png", rgb)
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode()


def syllables(x: np.ndarray, sr: int, band=(1000, 10000), min_gap: float = 0.03, min_len: float = 0.03) -> tuple[list, dict]:
    """Spans where in-band energy rises clearly above the background, with hysteresis."""
    f, t, db = spectrogram(x, sr)
    sel = (f >= band[0]) & (f <= band[1])
    env = db[sel].max(axis=0)
    floor, peak = np.percentile(env, 20), np.percentile(env, 99)
    hi, lo = floor + 0.45 * (peak - floor), floor + 0.3 * (peak - floor)
    spans, on, start = [], False, 0
    for i, v in enumerate(env):
        if not on and v > hi:
            on, start = True, i
        elif on and v < lo:
            spans.append([start, i])
            on = False
    if on:
        spans.append([start, len(env) - 1])
    dt = t[1] - t[0] if len(t) > 1 else 0.01
    merged = []
    for s in spans:
        if merged and (s[0] - merged[-1][1]) * dt < min_gap:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    merged = [s for s in merged if (s[1] - s[0]) * dt >= min_len]
    return merged, {"f": f, "t": t, "db": db, "sel": sel, "dt": dt}


def features(spans: list, sp: dict) -> np.ndarray:
    """Per syllable: duration, peak frequency at start, middle and end, bandwidth and frequency wobble."""
    f, db, sel, dt = sp["f"][sp["sel"]], sp["db"][sp["sel"]], sp["sel"], sp["dt"]
    rows = []
    for s, e in spans:
        seg = db[:, s:e + 1]
        track = f[seg.argmax(axis=0)]
        third = max(1, len(track) // 3)
        bw = np.mean([np.ptp(f[c > c.max() - 10]) for c in seg.T])
        rows.append([(e - s + 1) * dt, track[:third].mean(), track[third:2 * third].mean() if len(track) > 2 else track.mean(), track[-third:].mean(), bw, np.std(np.diff(track)) if len(track) > 2 else 0.0])
    return np.array(rows) if rows else np.zeros((0, 6))


def cluster(feat: np.ndarray, max_types: int = 12) -> list[str]:
    """Group syllables into types: scaled features, joined while the closest pair of groups is near enough."""
    if len(feat) == 0:
        return []
    z = (feat - feat.mean(axis=0)) / (feat.std(axis=0) + 1e-9)
    groups = [[i] for i in range(len(z))]
    cent = [z[i].copy() for i in range(len(z))]
    while len(groups) > 1:
        best, pair = 1e9, None
        for a in range(len(groups)):
            for b in range(a + 1, len(groups)):
                d = np.linalg.norm(cent[a] - cent[b]) * math.sqrt(len(groups[a]) * len(groups[b]) / (len(groups[a]) + len(groups[b])))
                if d < best:
                    best, pair = d, (a, b)
        if best > 2.5 and len(groups) <= max_types:
            break
        a, b = pair
        groups[a] += groups[b]
        cent[a] = z[groups[a]].mean(axis=0)
        del groups[b], cent[b]
    order = sorted(range(len(groups)), key=lambda g: min(groups[g]))
    labels = [""] * len(z)
    for rank, g in enumerate(order):
        for i in groups[g]:
            labels[i] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[rank % 26]
    return labels


def sequence_stats(seq: str) -> dict:
    """The song read as text: repertoire, entropy of types, and how predictable each syllable is from the last."""
    if not seq:
        return {}
    n, c = len(seq), Counter(seq)
    h1 = -sum(v / n * math.log2(v / n) for v in c.values())
    pairs = Counter(zip(seq, seq[1:]))
    firsts = Counter(seq[:-1])
    h_cond = -sum(v / max(n - 1, 1) * math.log2(v / firsts[a]) for (a, _), v in pairs.items()) if n > 1 else 0.0
    return {"syllables": n, "types": len(c), "entropy_bits": round(h1, 3), "max_bits": round(math.log2(len(c)), 3) if len(c) > 1 else 0.0, "conditional_bits": round(h_cond, 3), "repeats": round(sum(a == b for a, b in zip(seq, seq[1:])) / max(n - 1, 1), 3), "transitions": [[f"{a}{b}", v] for (a, b), v in pairs.most_common(8)]}


def analyse(x: np.ndarray, sr: int) -> dict:
    y = resample(x, sr, SR)
    spans, sp = syllables(y, SR)
    labels = cluster(features(spans, sp))
    seq = "".join(labels)
    marks = [(s, e, l) for (s, e), l in zip(spans, labels)]
    return {"duration": round(len(y) / SR, 2), "spectrogram": spectrogram_png(sp["db"], marks, sp["db"].shape[1]), "syllables": [{"start": round(s * sp["dt"], 3), "end": round(e * sp["dt"], 3), "type": l} for (s, e), l in zip(spans, labels)], "sequence": seq, "stats": sequence_stats(seq), "max_freq_hz": SR // 2}


def agreement(true: str, got: str) -> float:
    """How well found types match true types, allowing any renaming: best one-to-one mapping by count."""
    if not true or len(true) != len(got):
        return 0.0
    pairs = Counter(zip(got, true))
    used_g, used_t, hit = set(), set(), 0
    for (g, t), v in pairs.most_common():
        if g not in used_g and t not in used_t:
            used_g.add(g); used_t.add(t); hit += v
    return hit / len(true)
