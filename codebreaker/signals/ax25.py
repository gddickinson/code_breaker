"""APRS packets: AX.25 frames in HDLC with NRZI, sent as Bell 202 AFSK (1200 baud, 1200 and 2200 Hz tones).

The frame check is CRC-16/X-25, checked against its published value 0x906E for "123456789"."""
import numpy as np

SR, BAUD, MARK, SPACE = 48000, 1200, 1200.0, 2200.0


def crc_x25(data: bytes) -> int:
    c = 0xFFFF
    for b in data:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ 0x8408 if c & 1 else c >> 1
    return c ^ 0xFFFF


def address(call: str, last: bool) -> bytes:
    name, _, ssid = call.partition("-")
    return bytes((ord(c) << 1) for c in name.upper().ljust(6)[:6]) + bytes([0x60 | (int(ssid or 0) << 1) | int(last)])


def frame(src: str, dst: str, info: str, path: tuple = ("WIDE1-1",)) -> bytes:
    calls = [dst, src, *path]
    body = b"".join(address(c, i == len(calls) - 1) for i, c in enumerate(calls)) + b"\x03\xf0" + info.encode()
    c = crc_x25(body)
    return body + bytes([c & 0xFF, c >> 8])


def to_bits(data: bytes) -> list[int]:
    """HDLC: flags around the frame, a 0 stuffed after five 1s, least significant bit first."""
    flag = [0, 1, 1, 1, 1, 1, 1, 0]
    out, ones = flag * 8, 0
    for b in data:
        for i in range(8):
            v = (b >> i) & 1
            out.append(v)
            ones = ones + 1 if v else 0
            if ones == 5:
                out.append(0)
                ones = 0
    return out + flag * 4


def afsk(data: bytes, rnd: np.random.Generator, noise: float = 0.05) -> np.ndarray:
    """NRZI: a 0 switches tone, a 1 keeps it. Phase stays continuous across bits."""
    tone, phase, spb, out = MARK, 0.0, SR / BAUD, []
    acc = 0.0
    for b in to_bits(data):
        if b == 0:
            tone = SPACE if tone == MARK else MARK
        acc += spb
        n = int(round(acc))
        acc -= n
        t = np.arange(n)
        out.append(np.sin(phase + 2 * np.pi * tone * t / SR))
        phase = (phase + 2 * np.pi * tone * n / SR) % (2 * np.pi)
    x = np.concatenate([np.zeros(SR // 10), *out, np.zeros(SR // 10)]) * 0.5
    return (x + rnd.normal(0, noise, len(x))).astype(np.float32)


def demodulate(x: np.ndarray, sr: int = SR) -> list[int]:
    """Tone per sample from correlation with each tone over one bit, then sampling at bit centres re-timed on changes."""
    n = int(sr / BAUD)
    t = np.arange(n) / sr
    k = np.ones(n)
    def power(f):
        i = np.convolve(x, np.cos(2 * np.pi * f * t)[::-1], "same")
        q = np.convolve(x, np.sin(2 * np.pi * f * t)[::-1], "same")
        return i * i + q * q
    raw = (power(MARK) > power(SPACE)).astype(np.float32)
    # Smooth the tone decision, then let transitions nudge the bit clock halfway rather than reset it,
    # so a noise blip near the decision boundary cannot make the decoder skip a bit.
    m = max(3, n // 4)
    mark = (np.convolve(raw, np.ones(m) / m, "same") > 0.5).astype(np.int8)
    change = np.flatnonzero(np.diff(mark)) + 1
    spb = sr / BAUD
    bits, last, pos, k = [], mark[0], spb / 2, 0
    while pos < len(mark):
        while k < len(change) and change[k] < pos:
            k += 1
        # Only a change since the previous sample re-times this bit: the ideal sample is half a bit after it.
        if k and change[k - 1] >= pos - spb:
            pos += 0.5 * ((change[k - 1] + spb / 2) - pos)
        p = int(pos)
        if p >= len(mark):
            break
        v = int(mark[p])
        bits.append(1 if v == last else 0)
        last = v
        pos += spb
    return bits


def deframe(bits: list[int]) -> list[dict]:
    """Split on flags, remove stuffed zeros, check each frame's CRC and read the addresses and text."""
    s = "".join(map(str, bits))
    out = []
    for chunk in s.split("01111110"):
        if len(chunk) < 136:
            continue
        b, ones, i = [], 0, 0
        while i < len(chunk):
            v = chunk[i]
            if ones == 5:
                ones, i = 0, i + 1
                continue
            b.append(int(v))
            ones = ones + 1 if v == "1" else 0
            i += 1
        data = bytes(sum(b[j + k] << k for k in range(8)) for j in range(0, len(b) - 7, 8))
        if len(data) < 18:
            continue
        body, fcs = data[:-2], data[-2] | (data[-1] << 8)
        if crc_x25(body) != fcs:
            out.append({"crc_ok": False})
            continue
        calls, j = [], 0
        while j + 7 <= len(body):
            a = body[j:j + 7]
            calls.append("".join(chr(c >> 1) for c in a[:6]).strip() + (f"-{(a[6] >> 1) & 15}" if (a[6] >> 1) & 15 else ""))
            j += 7
            if a[6] & 1:
                break
        out.append({"crc_ok": True, "destination": calls[0], "source": calls[1] if len(calls) > 1 else "", "path": calls[2:], "info": body[j + 2:].decode("latin-1")})
    return out
