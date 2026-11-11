"""Hidden messages in images (Lens, Round 78b).

Pixel tests (lossless images only; a JPEG's own compression decides its low bits):
  chi-square attack (Westfeld and Pfitzmann 2000): replacing least significant bits equalises the counts of each
    value pair (2k, 2k+1); p near 1 means the pairs are suspiciously equal (sequential embedding);
  sample pair analysis (Dumitrescu, Wu and Wang 2003): an estimate of the share of pixels whose LSB was replaced,
    from the smaller root of 0.5(|W|+|Z|)p^2 + (2|X|-|P|)p + |Y|-|X| = 0 over horizontally adjacent pairs.
Thresholds are set by controls on clean images (stego_controls.py), not by hand. An image that was ever saved as JPEG
can raise false alarms even as PNG (measured in the controls); no reliable test for that history was found (Round 78b). File checks: metadata and text
chunks, bytes after the image's end marker, other files embedded inside, and the bit planes for the user to view."""
import base64
import io

import cv2
import numpy as np
from PIL import Image
from scipy.stats import chi2

from ..files.carve import embedded


def chi_square(ch: np.ndarray, fraction: float = 1.0) -> float:
    """Probability that the first `fraction` of the channel carries LSB-replaced data (Westfeld-Pfitzmann)."""
    v = ch.ravel()[: max(64, int(ch.size * fraction))]
    h = np.bincount(v, minlength=256).astype(float)
    even, odd = h[0::2], h[1::2]
    exp = (even + odd) / 2
    keep = exp > 4
    if keep.sum() < 2:
        return 0.0
    stat = float((((even - exp) ** 2)[keep] / exp[keep]).sum())
    return float(1 - chi2.cdf(stat, keep.sum() - 1))


FLAT = 0.5  # share of equal neighbouring pairs above which a channel is too flat for sample pair analysis


def spa(ch: np.ndarray) -> float | None:
    """Sample pair analysis: estimated share of pixels with a replaced least significant bit (0 to 1); None if the
    channel is too flat to judge. Like the published method it is unreliable near full embedding (p close to 1)."""
    a = ch.astype(np.int64)
    u, v = a[:, :-1].ravel(), a[:, 1:].ravel()
    P = len(u)
    if (u == v).mean() > FLAT:
        return None
    x = ((v % 2 == 0) & (u < v)) | ((v % 2 == 1) & (u > v))
    y = ((v % 2 == 0) & (u > v)) | ((v % 2 == 1) & (u < v))
    z = u == v
    w = y & (u // 2 == v // 2)
    X, Y, Z, W = x.sum(), y.sum(), z.sum(), w.sum()
    A, B, C = 0.5 * (W + Z), 2 * X - P, Y - X
    if A == 0:
        return float(max(0.0, -C / B)) if B else 0.0
    disc = B * B - 4 * A * C
    if disc < 0:
        return 0.0
    root = min((-B - np.sqrt(disc)) / (2 * A), (-B + np.sqrt(disc)) / (2 * A))
    return float(np.clip(root, 0, 1))  # the smaller root, as published; a negative estimate means none


def channels(img: np.ndarray) -> dict:
    if img.ndim == 2:
        return {"grey": img}
    names = ("blue", "green", "red", "alpha")[: img.shape[2]]
    return {n: img[:, :, i] for i, n in enumerate(names)}


def bit_plane(ch: np.ndarray, bit: int = 0, max_side: int = 480) -> str:
    plane = ((ch >> bit) & 1).astype(np.uint8) * 255
    s = min(1.0, max_side / max(plane.shape))
    plane = cv2.resize(plane, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    ok, enc = cv2.imencode(".png", plane)
    return "data:image/png;base64," + base64.b64encode(enc.tobytes()).decode()


def trailing(data: bytes) -> dict | None:
    """Bytes after a PNG's IEND chunk or a JPEG's last end-of-image marker."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        i = data.find(b"IEND")
        end = i + 8 if i >= 0 else len(data)
    elif data[:2] == b"\xff\xd8":
        i = data.rfind(b"\xff\xd9")
        end = i + 2 if i >= 0 else len(data)
    else:
        return None
    extra = data[end:]
    if len(extra) < 4:
        return None
    text = extra[:400].decode("utf-8", "replace")
    return {"bytes": len(extra), "preview": text if sum(c.isprintable() for c in text) > 0.8 * len(text) else extra[:48].hex()}


def metadata(data: bytes) -> list[dict]:
    out = []
    try:
        im = Image.open(io.BytesIO(data))
        for k, v in (im.info or {}).items():
            if isinstance(v, (str, bytes)) and k not in ("icc_profile", "exif", "dpi"):
                s = v.decode("utf-8", "replace") if isinstance(v, bytes) else v
                out.append({"field": k, "value": s[:300]})
        exif = im.getexif()
        from PIL.ExifTags import TAGS
        for tag, v in exif.items():
            if isinstance(v, (str, bytes)) and str(v).strip():
                out.append({"field": TAGS.get(tag, str(tag)), "value": str(v)[:300]})
    except Exception:
        pass
    return out


def analyse(data: bytes, spa_alarm: float | None = None, chi_alarm: float = 0.95) -> dict:
    """Every check on an image file. Pixel tests run only on lossless formats; the alarm comes from the controls."""
    if spa_alarm is None:
        import json as _json
        from .stego_controls import RESULT
        spa_alarm = _json.loads(RESULT.read_text())["spa_alarm"] if RESULT.exists() else 0.1
    arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_UNCHANGED)
    lossless = data[:8] == b"\x89PNG\r\n\x1a\n" or data[:2] == b"BM" or data[:4] in (b"II*\x00", b"MM\x00*")
    res = {"lossless": lossless, "caveat": "Pixel tests assume the picture was never saved as JPEG; if it was, alarms may be false." if lossless else
           "JPEG pictures are not pixel-tested: compression sets their low bits.", "metadata": metadata(data), "trailing": trailing(data), "embedded": embedded(data)[:20], "channels": {}, "findings": []}
    if arr is None:
        return res
    if arr.dtype != np.uint8:
        arr = (arr / 256).astype(np.uint8)
    for name, ch in channels(arr).items():
        row = {"bit_plane": bit_plane(ch)}
        if lossless:
            est = spa(ch)
            row.update(spa=None if est is None else round(est, 3), chi_first_half=round(chi_square(ch, 0.5), 3), chi_whole=round(chi_square(ch), 3))
            if est is None:
                row["verdict"] = "not judged: too flat to test"
                res["channels"][name] = row
                continue
            if row["spa"] > spa_alarm:
                res["findings"].append({"kind": "lsb", "label": f"{name} channel: about {row['spa']:.0%} of least significant bits look replaced (sample pair analysis)"})
            if row["chi_first_half"] > chi_alarm:
                res["findings"].append({"kind": "lsb", "label": f"{name} channel: value pairs equalised in the first half (chi-square p={row['chi_first_half']:.2f}), as sequential LSB embedding leaves"})
        res["channels"][name] = row
    if res["trailing"]:
        res["findings"].append({"kind": "trailing", "label": f"{res['trailing']['bytes']} bytes after the end of the image", "detail": res["trailing"]["preview"]})
    for e in res["embedded"]:
        res["findings"].append({"kind": "embedded", "label": f"{e.get('kind', 'file')} signature inside at byte {e.get('offset')}"})
    for m in res["metadata"]:
        res["findings"].append({"kind": "metadata", "label": f"metadata '{m['field']}'", "detail": m["value"]})
    return res
