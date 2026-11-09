"""Audio in: any format libsndfile reads (WAV, FLAC, OGG, MP3), as mono float32."""
import io

import numpy as np
from scipy.signal import resample_poly

MAX_SECONDS = 120


def decode(data: bytes, max_seconds: float = MAX_SECONDS) -> tuple[np.ndarray, int]:
    import soundfile as sf

    x, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=True, frames=-1)
    x = x[: int(max_seconds * sr)].mean(axis=1)
    return x.astype(np.float32), int(sr)


def load(path: str, max_seconds: float = MAX_SECONDS) -> tuple[np.ndarray, int]:
    with open(path, "rb") as f:
        return decode(f.read(), max_seconds)


def resample(x: np.ndarray, sr: int, target: int) -> np.ndarray:
    if sr == target:
        return x
    g = np.gcd(sr, target)
    return resample_poly(x, target // g, sr // g).astype(np.float32)


def wav_bytes(x: np.ndarray, sr: int) -> bytes:
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, x, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()
