"""Generated logic-analyser captures with known contents: UART, SPI, I2C, CAN and 1-Wire, with jitter and glitches."""
import numpy as np


class Wave:
    """Builds digital channels as runs of levels in time, then samples them."""

    def __init__(self, names: list[str], idle: dict):
        self.names, self.t, self.events = names, 0.0, [(0.0, dict(idle))]

    def set(self, **levels):
        self.events.append((self.t, levels))

    def wait(self, dt: float):
        self.t += dt

    def sample(self, rate: float, rnd: np.random.Generator, jitter: float = 0.0, glitches: int = 0) -> dict:
        n = int((self.t + 1e-4) * rate) + 1
        cur, out, k = dict(self.events[0][1]), {c: np.zeros(n, np.uint8) for c in self.names}, 0
        times = np.array([e[0] + (rnd.normal(0, jitter) if jitter and i else 0) for i, e in enumerate(self.events)])
        idx = np.clip((times * rate).astype(int), 0, n - 1)
        for i, (_, levels) in enumerate(self.events):
            start = idx[i]
            end = idx[i + 1] if i + 1 < len(idx) else n
            cur.update(levels)
            for c in self.names:
                out[c][start:end] = cur[c]
        for _ in range(glitches):
            c = self.names[rnd.integers(len(self.names))]
            p = rnd.integers(n)
            out[c][p] ^= 1
        return out


def uart(data: bytes, baud: int, parity: str = "N", invert: bool = False) -> Wave:
    w = Wave(["RX"], {"RX": 0 if invert else 1})
    hi, lo = (0, 1) if invert else (1, 0)
    bit = 1 / baud
    w.wait(5 * bit)
    for b in data:
        bits = [(b >> i) & 1 for i in range(8)]
        if parity in "EO":
            bits.append((sum(bits) + (parity == "O")) % 2)
        w.set(RX=lo)
        w.wait(bit)
        for v in bits:
            w.set(RX=hi if v else lo)
            w.wait(bit)
        w.set(RX=hi)
        w.wait(bit * 1.5)
    w.wait(5 * bit)
    return w


def spi(data: bytes, rate: float, mode: int = 0) -> Wave:
    cpol, cpha = mode >> 1, mode & 1
    w = Wave(["CS", "SCK", "MOSI"], {"CS": 1, "SCK": cpol, "MOSI": 0})
    half = 1 / (2 * rate)
    w.wait(4 * half)
    w.set(CS=0)
    w.wait(2 * half)
    for b in data:
        for i in range(7, -1, -1):
            v = (b >> i) & 1
            if cpha == 0:
                w.set(MOSI=v)
                w.wait(half)
                w.set(SCK=1 - cpol)
                w.wait(half)
                w.set(SCK=cpol)
            else:
                w.set(SCK=1 - cpol)
                w.set(MOSI=v)
                w.wait(half)
                w.set(SCK=cpol)
                w.wait(half)
        w.wait(2 * half)
    w.set(CS=1)
    w.wait(4 * half)
    return w


def i2c(address: int, data: bytes, rate: float, read: bool = False) -> Wave:
    w = Wave(["SCL", "SDA"], {"SCL": 1, "SDA": 1})
    q = 1 / (4 * rate)
    w.wait(4 * q)
    w.set(SDA=0)
    w.wait(2 * q)
    w.set(SCL=0)
    for byte in [(address << 1) | int(read)] + list(data):
        for v in [(byte >> i) & 1 for i in range(7, -1, -1)] + [0]:
            w.wait(q)
            w.set(SDA=v)
            w.wait(q)
            w.set(SCL=1)
            w.wait(2 * q)
            w.set(SCL=0)
    w.wait(q)
    w.set(SDA=0)
    w.wait(q)
    w.set(SCL=1)
    w.wait(q)
    w.set(SDA=1)
    w.wait(4 * q)
    return w


def crc15(bits: list[int]) -> int:
    crc = 0
    for b in bits:
        nxt = b ^ ((crc >> 14) & 1)
        crc = (crc << 1) & 0x7FFF
        if nxt:
            crc ^= 0x4599
    return crc


def can_bits(ident: int, data: bytes) -> list[int]:
    """A standard data frame before stuffing: SOF, ID, RTR, IDE, r0, DLC, data, CRC."""
    bits = [0] + [(ident >> i) & 1 for i in range(10, -1, -1)] + [0, 0, 0] + [(len(data) >> i) & 1 for i in range(3, -1, -1)]
    for b in data:
        bits += [(b >> i) & 1 for i in range(7, -1, -1)]
    c = crc15(bits)
    return bits + [(c >> i) & 1 for i in range(14, -1, -1)]


def stuff(bits: list[int]) -> list[int]:
    out, run, last = [], 0, None
    for b in bits:
        out.append(b)
        run = run + 1 if b == last else 1
        last = b
        if run == 5:
            out.append(1 - b)
            last, run = 1 - b, 1
    return out


def can(frames: list[tuple[int, bytes]], bitrate: int) -> Wave:
    w = Wave(["CAN"], {"CAN": 1})
    bit = 1 / bitrate
    w.wait(12 * bit)
    for ident, data in frames:
        for v in stuff(can_bits(ident, data)) + [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]:
            w.set(CAN=v)
            w.wait(bit)
        w.wait(3 * bit)
    return w


def onewire(data: bytes) -> Wave:
    """Reset, presence, then bytes LSB first: a 1 is a short low pulse, a 0 a long one."""
    w = Wave(["DQ"], {"DQ": 1})
    w.wait(100e-6)
    w.set(DQ=0)
    w.wait(500e-6)
    w.set(DQ=1)
    w.wait(70e-6)
    w.set(DQ=0)
    w.wait(120e-6)
    w.set(DQ=1)
    w.wait(300e-6)
    for b in data:
        for i in range(8):
            w.set(DQ=0)
            w.wait(6e-6 if (b >> i) & 1 else 64e-6)
            w.set(DQ=1)
            w.wait(64e-6 if (b >> i) & 1 else 6e-6)
            w.wait(5e-6)
    w.wait(200e-6)
    return w
