"""USB low and full speed from sampled D+ and D-: NRZI, bit stuffing, packet IDs, CRC5 and CRC16.

Generated packets and the decoder share nothing but the specification, and both CRCs are checked against the
published catalogue values (CRC-5/USB check 0x19, CRC-16/USB check 0xB4C8 for the bytes "123456789")."""
import numpy as np

from .logic_decode import debounce
from .logic_synth import Wave

PIDS = {0x1: "OUT", 0x9: "IN", 0x5: "SOF", 0xD: "SETUP", 0x3: "DATA0", 0xB: "DATA1", 0x7: "DATA2", 0xF: "MDATA", 0x2: "ACK", 0xA: "NAK", 0xE: "STALL", 0x6: "NYET"}
TOKENS, DATA, HANDSHAKE = {0x1, 0x9, 0xD}, {0x3, 0xB, 0x7, 0xF}, {0x2, 0xA, 0xE, 0x6}
SPEEDS = {"full": 12_000_000, "low": 1_500_000}


def lsb_bits(data: bytes) -> list[int]:
    return [(b >> i) & 1 for b in data for i in range(8)]


def crc5(bits: list[int]) -> int:
    """Reflected CRC-5/USB over bits sent least significant first."""
    c = 0x1F
    for b in bits:
        c = (c >> 1) ^ 0x14 if (c ^ b) & 1 else c >> 1
    return c ^ 0x1F


def crc16(data: bytes) -> int:
    c = 0xFFFF
    for byte in data:
        c ^= byte
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c ^ 0xFFFF


def packet_bits(pid: int, addr: int = 0, endp: int = 0, data: bytes = b"") -> list[int]:
    """SYNC, PID with its complement, then the fields for this packet type, least significant bit first."""
    bits = [0, 0, 0, 0, 0, 0, 0, 1] + lsb_bits(bytes([pid | ((~pid & 0xF) << 4)]))
    if pid in TOKENS:
        f = [(addr >> i) & 1 for i in range(7)] + [(endp >> i) & 1 for i in range(4)]
        c = crc5(f)
        bits += f + [(c >> i) & 1 for i in range(5)]
    elif pid in DATA:
        c = crc16(data)
        bits += lsb_bits(data) + lsb_bits(bytes([c & 0xFF, c >> 8]))
    return bits


def stuff(bits: list[int]) -> list[int]:
    out, ones = [], 0
    for b in bits:
        out.append(b)
        ones = ones + 1 if b else 0
        if ones == 6:
            out.append(0)
            ones = 0
    return out


def transaction(packets: list[tuple], speed: str = "full") -> Wave:
    """Packets on the wire: NRZI (0 toggles the line), stuffed, each ended by two bits of SE0 then idle J."""
    jp, jm = (1, 0) if speed == "full" else (0, 1)
    w = Wave(["D+", "D-"], {"D+": jp, "D-": jm})
    bit = 1 / SPEEDS[speed]
    w.wait(20 * bit)
    for p in packets:
        state = 1
        for b in stuff(packet_bits(*p)):
            if b == 0:
                state ^= 1
            w.set(**{"D+": jp if state else 1 - jp, "D-": jm if state else 1 - jm})
            w.wait(bit)
        w.set(**{"D+": 0, "D-": 0})
        w.wait(2 * bit)
        w.set(**{"D+": jp, "D-": jm})
        w.wait(8 * bit)
    w.wait(10 * bit)
    return w


def _decode_packet(bits: list[int]) -> dict | None:
    if bits[:8] != [0, 0, 0, 0, 0, 0, 0, 1] or len(bits) < 16:
        return None
    out, ones, i = [], 0, 8
    while i < len(bits):
        b = bits[i]
        if ones == 6:
            if b != 0:
                return {"error": "stuffing"}
            ones, i = 0, i + 1
            continue
        out.append(b)
        ones = ones + 1 if b else 0
        i += 1
    if len(out) < 8:
        return None
    pid = sum(v << k for k, v in enumerate(out[:8]))
    if (pid & 0xF) != (~pid >> 4) & 0xF:
        return {"error": "PID check"}
    p, body = pid & 0xF, out[8:]
    rec = {"pid": PIDS.get(p, hex(p)), "ok": True}
    if p in TOKENS and len(body) >= 16:
        rec |= {"addr": sum(v << k for k, v in enumerate(body[:7])), "endp": sum(v << k for k, v in enumerate(body[7:11])), "ok": crc5(body[:11]) == sum(v << k for k, v in enumerate(body[11:16]))}
    elif p in DATA:
        n = len(body) // 8
        data = bytes(sum(v << k for k, v in enumerate(body[8 * j:8 * j + 8])) for j in range(n))
        if n < 2:
            return {"error": "short data"}
        rec |= {"data": list(data[:-2]), "ok": crc16(data[:-2]) == data[-2] | (data[-1] << 8)}
    return rec


def decode(dp: np.ndarray, dm: np.ndarray, rate: float) -> dict:
    """Find the speed from the idle state, recover bits from line changes, and check every packet."""
    dp, dm = debounce(dp), debounce(dm)
    speed = "full" if dp[:20].mean() > dm[:20].mean() else "low"
    spb = rate / SPEEDS[speed]
    diff = dp.astype(np.int8) - dm.astype(np.int8)
    jval = 1 if speed == "full" else -1
    packets, n, i = [], len(dp), 1
    while i < n:
        if diff[i - 1] == jval and diff[i] == -jval:
            states, k = [], 0
            while True:
                c = int(i + spb * (k + 0.5))
                if c >= n or diff[c] == 0:
                    break
                states.append(1 if diff[c] == jval else 0)
                k += 1
            prev, bits = 1, []
            for s in states:
                bits.append(1 if s == prev else 0)
                prev = s
            rec = _decode_packet(bits)
            if rec is not None:
                rec["t"] = i / rate
                packets.append(rec)
            i = int(i + spb * (k + 2))
        else:
            i += 1
    # Each data byte is placed at its position after SYNC and PID, ignoring stuffed bits, for drawing.
    byte_t = 8 / SPEEDS[speed]
    data = [{"t": p["t"] + (2 + j) * byte_t, "value": v, "ok": True} for p in packets if p.get("ok") and "data" in p for j, v in enumerate(p["data"])]
    return {"protocol": "USB", "speed": speed, "packets": packets, "bytes": data, "errors": sum(1 for p in packets if not p.get("ok") or "error" in p)}
