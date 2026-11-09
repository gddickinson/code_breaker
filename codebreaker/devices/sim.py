"""Simulated serial devices, so the live analysis can be shown and tested without hardware."""
import math
import random
import struct
import time

SIMS = {"sim://gps": "Simulated GPS receiver (NMEA sentences)", "sim://sensor": "Simulated sensor board (comma-separated readings)", "sim://packets": "Simulated binary telemetry (fixed 16-byte packets)"}


def nmea_line(t: float) -> bytes:
    lat, lon = 4851.3 + 0.01 * math.sin(t / 7), 220.6 + 0.01 * math.cos(t / 9)
    body = f"GPGGA,{time.strftime('%H%M%S', time.gmtime(t))}.00,{lat:.4f},N,00{lon:.4f},E,1,08,0.9,35.{int(t) % 10},M,46.9,M,,"
    x = 0
    for c in body.encode():
        x ^= c
    return f"${body}*{x:02X}\r\n".encode()


class SimPort:
    """Behaves like a pyserial port for reading: produces bytes at a steady rate."""

    def __init__(self, url: str, seed: int = 1):
        self.kind, self.rnd, self.t0, self.n = url, random.Random(seed), time.time(), 0

    def read(self, size: int = 4096) -> bytes:
        time.sleep(0.1)
        t = time.time()
        self.n += 1
        if self.kind == "sim://gps":
            return nmea_line(t) if self.n % 5 == 0 else b""
        if self.kind == "sim://sensor":
            return f"{20 + 2 * math.sin(t / 5) + self.rnd.gauss(0, 0.1):.2f},{55 + self.rnd.gauss(0, 0.5):.1f},{1013 + self.rnd.randint(-2, 2)}\n".encode()
        seq = self.n & 0xFFFF
        payload = struct.pack("<HhhhI", seq, int(100 * math.sin(t)), int(100 * math.cos(t)), self.rnd.randint(-5, 5), int(t))
        return b"\xAA\x55" + payload + bytes([sum(payload) & 0xFF, 0x0D])

    def close(self) -> None:
        pass
