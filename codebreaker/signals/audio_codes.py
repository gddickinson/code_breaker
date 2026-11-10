"""Codes carried as sound: DTMF touch tones and Morse code, generated and decoded from audio samples."""
import numpy as np

SR = 8000
DTMF_ROWS, DTMF_COLS = [697, 770, 852, 941], [1209, 1336, 1477, 1633]
DTMF_KEYS = ["123A", "456B", "789C", "*0#D"]
MORSE = {"A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.", ".": ".-.-.-", ",": "--..--", "?": "..--..", "/": "-..-.", "=": "-...-"}
FROM_MORSE = {v: k for k, v in MORSE.items()}


def goertzel(x: np.ndarray, f: float, sr: int = SR) -> float:
    k = 2 * np.cos(2 * np.pi * f / sr)
    s1 = s2 = 0.0
    for v in x:
        s1, s2 = v + k * s1 - s2, s1
    return s1 * s1 + s2 * s2 - k * s1 * s2


def dtmf_tones(keys: str, rnd: np.random.Generator, on: float = 0.09, off: float = 0.07, noise: float = 0.05) -> np.ndarray:
    parts = [np.zeros(int(0.1 * SR))]
    t = np.arange(int(on * SR)) / SR
    for k in keys:
        r = next(i for i, row in enumerate(DTMF_KEYS) if k in row)
        c = DTMF_KEYS[r].index(k)
        parts += [0.4 * np.sin(2 * np.pi * DTMF_ROWS[r] * t) + 0.5 * np.sin(2 * np.pi * DTMF_COLS[c] * t), np.zeros(int(off * SR))]
    x = np.concatenate(parts)
    return (x + rnd.normal(0, noise, len(x))).astype(np.float32)


def dtmf_decode(x: np.ndarray, sr: int = SR) -> dict:
    """20 ms frames; a key needs one clear row tone and one clear column tone, held for two frames."""
    n = int(0.02 * sr)
    keys, prev, held = [], "", 0
    for i in range(0, len(x) - n, n):
        f = x[i:i + n]
        energy = float(np.dot(f, f))
        r = [goertzel(f, q, sr) for q in DTMF_ROWS]
        c = [goertzel(f, q, sr) for q in DTMF_COLS]
        ri, ci = int(np.argmax(r)), int(np.argmax(c))
        rs, cs = sorted(r), sorted(c)
        ok = r[ri] > 4 * rs[-2] and c[ci] > 4 * cs[-2] and r[ri] + c[ci] > 0.3 * energy * n / 2 and 0.1 < c[ci] / (r[ri] + 1e-12) < 10
        k = DTMF_KEYS[ri][ci] if ok else ""
        held = held + 1 if k and k == prev else (1 if k else 0)
        if k and held == 2:
            keys.append(k)
        prev = k
    return {"code": "DTMF", "text": "".join(keys), "symbols": len(keys)}


def morse_audio(text: str, wpm: float, rnd: np.random.Generator, tone: float = 700, noise: float = 0.05) -> np.ndarray:
    unit = 1.2 / wpm
    seq = []
    for w, word in enumerate(text.upper().split()):
        if w:
            seq.append((0, 7))
        for i, ch in enumerate(word):
            if i:
                seq.append((0, 3))
            for j, sym in enumerate(MORSE.get(ch, "")):
                if j:
                    seq.append((0, 1))
                seq.append((1, 1 if sym == "." else 3))
    parts = [np.zeros(int(0.2 * SR))]
    for on, units in seq:
        k = int(units * unit * SR)
        parts.append(0.6 * np.sin(2 * np.pi * tone * np.arange(k) / SR) if on else np.zeros(k))
    parts.append(np.zeros(int(0.2 * SR)))
    x = np.concatenate(parts)
    return (x + rnd.normal(0, noise, len(x))).astype(np.float32)


def morse_decode(x: np.ndarray, sr: int = SR) -> dict:
    """Envelope, threshold, then classify mark and gap lengths against the shortest common unit."""
    win = max(8, int(sr * 0.005))
    env = np.convolve(np.abs(x), np.ones(win) / win, "same")
    # The noise floor is taken low in the distribution, since a busy message can be tone most of the time.
    lo, hi = np.percentile(env, 5), np.percentile(env, 99)
    if hi < 3 * max(lo, 1e-6):
        return {"code": "Morse", "text": "", "symbols": 0}
    # Hysteresis: switch on above 50% and off below 30%, so noise near the threshold cannot chatter.
    on_t, off_t, state, on = lo + 0.5 * (hi - lo), lo + 0.3 * (hi - lo), False, np.zeros(len(env), bool)
    for i, v in enumerate(env):
        state = v > on_t if not state else v > off_t
        on[i] = state
    edges = np.flatnonzero(np.diff(on.astype(np.int8))) + 1
    if len(edges) < 2:
        return {"code": "Morse", "text": "", "symbols": 0}
    bounds = np.concatenate([[0], edges, [len(on)]])
    runs = [[bool(on[a]), (b - a) / sr] for a, b in zip(bounds[:-1], bounds[1:])]
    marks = np.array([d for v, d in runs if v])
    if len(marks) < 2:
        return {"code": "Morse", "text": "", "symbols": 0}
    unit = float(np.median(marks[marks <= np.median(marks)]))
    # Merge any run shorter than a third of a unit into its neighbours: it is noise, not a symbol.
    merged = []
    for v, d in runs:
        if merged and (d < unit / 3 or merged[-1][0] == v):
            merged[-1][1] += d
        else:
            merged.append([v, d])
    runs = merged
    marks = np.array([d for v, d in runs if v])
    unit = float(np.median(marks[marks <= np.median(marks)]))
    out, cur = [], ""
    for v, d in runs[1:-1] if not runs[0][0] else runs:
        u = d / unit
        if v:
            cur += "." if u < 2 else "-"
        elif u > 5:
            out.append(FROM_MORSE.get(cur, "?") + " ") if cur else None
            cur = ""
        elif u > 2:
            if cur:
                out.append(FROM_MORSE.get(cur, "?"))
            cur = ""
    if cur:
        out.append(FROM_MORSE.get(cur, "?"))
    text = "".join(out).strip()
    return {"code": "Morse", "text": text, "symbols": len(text.replace(" ", "")), "wpm": round(1.2 / unit, 1), "unknown": text.count("?")}
