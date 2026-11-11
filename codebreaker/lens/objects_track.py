"""Tracking an object across live frames (Round 90b): normalised template matching at three scales in a window around
the last box. The template is renewed only on strong matches (so it follows slow changes without drifting onto the
background), and the object is reported lost when the best match falls below LOST. OpenCV's CSRT tracker is not in
this build; controls in objects_eval.py (a moving pasted object, and frames with the object removed for the null)."""
import cv2
import numpy as np

LOST, RENEW = 0.55, 0.85
_SESSIONS: dict[str, "Tracker"] = {}


def _gray(img: np.ndarray) -> np.ndarray:
    return img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


class Tracker:
    def __init__(self, frame: np.ndarray, box: list[int]):
        g = _gray(frame)
        x, y, w, h = [int(v) for v in box]
        x, y = max(0, x), max(0, y)
        self.box = [x, y, max(8, min(w, g.shape[1] - x)), max(8, min(h, g.shape[0] - y))]
        self.template = g[self.box[1]:self.box[1] + self.box[3], self.box[0]:self.box[0] + self.box[2]].copy()
        self.lost = False

    def update(self, frame: np.ndarray) -> dict:
        g = _gray(frame)
        H, W = g.shape
        x, y, w, h = self.box
        best = (-1.0, None)
        for s in (0.92, 1.0, 1.08):
            tw, th = max(8, int(w * s)), max(8, int(h * s))
            t = cv2.resize(self.template, (tw, th))
            x0, y0 = max(0, x - w // 2), max(0, y - h // 2)
            x1, y1 = min(W, x + w + w // 2), min(H, y + h + h // 2)
            win = g[y0:y1, x0:x1]
            if win.shape[0] < th or win.shape[1] < tw:
                continue
            r = cv2.matchTemplate(win, t, cv2.TM_CCOEFF_NORMED)
            _, v, _, loc = cv2.minMaxLoc(r)
            if v > best[0]:
                best = (v, [x0 + loc[0], y0 + loc[1], tw, th])
        score, box = best
        self.lost = box is None or score < LOST
        if not self.lost:
            self.box = box
            if score >= RENEW:
                self.template = g[box[1]:box[1] + box[3], box[0]:box[0] + box[2]].copy()
        return {"box": self.box, "score": round(float(score), 3), "lost": self.lost}


def start(session: str, frame: np.ndarray, box: list[int]) -> dict:
    _SESSIONS[session] = Tracker(frame, box)
    return {"box": _SESSIONS[session].box, "lost": False}


def step(session: str, frame: np.ndarray) -> dict | None:
    t = _SESSIONS.get(session)
    return t.update(frame) if t else None
