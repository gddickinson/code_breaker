"""Decode sampled digital signals: UART with baud and polarity found automatically, SPI with its mode, and I2C."""
import numpy as np

BAUDS = [300, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 76800, 115200, 230400, 250000, 460800, 500000, 921600, 1000000]


def edges(x: np.ndarray) -> np.ndarray:
    return np.flatnonzero(np.diff(x.astype(np.int8)) != 0) + 1


def debounce(x: np.ndarray, k: int = 1) -> np.ndarray:
    """Remove pulses no longer than k samples, which are glitches rather than data."""
    y = x.copy()
    e = edges(y)
    runs = np.diff(np.concatenate([[0], e, [len(y)]]))
    starts = np.concatenate([[0], e])
    for s, r in zip(starts, runs):
        if 0 < s and r <= k and s + r < len(y):
            y[s:s + r] = y[s - 1]
    return y


def unit_width(x: np.ndarray) -> float:
    """The shortest common run between edges: one bit for NRZ lines."""
    e = edges(x)
    if len(e) < 4:
        return 0.0
    runs = np.diff(e)
    runs = runs[runs > 1]
    if not len(runs):
        return 0.0
    small = np.percentile(runs, 10)
    close = runs[runs < small * 1.5]
    return float(np.median(close)) if len(close) else float(small)


def guess_baud(x: np.ndarray, rate: float) -> int:
    w = unit_width(x)
    if not w:
        return 0
    est = rate / w
    return min(BAUDS, key=lambda b: abs(np.log(b / est)))


def uart(x: np.ndarray, rate: float, baud: int | None = None, parity: str | None = None) -> dict:
    """8 data bits, LSB first. Unless given, parity (none, even, odd) and polarity are both found by decoding every
    combination and keeping the one with the fewest framing and parity errors; ties go to no parity."""
    x = debounce(x)
    tries = [_uart(x, rate, baud, p, inv) for p in ([parity] if parity else ["N", "E", "O"]) for inv in (False, True)]
    return min(tries, key=lambda r: (r["errors"] / max(len(r["bytes"]), 1), -len(r["bytes"]), r.get("parity", "N") != "N"))


def _uart(x: np.ndarray, rate: float, baud: int | None, parity: str, invert: bool) -> dict:
    y = 1 - x if invert else x
    baud = baud or guess_baud(y, rate)
    if not baud:
        return {"protocol": "UART", "bytes": [], "errors": 0, "baud": 0}
    spb = rate / baud
    nbits = 9 if parity in "EO" else 8
    out, errors, i, n = [], 0, 1, len(y)
    while i < n:
        if y[i - 1] == 1 and y[i] == 0:
            centres = [int(i + spb * (k + 1.5)) for k in range(nbits)]
            stop = int(i + spb * (nbits + 1.5))
            if stop >= n:
                break
            bits = [int(y[c]) for c in centres]
            val = sum(b << k for k, b in enumerate(bits[:8]))
            ok = y[stop] == 1 and y[int(i + spb * 0.5)] == 0
            if parity in "EO" and ok:
                ok = (sum(bits) % 2) == (1 if parity == "O" else 0)
            out.append({"t": i / rate, "value": val, "ok": bool(ok)})
            errors += not ok
            i = int(i + spb * (nbits + 1))
        else:
            i += 1
    return {"protocol": "UART", "baud": baud, "inverted": bool(invert), "parity": parity, "bytes": out, "errors": errors}


def spi(cs: np.ndarray, sck: np.ndarray, mosi: np.ndarray, rate: float) -> dict:
    """Clock polarity from the idle level; phase from which clock edge the data never changes on."""
    cs, sck, mosi = debounce(cs), debounce(sck), debounce(mosi)
    active = cs == 0
    if not active.any():
        return {"protocol": "SPI", "bytes": [], "errors": 0}
    first = int(np.argmax(active))
    cpol = int(sck[max(first - 1, 0)])
    e = edges(sck)
    e = e[active[np.clip(e, 0, len(cs) - 1)]]
    lead = [k for k in e if sck[k] != cpol]
    trail = [k for k in e if sck[k] == cpol]
    d = edges(mosi)

    def changes_at(ks):
        """How often the data line changes within a sample of this kind of clock edge: it must not, where data is read."""
        if not len(d) or not ks:
            return 0.0
        return float(np.mean([np.min(np.abs(d - k)) <= 1 for k in ks]))
    cpha = 0 if changes_at(lead) <= changes_at(trail) else 1
    samples = lead if cpha == 0 else trail
    bits = [int(mosi[k]) for k in samples]
    out = []
    for j in range(0, len(bits) - 7, 8):
        out.append({"t": samples[j] / rate, "value": int("".join(map(str, bits[j:j + 8])), 2), "ok": True})
    return {"protocol": "SPI", "mode": cpol * 2 + cpha, "cpol": cpol, "cpha": cpha, "bytes": out, "errors": 0}


def i2c(scl: np.ndarray, sda: np.ndarray, rate: float) -> dict:
    """START and STOP from data changing while the clock is high; bits on clock rises; the ninth bit is ACK."""
    scl, sda = debounce(scl), debounce(sda)
    out, msgs, cur, bits, errors = [], [], None, [], 0
    for k in edges(np.maximum(scl, 0) * 2 + sda):
        if k == 0:
            continue
        if scl[k] == 1 and scl[k - 1] == 1 and sda[k] != sda[k - 1]:
            if sda[k] == 0:
                cur, bits = {"t": k / rate, "address": None, "read": None, "data": [], "acks": []}, []
            elif cur is not None:
                msgs.append(cur)
                cur = None
            continue
        if cur is not None and scl[k] == 1 and scl[k - 1] == 0:
            bits.append(int(sda[k]))
            if len(bits) == 9:
                byte, ack = int("".join(map(str, bits[:8])), 2), bits[8] == 0
                if cur["address"] is None:
                    cur["address"], cur["read"] = byte >> 1, bool(byte & 1)
                else:
                    cur["data"].append(byte)
                    out.append({"t": k / rate, "value": byte, "ok": ack})
                cur["acks"].append(ack)
                errors += not ack
                bits = []
    return {"protocol": "I2C", "messages": msgs, "bytes": out, "errors": errors}
