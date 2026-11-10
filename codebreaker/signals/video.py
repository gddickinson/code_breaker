"""Analog video from samples: VGA (separate sync lines) and monochrome composite (sync inside the signal).

Mode timings are the published VESA and CEA values. Times are in pixel clocks for VGA and microseconds for composite."""
import cv2
import numpy as np

# name: (h visible, front porch, sync, back porch, v visible, front porch, sync, back porch, pixel clock, h sync +, v sync +)
MODES = {
    "640x480 @ 60 Hz": (640, 16, 96, 48, 480, 10, 2, 33, 25.175e6, False, False),
    "720x400 @ 70 Hz": (720, 18, 108, 54, 400, 12, 2, 35, 28.322e6, False, True),
    "800x600 @ 60 Hz": (800, 40, 128, 88, 600, 1, 4, 23, 40.0e6, True, True),
    "1024x768 @ 60 Hz": (1024, 24, 136, 160, 768, 3, 6, 29, 65.0e6, False, False),
    "1280x720 @ 60 Hz": (1280, 110, 40, 220, 720, 5, 5, 20, 74.25e6, True, True),
}
# Monochrome NTSC-style composite, progressive 262 lines: levels in volts, times in microseconds
CV = {"line_us": 63.556, "hsync_us": 4.7, "active_start_us": 10.9, "active_us": 52.6, "broad_us": 27.1, "lines": 262, "first_active": 22, "active_lines": 240, "sync": 0.0, "blank": 0.3, "black": 0.339, "white": 1.0}


MIN_REGULAR, MIN_CONFIDENCE = 0.9, 0.3


def vga_signal(rgb: np.ndarray, mode: str, fs_factor: float, noise: float, rnd: np.random.Generator) -> tuple[dict, float]:
    """One frame and a little more, sampled at fs_factor times the pixel clock."""
    hv, hf, hs, hb, vv, vf, vs, vb, pclk, hpos, vpos = MODES[mode]
    ht, vt = hv + hf + hs + hb, vv + vf + vs + vb
    img = cv2.resize(rgb, (hv, vv), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 * 0.7
    grid = np.zeros((vt, ht, 3), np.float32)
    top, left = vs + vb, hs + hb
    grid[top:top + vv, left:left + hv] = img
    hsync = np.zeros((vt, ht), np.uint8)
    hsync[:, :hs] = 1
    vsync = np.zeros((vt, ht), np.uint8)
    vsync[:vs] = 1
    # Start part-way through a frame, as a real capture would, so two frame starts fall inside it.
    frames, skip = 3, (vt // 3) * ht
    flat = np.tile(grid.reshape(-1, 3), (frames, 1))[skip:]
    hsf, vsf = np.tile(hsync.reshape(-1), frames)[skip:], np.tile(vsync.reshape(-1), frames)[skip:]
    pos = (np.arange(int(len(flat) * fs_factor)) / fs_factor).astype(int)
    out = {}
    for i, c in enumerate("RGB"):
        x = cv2.GaussianBlur(flat[:, i].reshape(1, -1), (0, 0), 0.6).reshape(-1)[pos]
        out[c] = (x + rnd.normal(0, noise, len(x))).astype(np.float32)
    out["HSYNC"] = (hsf[pos] if hpos else 1 - hsf[pos]).astype(np.float32)
    out["VSYNC"] = (vsf[pos] if vpos else 1 - vsf[pos]).astype(np.float32)
    return out, pclk * fs_factor


def _pulses(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    """Starts and widths of sync pulses; the active level is whichever is rarer."""
    d = (x > 0.5 * (x.min() + x.max())).astype(np.int8)
    active = 1 if d.mean() < 0.5 else 0
    a = (d == active).astype(np.int8)
    e = np.diff(a)
    starts, ends = np.flatnonzero(e == 1) + 1, np.flatnonzero(e == -1) + 1
    if len(ends) and len(starts) and ends[0] < starts[0]:
        ends = ends[1:]
    n = min(len(starts), len(ends))
    return starts[:n], ends[:n] - starts[:n], active


def vga_decode(ch: dict, fs: float) -> dict:
    """Measure line and frame timing from the sync lines, match a standard mode, then sample the picture."""
    hst, hw, hact = _pulses(ch["HSYNC"])
    vst, vw, vact = _pulses(ch["VSYNC"])
    if len(hst) < 10 or len(vst) < 1:
        return {"ok": False, "reason": "no sync pulses found"}
    gaps = np.diff(hst)
    line = float(np.median(gaps))
    regular = float(np.mean(np.abs(gaps - line) <= 0.02 * line))
    lines_per_frame = float(np.median(np.diff(vst)) / line) if len(vst) > 1 else None
    measured = {"regular_lines": round(regular, 3), "line_khz": round(fs / line / 1e3, 3), "hsync_us": round(float(np.median(hw)) / fs * 1e6, 3), "vsync_lines": round(float(np.median(vw)) / line, 2), "lines_per_frame": round(lines_per_frame, 1) if lines_per_frame else None, "hsync_positive": bool(hact), "vsync_positive": bool(vact)}

    def mismatch(m):
        hv, hf, hs, hb, vv, vf, vs, vb, pclk, hpos, vpos = MODES[m]
        f_line = pclk / (hv + hf + hs + hb)
        err = abs(np.log(fs / line / f_line)) * 50 + abs(np.log(measured["hsync_us"] / (hs / pclk * 1e6))) * 5
        if lines_per_frame:
            err += abs(lines_per_frame - (vv + vf + vs + vb)) / 10
        return err + (hpos != bool(hact)) * 0.5 + (vpos != bool(vact)) * 0.5
    mode = min(MODES, key=mismatch)
    hv, hf, hs, hb, vv, vf, vs, vb, pclk, *_ = MODES[mode]
    spp = fs / pclk
    v0 = vst[0]
    rows = []
    for k in range(vv):
        ln = v0 + (vs + vb + k) * line
        idx = np.searchsorted(hst, ln - line / 2)
        if idx >= len(hst):
            break
        s = hst[idx] + (hs + hb) * spp
        pos = s + (np.arange(hv) + 0.5) * spp
        pos = pos[pos < len(ch["R"]) - 1].astype(int)
        if len(pos) < hv:
            break
        rows.append(np.stack([ch[c][pos] for c in "RGB"], axis=1))
    img = np.clip(np.array(rows) / 0.7 * 255, 0, 255).astype(np.uint8) if rows else None
    conf = float(np.exp(-mismatch(mode)))
    # Success needs regular line syncs and a standard mode that fits; otherwise say what was measured.
    matched = regular >= MIN_REGULAR and conf >= MIN_CONFIDENCE
    reason = "" if matched else ("sync pulses are irregular, so this is probably not video" if regular < MIN_REGULAR else f"no standard mode matches; closest is {mode}")
    return {"ok": bool(matched and img is not None and len(rows) == vv), "mode": mode if matched else None, "closest": mode, "confidence": round(conf, 3), "measured": measured, "reason": reason, "image": img if matched else None}


def composite_signal(gray: np.ndarray, fs: float, noise: float, rnd: np.random.Generator) -> np.ndarray:
    """Two progressive frames: three lines of broad vertical pulses, blank lines, then 240 lines of picture."""
    c, us = CV, fs / 1e6
    n_line = int(round(c["line_us"] * us))
    img = cv2.resize(gray, (int(c["active_us"] * us), c["active_lines"]), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    frame = np.full((c["lines"], n_line), c["blank"], np.float32)
    for ln in range(c["lines"]):
        if ln < 3:
            half = n_line // 2
            for h0 in (0, half):
                frame[ln, h0:h0 + int(c["broad_us"] * us)] = c["sync"]
            continue
        frame[ln, :int(c["hsync_us"] * us)] = c["sync"]
        k = ln - c["first_active"]
        if 0 <= k < c["active_lines"]:
            a = int(c["active_start_us"] * us)
            frame[ln, a:a + img.shape[1]] = c["black"] + img[k] * (c["white"] - c["black"])
    x = np.tile(frame.reshape(-1), 2)
    return (cv2.GaussianBlur(x.reshape(1, -1), (0, 0), max(0.5, us / 8)).reshape(-1) + rnd.normal(0, noise, len(x))).astype(np.float32)


def composite_decode(x: np.ndarray, fs: float, width: int = 480) -> dict:
    """Sync is below the blanking level. Short pulses are line syncs, broad ones mark the start of a frame."""
    c, us = CV, fs / 1e6
    thr = 0.5 * (np.percentile(x, 1) + c["blank"])
    low = (x < thr).astype(np.int8)
    e = np.diff(low)
    starts, ends = np.flatnonzero(e == 1) + 1, np.flatnonzero(e == -1) + 1
    if len(ends) and len(starts) and ends[0] < starts[0]:
        ends = ends[1:]
    n = min(len(starts), len(ends))
    starts, widths = starts[:n], (ends[:n] - starts[:n]) / us
    short = starts[(widths > 2) & (widths < 8)]
    broad = starts[widths > 15]
    if len(short) < 20 or not len(broad):
        return {"ok": False, "reason": "no composite sync found"}
    line = float(np.median(np.diff(short)))
    after = short[short > broad[0]]
    groups = np.flatnonzero(np.diff(broad) > 2 * line)
    first_broad = broad[0]
    line0 = first_broad + 3 * line
    rows = []
    for k in range(c["active_lines"]):
        ln = line0 + (c["first_active"] - 3 + k) * line
        idx = np.searchsorted(after, ln - line / 2)
        if idx >= len(after):
            break
        s = after[idx] + c["active_start_us"] * us
        pos = (s + (np.arange(width) + 0.5) * c["active_us"] * us / width).astype(int)
        if pos[-1] >= len(x):
            break
        rows.append(x[pos])
    img = np.clip((np.array(rows) - c["black"]) / (c["white"] - c["black"]) * 255, 0, 255).astype(np.uint8) if rows else None
    return {"ok": img is not None and len(rows) == c["active_lines"], "measured": {"line_khz": round(fs / line / 1e3, 3), "hsync_us": round(float(np.median(widths[(widths > 2) & (widths < 8)])), 3), "broad_pulses": int(len(broad)), "frames": int(len(groups) + 1)}, "image": img}
