"""Infrared remote codes as seen on an IR receiver's output (low while the carrier is present): NEC and Philips RC5."""
import numpy as np

from .logic_decode import debounce, edges
from .logic_synth import Wave

NEC_UNIT = 562.5e-6
RC5_HALF = 889e-6


def nec(address: int, command: int, repeats: int = 0) -> Wave:
    """9 ms burst, 4.5 ms space, 32 bits LSB first: address, its inverse, command, its inverse. Then repeat codes."""
    w = Wave(["IR"], {"IR": 1})
    w.wait(0.005)
    w.set(IR=0)
    w.wait(16 * NEC_UNIT)
    w.set(IR=1)
    w.wait(8 * NEC_UNIT)
    for byte in (address, address ^ 0xFF, command, command ^ 0xFF):
        for i in range(8):
            w.set(IR=0)
            w.wait(NEC_UNIT)
            w.set(IR=1)
            w.wait(3 * NEC_UNIT if (byte >> i) & 1 else NEC_UNIT)
    w.set(IR=0)
    w.wait(NEC_UNIT)
    w.set(IR=1)
    for _ in range(repeats):
        w.wait(0.040)
        w.set(IR=0)
        w.wait(16 * NEC_UNIT)
        w.set(IR=1)
        w.wait(4 * NEC_UNIT)
        w.set(IR=0)
        w.wait(NEC_UNIT)
        w.set(IR=1)
    w.wait(0.01)
    return w


def rc5(address: int, command: int, toggle: int = 0) -> Wave:
    """14 bits, Manchester at 889 us per half bit: a 1 is space then burst, a 0 burst then space."""
    bits = [1, 1, toggle] + [(address >> i) & 1 for i in range(4, -1, -1)] + [(command >> i) & 1 for i in range(5, -1, -1)]
    w = Wave(["IR"], {"IR": 1})
    w.wait(0.005)
    for b in bits:
        first, second = (1, 0) if b else (0, 1)
        w.set(IR=first)
        w.wait(RC5_HALF)
        w.set(IR=second)
        w.wait(RC5_HALF)
    w.set(IR=1)
    w.wait(0.01)
    return w


def decode_nec(x: np.ndarray, rate: float) -> dict:
    x = debounce(x)
    e = edges(x)
    runs = [(int(x[a]), (b - a) / rate) for a, b in zip(e[:-1], e[1:])]
    frames, repeats, i = [], 0, 0
    while i < len(runs) - 1:
        lvl, d = runs[i]
        if lvl == 0 and 8e-3 < d < 10e-3:
            gap = runs[i + 1][1]
            if 3.8e-3 < gap < 5.2e-3:
                bits = []
                for k in range(32):
                    j = i + 2 + 2 * k
                    if j + 1 >= len(runs):
                        break
                    bits.append(1 if runs[j + 1][1] > 1.1e-3 else 0)
                if len(bits) == 32:
                    by = [sum(bits[8 * n + k] << k for k in range(8)) for n in range(4)]
                    frames.append({"address": by[0], "command": by[2], "ok": by[0] ^ by[1] == 0xFF and by[2] ^ by[3] == 0xFF})
                i += 66
                continue
            if 1.8e-3 < gap < 2.7e-3:
                repeats += 1
        i += 1
    return {"protocol": "NEC infrared", "frames": frames, "repeats": repeats, "bytes": [{"t": 0.0, "value": f["command"], "ok": f["ok"]} for f in frames], "errors": sum(not f["ok"] for f in frames)}


def decode_rc5(x: np.ndarray, rate: float) -> dict:
    """The first burst begins halfway through the first start bit, which fixes the timing of all 14 bits."""
    x = debounce(x)
    lows = np.flatnonzero(np.diff(x.astype(np.int8)) == -1) + 1
    frames, used = [], -1
    for s in lows:
        if s <= used:
            continue
        t0, half = s - RC5_HALF * rate, RC5_HALF * rate
        bits, bad = [], 0
        for k in range(14):
            a, b = int(t0 + (2 * k + 0.5) * half), int(t0 + (2 * k + 1.5) * half)
            if b >= len(x) or a < 0:
                bad += 14
                break
            pair = (int(x[a]), int(x[b]))
            if pair == (1, 0):
                bits.append(1)
            elif pair == (0, 1):
                bits.append(0)
            else:
                bad += 1
                bits.append(0)
        if bad == 0 and bits[0] == 1:
            frames.append({"toggle": bits[2], "address": int("".join(map(str, bits[3:8])), 2), "command": int("".join(map(str, bits[8:14])), 2), "ok": bits[1] == 1})
            used = int(t0 + 28 * half)
    return {"protocol": "RC5 infrared", "frames": frames, "bytes": [{"t": 0.0, "value": f["command"], "ok": f["ok"]} for f in frames], "errors": sum(not f["ok"] for f in frames)}
