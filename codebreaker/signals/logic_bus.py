"""CAN frames (bit rate found, stuffing removed, CRC-15 checked) and 1-Wire slots, from sampled lines."""
import numpy as np

from .logic_decode import BAUDS, debounce, edges, unit_width
from .logic_synth import crc15

CAN_RATES = [10000, 20000, 50000, 83333, 100000, 125000, 250000, 500000, 800000, 1000000]


def can(x: np.ndarray, rate: float, bitrate: int | None = None) -> dict:
    x = debounce(x)
    if not bitrate:
        w = unit_width(x)
        bitrate = min(CAN_RATES, key=lambda b: abs(np.log(b / (rate / w)))) if w else 0
    if not bitrate:
        return {"protocol": "CAN", "frames": [], "bytes": [], "errors": 0, "bitrate": 0}
    spb, n, i = rate / bitrate, len(x), 1
    frames, out, errors = [], [], 0
    while i < n:
        if x[i - 1] == 1 and x[i] == 0 and (i < 11 * spb or np.all(x[max(0, int(i - 10 * spb)):i] == 1)):
            raw, k, run, last, bits, stuffed_err = [], 0, 0, None, [], False
            while True:
                c = int(i + spb * (k + 0.5))
                if c >= n:
                    break
                b = int(x[c])
                k += 1
                if run == 5:
                    if b == last:
                        stuffed_err = True
                        break
                    run, last = 1, b
                    continue
                run = run + 1 if b == last else 1
                last = b
                bits.append(b)
                if len(bits) == 19:
                    dlc = int("".join(map(str, bits[15:19])), 2)
                    need = 19 + 8 * min(dlc, 8) + 15
                if len(bits) >= 19 and len(bits) == need:
                    break
            if len(bits) >= 34 and not stuffed_err:
                ident = int("".join(map(str, bits[1:12])), 2)
                dlc = min(int("".join(map(str, bits[15:19])), 2), 8)
                data = [int("".join(map(str, bits[19 + 8 * j:27 + 8 * j])), 2) for j in range(dlc)]
                crc = int("".join(map(str, bits[19 + 8 * dlc:34 + 8 * dlc])), 2)
                ok = crc == crc15(bits[:19 + 8 * dlc])
                frames.append({"t": i / rate, "id": ident, "data": data, "crc_ok": ok})
                out += [{"t": i / rate, "value": d, "ok": ok} for d in data]
                errors += not ok
            elif stuffed_err:
                errors += 1
            i = int(i + spb * (k + 10))
        else:
            i += 1
    return {"protocol": "CAN", "bitrate": bitrate, "frames": frames, "bytes": out, "errors": errors}


def onewire(x: np.ndarray, rate: float) -> dict:
    """Low pulses: over 400 microseconds is a reset; under 15 is a 1; 15 to 120 is a 0."""
    x = debounce(x)
    e = edges(x)
    lows = [(a, b) for a, b in zip(e[:-1], e[1:]) if x[a] == 0]
    bits, out, resets, presence = [], [], 0, 0
    for a, b in lows:
        us = (b - a) / rate * 1e6
        if us > 400:
            resets += 1
            bits = []
        elif 60 <= us <= 240 and resets and not bits and presence < resets:
            presence += 1
        elif us < 15:
            bits.append(1)
        elif us <= 120:
            bits.append(0)
        if len(bits) == 8:
            out.append({"t": a / rate, "value": sum(v << k for k, v in enumerate(bits)), "ok": True})
            bits = []
    return {"protocol": "1-Wire", "resets": resets, "presence": presence, "bytes": out, "errors": 0}
