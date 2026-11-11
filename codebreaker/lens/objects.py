"""Object understanding for the Lens (Round 90b): what the object is and where it is.

With a local vision model (Ollama, ai_local.py): one call returns a name, a one-line description and a box. The
picture is first resized to about 802,816 pixels in multiples of 28, the grid the model works on, so its box comes
back in known pixels (checked on drawn rectangles: within 2-4 pixels at 512 to 1920 pixels wide). Without one: the
classical fallback, MobileNetV2 (ONNX model zoo, ImageNet, Apache-2.0; data/models/objects, not committed) for the top
labels, and GrabCut started from a central rectangle for the outline. The mode that ran is always reported.
Controls in objects_eval.py; tracking in objects_track.py."""
import json
import re
from functools import lru_cache

import cv2
import numpy as np

from .. import ai_local
from ..languages import ROOT

DIR = ROOT / "data/models/objects"
AREA = 802816  # 1024 patches of 28 x 28
PROMPT = ('Identify the main object in this picture. Answer only with JSON: {"label": "a short noun", "description": "one short sentence", '
          '"bbox_2d": [x1, y1, x2, y2]}. If there is no recognisable object, use "label": "none".')


def model_grid(img: np.ndarray) -> tuple[np.ndarray, float, float]:
    h, w = img.shape[:2]
    s = (AREA / (w * h)) ** 0.5
    W, H = max(28, round(w * s / 28) * 28), max(28, round(h * s / 28) * 28)
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC), W / w, H / h


def _parse(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return d[0] if isinstance(d, list) and d else d if isinstance(d, dict) else None


def identify_ai(img: np.ndarray, model: str | None = None) -> dict | None:
    model = model or ai_local.status()["vision"]
    if not model:
        return None
    g, sx, sy = model_grid(img)
    r = ai_local.generate(model, PROMPT, [cv2.imencode(".png", g)[1].tobytes()], num_predict=120)
    if r is None:
        return None
    d = _parse(r["text"]) or {"label": r["text"].strip()[:40]}
    box = None
    b = d.get("bbox_2d")
    if isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b):
        x1, y1, x2, y2 = b[0] / sx, b[1] / sy, b[2] / sx, b[3] / sy
        box = [int(x1), int(y1), int(max(1, x2 - x1)), int(max(1, y2 - y1))]
    label = str(d.get("label", "")).strip()
    return {"mode": f"local {model}", "label": "" if label.lower() == "none" else label, "description": str(d.get("description", "")),
            "box": box, "seconds": r["seconds"]}


@lru_cache(maxsize=1)
def _net():
    path = DIR / "mobilenetv2-12.onnx"
    if not path.exists():
        return None, []
    labels = [l.split(" ", 1)[1] for l in (DIR / "synset.txt").read_text().splitlines()]
    return cv2.dnn.readNetFromONNX(str(path)), labels


def classify(img: np.ndarray, top: int = 5) -> list[dict]:
    net, labels = _net()
    if net is None:
        return []
    rgb = cv2.cvtColor(img if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR), cv2.COLOR_BGR2RGB)
    x = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    net.setInput(x.transpose(2, 0, 1)[None])
    z = net.forward().ravel()
    p = np.exp(z - z.max())
    p /= p.sum()
    return [{"label": labels[i].split(",")[0], "names": labels[i], "p": round(float(p[i]), 3)} for i in np.argsort(-p)[:top]]


def outline(img: np.ndarray, margin: float = 0.08) -> list[int] | None:
    """GrabCut from a central rectangle; the box of the largest foreground region."""
    bgr = img if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    h, w = bgr.shape[:2]
    s = min(1.0, 400 / max(h, w))
    small = cv2.resize(bgr, (max(8, int(w * s)), max(8, int(h * s))))
    sh, sw = small.shape[:2]
    mask = np.zeros((sh, sw), np.uint8)
    rect = (int(sw * margin), int(sh * margin), int(sw * (1 - 2 * margin)), int(sh * (1 - 2 * margin)))
    try:
        cv2.grabCut(small, mask, rect, np.zeros((1, 65)), np.zeros((1, 65)), 4, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return None
    fg = ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(fg)
    if n < 2:
        return None
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, bw, bh = stats[i, :4]
    return [int(x / s), int(y / s), int(bw / s), int(bh / s)]


def identify_classical(img: np.ndarray) -> dict:
    labels = classify(img)
    if not labels:
        return {"mode": "own algorithms only", "label": "", "description": "", "box": outline(img), "note": "No classifier on disk (data/models/objects)."}
    return {"mode": "classical: MobileNetV2 (ImageNet) and GrabCut", "label": labels[0]["label"], "candidates": labels,
            "description": f"ImageNet's closest classes: {', '.join(l['label'] for l in labels[:3])}.", "box": outline(img)}


def understand(img: np.ndarray, use_ai: bool = True) -> dict:
    r = identify_ai(img) if use_ai else None
    return r if r is not None else identify_classical(img)
