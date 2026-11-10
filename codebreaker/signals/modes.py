"""ADS-B (Mode S extended squitter, 1090 MHz): CRC-24, identity, altitude, CPR position and velocity, and the
pulse-position signal that carries it. Checked against the worked examples in Junzi Sun's "The 1090 MHz Riddle"."""
import math

import numpy as np

CHARS = "#ABCDEFGHIJKLMNOPQRSTUVWXYZ##### ###############0123456789######"
POLY = 0xFFF409
NZ = 15


def bits_of(hexstr: str) -> str:
    return bin(int(hexstr, 16))[2:].zfill(len(hexstr) * 4)


def crc24(bits: str) -> int:
    """Remainder of the message, with the last 24 bits as parity, divided by the Mode S generator: 0 for a clean frame."""
    data = [int(b) for b in bits]
    gen = [int(b) for b in bin(POLY | (1 << 24))[2:]]
    for i in range(len(data) - 24):
        if data[i]:
            for j in range(25):
                data[i + j] ^= gen[j]
    return int("".join(map(str, data[-24:])), 2)


def with_parity(payload_hex: str) -> str:
    """Append the CRC-24 parity to an 88-bit payload."""
    b = bits_of(payload_hex) + "0" * 24
    return payload_hex + f"{crc24(b):06X}"


def _int(b: str, a: int, z: int) -> int:
    return int(b[a - 1:z], 2)


def _altitude(b: str) -> int | None:
    a = b[40:52]
    if a[7] == "1":
        n = int(a[:7] + a[8:], 2)
        return n * 25 - 1000
    return None


def _nl(lat: float) -> int:
    if abs(lat) >= 87:
        return 1 if abs(lat) > 87 else 2
    return int(math.floor(2 * math.pi / math.acos(1 - (1 - math.cos(math.pi / (2 * NZ))) / math.cos(math.radians(lat)) ** 2)))


def cpr_global(even: tuple, odd: tuple, newest_odd: bool) -> tuple[float, float] | None:
    """Latitude and longitude from an even and an odd compact position report."""
    lat_e, lon_e = even[0] / 131072, even[1] / 131072
    lat_o, lon_o = odd[0] / 131072, odd[1] / 131072
    j = math.floor(59 * lat_e - 60 * lat_o + 0.5)
    le, lo = 360 / 60 * ((j % 60) + lat_e), 360 / 59 * ((j % 59) + lat_o)
    le, lo = (le - 360 if le >= 270 else le), (lo - 360 if lo >= 270 else lo)
    if _nl(le) != _nl(lo):
        return None
    lat = lo if newest_odd else le
    nl = _nl(lat)
    m = math.floor(lon_e * (nl - 1) - lon_o * nl + 0.5)
    ni = max(nl - (1 if newest_odd else 0), 1)
    lon = 360 / ni * ((m % ni) + (lon_o if newest_odd else lon_e))
    return round(lat, 5), round(lon - 360 if lon >= 180 else lon, 5)


def decode(hexstr: str) -> dict:
    b = bits_of(hexstr)
    out = {"hex": hexstr.upper(), "df": _int(b, 1, 5), "crc_ok": len(b) == 112 and crc24(b) == 0}
    if out["df"] not in (17, 18) or len(b) != 112:
        return out
    out["icao"] = f"{_int(b, 9, 32):06X}"
    tc = _int(b, 33, 37)
    out["tc"] = tc
    if 1 <= tc <= 4:
        out["kind"] = "identification"
        out["callsign"] = "".join(CHARS[_int(b, 41 + 6 * i, 46 + 6 * i)] for i in range(8)).replace("#", "").strip()
    elif 9 <= tc <= 18:
        out["kind"] = "airborne position"
        out["altitude_ft"] = _altitude(b)
        out["cpr_odd"] = b[53] == "1"
        out["cpr"] = (_int(b, 55, 71), _int(b, 72, 88))
    elif tc == 19 and _int(b, 38, 40) in (1, 2):
        out["kind"] = "airborne velocity"
        vew = (_int(b, 47, 56) - 1) * (-1 if b[45] == "1" else 1)
        vns = (_int(b, 58, 67) - 1) * (-1 if b[56] == "1" else 1)
        out["speed_kt"] = round(math.hypot(vew, vns), 2)
        out["heading_deg"] = round(math.degrees(math.atan2(vew, vns)) % 360, 2)
        out["vertical_rate_fpm"] = (_int(b, 70, 78) - 1) * 64 * (-1 if b[68] == "1" else 1)
    else:
        out["kind"] = f"type code {tc}"
    return out


def ppm(frames: list[str], rnd: np.random.Generator, noise: float = 0.1, gap_us: float = 60) -> np.ndarray:
    """Magnitude at 2 million samples a second: a preamble of four pulses, then each bit as a pulse in its first or second half."""
    out = [np.zeros(int(gap_us * 2))]
    for h in frames:
        pre = np.zeros(16)
        pre[[0, 2, 7, 9]] = 1
        data = np.zeros(224)
        for i, bit in enumerate(bits_of(h)):
            data[2 * i + (0 if bit == "1" else 1)] = 1
        out += [pre, data, np.zeros(int(gap_us * 2))]
    x = np.concatenate(out) * rnd.uniform(0.6, 1.0)
    return np.abs(x + rnd.normal(0, noise, len(x))).astype(np.float32)


def _syndromes() -> dict:
    """The CRC remainder left by a single flipped bit, for each of the 88 data bits: it names the bit to repair."""
    out = {}
    for i in range(88):
        b = ["0"] * 112
        b[i] = "1"
        out[crc24("".join(b))] = i
    return out


SYNDROME = _syndromes()


def repair(bits: str) -> tuple[str, int | None]:
    """A clean frame, or one with a single wrong data bit put right; anything worse is rejected."""
    r = crc24(bits)
    if r == 0:
        return bits, None
    i = SYNDROME.get(r)
    if i is None or bits[:5] not in ("10001", "10010"):
        return "", None
    return bits[:i] + ("1" if bits[i] == "0" else "0") + bits[i + 1:], i


def demodulate(x: np.ndarray) -> list[dict]:
    """Find preambles, read 112 bits by comparing the two halves of each bit, and keep frames whose CRC is zero."""
    found, i, n = [], 0, len(x)
    while i < n - 240:
        p = x[i:i + 16]
        hi = (p[0] + p[2] + p[7] + p[9]) / 4
        lo = (p[1] + p[3] + p[4] + p[5] + p[6] + p[8]) / 6
        if hi > 2.5 * lo + 0.1 and hi > 0.2:
            d = x[i + 16:i + 240].reshape(112, 2)
            bits, fixed = repair("".join("1" if a > b else "0" for a, b in d))
            if bits:
                f = decode(f"{int(bits, 2):028X}")
                f["repaired_bit"] = fixed
                found.append(f)
                i += 240
                continue
        i += 1
    return found
