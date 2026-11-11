"""Live sessions for the Lens (user's design, Round 78b): readings compiled across frames, motion and rotation
followed, hard lines handed to the thorough analyser, and results shared with captured photos.

Each frame is aligned to the session's reference frame by ORB features and a RANSAC homography, so text lines are
tracked in reference coordinates whatever the object does (moved, rotated, tilted). A line collects every frame's
reading; the shown text is the reading with the most confidence-weighted votes, so a misreading in one frame (glare,
blur, a bad angle) is outvoted by the others. A line that keeps disagreeing or stays unsure keeps its sharpest view,
and a background worker reads that view with the thorough analyser (ocr_deep.photo_words); its reading joins the vote
with extra weight. A captured photo aligned to the session adds its readings the same way, and the session's
consensus is offered back to the photo analyser. Sessions expire after two idle minutes."""
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from . import ocr

SESSIONS: dict[str, "Session"] = {}
IDLE = 120
DEEP_WEIGHT = 3.0  # a thorough reading counts as three confident frames
_POOL = ThreadPoolExecutor(1)  # one thorough reading at a time, so the live view stays responsive
_ORB = cv2.ORB_create(1500)


def _small(gray: np.ndarray, side: int = 640) -> tuple[np.ndarray, float]:
    s = min(1.0, side / max(gray.shape))
    return (cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else gray), s


def _rect(q: np.ndarray) -> tuple[float, float, float, float]:
    x0, y0 = q.min(0)
    x1, y1 = q.max(0)
    return float(x0), float(y0), float(x1 - x0), float(y1 - y0)


def _iou(a, b) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / max(1e-6, a[2] * a[3] + b[2] * b[3] - i)


def sharpness(img: np.ndarray) -> float:
    return float(cv2.Laplacian(img, cv2.CV_64F).var())


class Track:
    def __init__(self, quad: np.ndarray):
        self.quad, self.votes, self.seen, self.last = quad, Counter(), 0, 0
        self.best_view, self.best_sharp, self.deep, self.deep_pending, self.frames_conf = None, -1.0, None, False, []

    def text(self) -> str:
        return self.votes.most_common(1)[0][0] if self.votes else ""

    def agreement(self) -> float:
        total = sum(self.votes.values())
        return self.votes.most_common(1)[0][1] / total if total else 0.0

    def status(self) -> str:
        if self.deep and self.deep == self.text():
            return "confirmed by the thorough analyser"
        if self.seen >= 3 and self.agreement() >= 0.6:
            return "agreed over frames"
        return "reading"


class Session:
    def __init__(self):
        self.id, self.lock = uuid.uuid4().hex[:12], threading.Lock()
        self.ref_kp = self.ref_des = None
        self.ref_scale, self.tracks, self.frame, self.touched, self.resets = 1.0, [], 0, time.time(), 0

    def _features(self, gray):
        small, s = _small(gray)
        kp, des = _ORB.detectAndCompute(small, None)
        return kp, des, s

    def align(self, gray: np.ndarray) -> np.ndarray | None:
        """Homography from this frame's pixels to the reference frame's pixels; None if the view no longer matches."""
        kp, des, s = self._features(gray)
        if self.ref_des is None or des is None or len(kp) < 20:
            return None
        m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(des, self.ref_des)
        if len(m) < 20:
            return None
        src = np.float32([kp[x.queryIdx].pt for x in m]) / s
        dst = np.float32([self.ref_kp[x.trainIdx].pt for x in m]) / self.ref_scale
        H, inl = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        return H if H is not None and inl is not None and inl.sum() >= 15 else None

    def reset(self, gray: np.ndarray) -> np.ndarray:
        self.ref_kp, self.ref_des, self.ref_scale = self._features(gray)
        self.tracks, self.resets = [], self.resets + 1
        return np.eye(3)

    def add(self, gray: np.ndarray, lines: list[tuple], H: np.ndarray, weight: float = 1.0, deep: bool = False) -> None:
        """lines: (quad in this picture's pixels, text, confidence 0-1)."""
        for quad, txt, conf in lines:
            if not txt.strip():
                continue
            q = cv2.perspectiveTransform(np.float32(quad).reshape(-1, 1, 2), H).reshape(-1, 2)
            r = _rect(q)
            tr = max(self.tracks, key=lambda t: _iou(_rect(t.quad), r), default=None)
            if tr is None or _iou(_rect(tr.quad), r) < 0.3:
                tr = Track(q)
                self.tracks.append(tr)
            tr.quad = 0.7 * tr.quad + 0.3 * q
            tr.votes[txt] += weight * conf
            if deep:
                tr.deep = txt
            else:
                tr.seen, tr.last = tr.seen + 1, self.frame
                tr.frames_conf.append(conf)
                view = _rectify(gray, np.float32(quad))
                if view is not None and sharpness(view) > tr.best_sharp:
                    tr.best_view, tr.best_sharp = view, sharpness(view)

    def needs_help(self) -> list[Track]:
        return [t for t in self.tracks if t.seen >= 3 and not t.deep and not t.deep_pending and t.best_view is not None
                and (t.agreement() < 0.6 or float(np.mean(t.frames_conf[-5:])) < 0.85)]


def _rectify(gray: np.ndarray, quad: np.ndarray) -> np.ndarray | None:
    """The line straightened out of the picture (handles rotated or tilted lines), with a small margin."""
    w = int(max(np.linalg.norm(quad[1] - quad[0]), np.linalg.norm(quad[2] - quad[3])))
    h = int(max(np.linalg.norm(quad[3] - quad[0]), np.linalg.norm(quad[2] - quad[1])))
    if w < 8 or h < 6:
        return None
    pad = max(2, h // 4)
    dst = np.float32([[pad, pad], [pad + w, pad], [pad + w, pad + h], [pad, pad + h]])
    return cv2.warpPerspective(gray, cv2.getPerspectiveTransform(np.float32(quad), dst), (w + 2 * pad, h + 2 * pad), borderValue=int(np.median(gray)))


def _deep(session: Session, track: Track) -> None:
    from .ocr_deep import photo_words

    try:
        view = cv2.resize(track.best_view, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        ws = [w for w in photo_words(view) if ocr.readable(w)]
        txt = " ".join(w["text"] for w in sorted(ws, key=lambda w: w["box"][0]))
        with session.lock:
            if txt:
                track.votes[txt] += DEEP_WEIGHT
                track.deep = txt
    finally:
        track.deep_pending = False


def rapid_lines(gray: np.ndarray) -> list[tuple]:
    eng = ocr.rapid()
    if eng is None:
        return []
    res, _ = eng(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
    return [(np.float32(box), txt, float(conf)) for box, txt, conf in res or []]


def get(sid: str | None) -> Session:
    now = time.time()
    for k in [k for k, s in SESSIONS.items() if now - s.touched > IDLE]:
        SESSIONS.pop(k, None)
    s = SESSIONS.get(sid or "")
    if s is None:
        s = Session()
        SESSIONS[s.id] = s
    s.touched = now
    return s


def coach(gray: np.ndarray, lines: list[tuple], session: "Session") -> list[str]:
    """Instructions for the user, from measurements of this frame and the session (no guessing): blur (Laplacian
    variance), glare (share of near-white pixels), text height, light level, and lines still being read."""
    tips = []
    if sharpness(gray) < 40:
        tips.append("Hold still: the picture is blurred.")
    if (gray >= 250).mean() > 0.04:
        tips.append("Tilt the object a little: glare is hiding part of it.")
    if gray.mean() < 60:
        tips.append("More light would help.")
    hs = [float(np.linalg.norm(q[3] - q[0])) for q, _, _ in lines]
    if hs and np.median(hs) < 14:
        tips.append("Move closer: the text is small.")
    if not lines:
        tips.append("No text found yet: point the camera at the writing.")
    if any(t.deep_pending for t in session.tracks):
        tips.append("Keep it in view: taking a closer look at a hard line.")
    elif session.tracks and all(t.status() != "reading" for t in session.tracks if session.frame - t.last <= 4):
        tips.append("Got it: every line in view agrees across frames. Capture a photo for the full analysis.")
    return tips


def live_frame(sid: str | None, gray: np.ndarray) -> dict:
    """One live frame: align, vote, maybe hand a line to the thorough analyser; lines in this frame's pixels."""
    s = get(sid)
    lines = rapid_lines(gray)
    with s.lock:
        s.frame += 1
        H = s.align(gray)
        if H is None:
            H = s.reset(gray)
        s.add(gray, lines, H)
        for t in s.needs_help()[:1]:
            t.deep_pending = True
            _POOL.submit(_deep, s, t)
        Hinv = np.linalg.inv(H)
        out = []
        for t in s.tracks:
            if s.frame - t.last > 4 and not t.deep:
                continue
            q = cv2.perspectiveTransform(t.quad.reshape(-1, 1, 2), Hinv).reshape(-1, 2)
            x, y, w, h = _rect(q)
            out.append({"text": t.text(), "box": [round(x), round(y), round(w), round(h)], "quad": q.round(1).tolist(), "seen": t.seen,
                        "agreement": round(t.agreement(), 2), "status": t.status(), "stale": s.frame - t.last})
        tips = coach(gray, lines, s)
    return {"session": s.id, "frame": s.frame, "resets": s.resets, "lines": out, "pending": sum(t.deep_pending for t in s.tracks), "tips": tips}


def share_photo(sid: str | None, gray: np.ndarray, words: list[dict]) -> list[tuple]:
    """A captured photo and its session: the photo's lines join the session's vote as thorough readings, and the
    session's consensus lines (in the photo's pixels) come back as extra candidates for the photo analyser."""
    if not sid or sid not in SESSIONS:
        return []
    s = SESSIONS[sid]
    with s.lock:
        H = s.align(gray)
        if H is None:
            return []
        lines = []
        for line in ocr.group_lines([w for w in words if ocr.readable(w)]):
            x0 = min(w["box"][0] for w in line)
            y0 = min(w["box"][1] for w in line)
            x1 = max(w["box"][0] + w["box"][2] for w in line)
            y1 = max(w["box"][1] + w["box"][3] for w in line)
            lines.append((np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), " ".join(w["text"] for w in line), 1.0))
        s.add(gray, lines, H, DEEP_WEIGHT, deep=True)
        Hinv = np.linalg.inv(H)
        return [(_rect(cv2.perspectiveTransform(t.quad.reshape(-1, 1, 2), Hinv).reshape(-1, 2)), t.text())
                for t in s.tracks if t.seen >= 2]
