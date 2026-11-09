"""What the Signal Workbench page calls: detection with previews, manual renders, generated examples, the control table."""
import base64
import json

import cv2

from ..languages import ROOT
from .raw_detect import control, detect, example
from .raw_formats import FORMATS, image

RESULT = ROOT / "data/results/signals_raw_control.json"
MAX_BYTES = 16 * 1024 * 1024
EXAMPLES = {"kinect11": ("Kinect depth frame, 11-bit packed, 640x480", 640, 480), "yuyv": ("USB webcam frame, YUYV 4:2:2, 640x480", 640, 480), "raw10": ("Camera sensor, RAW10 packed, 752x480", 752, 480), "rgb565": ("Microcontroller display buffer, RGB565, 320x240", 320, 240), "bayer": ("Colour sensor mosaic, Bayer RGGB, 640x480", 640, 480), "gray16le": ("16-bit sensor (12-bit values), little-endian, 320x240", 320, 240)}


def _bytes(b64: str) -> bytes:
    data = base64.b64decode(b64.split(",", 1)[-1], validate=False)
    if not data:
        raise ValueError("No data was received.")
    if len(data) > MAX_BYTES:
        raise ValueError("That file is too large here (16 MB limit). Cut out one frame first.")
    return data


def png(data: bytes, fmt: str, width: int, offset: int = 0, bayer: str | None = None) -> str:
    if width < 2:
        raise ValueError("The width must be at least 2.")
    real = "gray8" if fmt == "bayer" else fmt
    rgb = image(data, real, width, offset, bayer or ("RGGB" if fmt == "bayer" else None))
    if rgb.size == 0:
        raise ValueError("Not enough data for one row at this width.")
    if rgb.shape[0] > 2000:
        rgb = rgb[:2000]
    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode()


def reliability() -> dict:
    """Per-format success in the generated control, so the page can say how far to trust a guess."""
    if not RESULT.exists():
        RESULT.write_text(json.dumps(control(), indent=1))
    rows = json.loads(RESULT.read_text())["rows"]
    out = {}
    for r in rows:
        k = r["kind"]
        n, ok = out.get(k, (0, 0))
        out[k] = (n + 1, ok + (r["format_ok"] and r["width_ok"]))
    return {k: {"cases": n, "correct": ok} for k, (n, ok) in out.items()}


def analyse(b64: str) -> dict:
    data = _bytes(b64)
    d = detect(data)
    best = d["best"]
    d["preview"] = png(data, best["format"], best["width"]) if best else None
    d["reliability"] = reliability()
    d["formats"] = {k: v["name"] for k, v in FORMATS.items()} | {"bayer": "Bayer colour mosaic, 8-bit"}
    return d


def render(b64: str, fmt: str, width: int, offset: int = 0, bayer: str | None = None) -> dict:
    return {"preview": png(_bytes(b64), fmt, width, offset, bayer)}


def make_example(kind: str) -> dict:
    title, w, h = EXAMPLES[kind]
    data, truth = example(kind, w, h, 7)
    return {"title": title, "data": base64.b64encode(data).decode(), "bytes": len(data), "truth": truth}
