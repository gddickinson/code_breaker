"""Read a sudoku grid from a photo: find the board, flatten it, and read each cell."""
import base64
import re
import subprocess

import cv2
import numpy as np


def decode_image(data_url: str) -> np.ndarray:
    raw = base64.b64decode(data_url.split(",", 1)[-1])
    img = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("That file could not be read as an image.")
    return img


def find_board(gray: np.ndarray, size: int = 900) -> np.ndarray:
    """Find the largest square-like outline and warp it to a flat square."""
    scale = 1000 / max(gray.shape)
    small = cv2.resize(gray, None, fx=scale, fy=scale) if scale < 1 else gray.copy()
    scale = min(scale, 1.0)
    thr = cv2.adaptiveThreshold(cv2.GaussianBlur(small, (5, 5), 0), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 7)
    contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area = small.shape[0] * small.shape[1]
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
        approx = cv2.approxPolyDP(c, 0.03 * cv2.arcLength(c, True), True)
        if len(approx) == 4 and cv2.contourArea(approx) > 0.12 * area:
            pts = approx.reshape(4, 2).astype(np.float32) / scale
            s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
            src = np.array([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]], dtype=np.float32)
            dst = np.array([[0, 0], [size - 1, 0], [size - 1, size - 1], [0, size - 1]], dtype=np.float32)
            return cv2.warpPerspective(gray, cv2.getPerspectiveTransform(src, dst), (size, size))
    raise ValueError("No sudoku grid was found. Try a straighter, closer photo.")


def read_digit(cell: np.ndarray) -> int:
    """Return 0 for an empty cell, otherwise the digit Tesseract reads."""
    h, w = cell.shape
    inner = cell[int(h * 0.16):int(h * 0.84), int(w * 0.16):int(w * 0.84)]
    bw = cv2.threshold(inner, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    if float(inner.max()) - float(inner.min()) < 50 or (bw > 0).mean() < 0.03:
        return 0
    points = cv2.findNonZero(bw)
    x, y, wd, ht = cv2.boundingRect(points)
    glyph = 255 - bw[y:y + ht, x:x + wd]
    glyph = cv2.copyMakeBorder(cv2.resize(glyph, None, fx=1.6, fy=1.6), 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255)
    ok, buf = cv2.imencode(".png", glyph)
    for psm in ("10", "8", "13", "7"):  # Tesseract sometimes returns nothing for one layout mode
        r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", psm, "-c", "tessedit_char_whitelist=123456789"], input=buf.tobytes(), capture_output=True, timeout=20)
        digits = re.findall(r"[1-9]", r.stdout.decode("utf-8", "ignore"))
        if digits:
            return int(digits[0])
    return 0


def read_grid(gray: np.ndarray) -> list[int]:
    board = find_board(gray)
    step = board.shape[0] / 9
    return [read_digit(board[int(r * step) + 6:int((r + 1) * step) - 6, int(c * step) + 6:int((c + 1) * step) - 6]) for r in range(9) for c in range(9)]
