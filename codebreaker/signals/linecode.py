"""Manchester, NRZI and 4B5B line codes, and Ethernet frames with their CRC-32 frame check."""
import zlib

FOUR_FIVE = ["11110", "01001", "10100", "10101", "01010", "01011", "01110", "01111", "10010", "10011", "10110", "10111", "11010", "11011", "11100", "11101"]
FIVE_FOUR = {c: i for i, c in enumerate(FOUR_FIVE)}
CONTROL_45 = {"11111": "I", "11000": "J", "10001": "K", "01101": "T", "00111": "R", "00100": "H", "00000": "Q"}


def bits_lsb(data: bytes) -> str:
    return "".join(str((b >> i) & 1) for b in data for i in range(8))


def bytes_lsb(bits: str) -> bytes:
    return bytes(sum(int(bits[i + k]) << k for k in range(8)) for i in range(0, len(bits) - 7, 8))


def manchester(bits: str, ieee: bool = True) -> str:
    """IEEE 802.3: a 1 is low-to-high in mid-bit, a 0 high-to-low. G. E. Thomas uses the opposite."""
    one, zero = ("01", "10") if ieee else ("10", "01")
    return "".join(one if b == "1" else zero for b in bits)


def unmanchester(chips: str) -> dict:
    """Try both half-bit alignments and both conventions; a clock transition must sit in every bit."""
    best = None
    for off in (0, 1):
        pairs = [chips[i:i + 2] for i in range(off, len(chips) - 1, 2)]
        bad = sum(p not in ("01", "10") for p in pairs)
        if best is None or bad < best[1]:
            best = (off, bad, pairs)
    off, bad, pairs = best
    ieee = "".join("1" if p == "01" else "0" for p in pairs)
    return {"code": "Manchester", "offset": off, "symbols": len(pairs), "invalid": bad, "bits_ieee": ieee, "bits_thomas": "".join("0" if b == "1" else "1" for b in ieee)}


def nrzi(bits: str) -> str:
    """A 1 is sent as a change of level, a 0 as no change (as used under 4B5B on FDDI and 100BASE-FX)."""
    out, level = [], 0
    for b in bits:
        if b == "1":
            level ^= 1
        out.append(str(level))
    return "".join(out)


def unnrzi(line: str, start: int = 0) -> str:
    prev, out = start, []
    for c in line:
        v = int(c)
        out.append("1" if v != prev else "0")
        prev = v
    return "".join(out)


def encode_4b5b(data: bytes, idle: int = 4) -> str:
    """Idle symbols, the J K start delimiter, data nibbles (low nibble first), then T R."""
    body = "".join(FOUR_FIVE[b & 15] + FOUR_FIVE[b >> 4] for b in data)
    return "11111" * idle + "11000" + "10001" + body + "01101" + "00111" + "11111" * idle


def decode_4b5b(bits: str) -> dict:
    """Align on the J K delimiter, read nibbles until T; any symbol outside the table is invalid."""
    start = bits.find("1100010001")
    if start < 0:
        return {"code": "4B5B", "aligned": False, "bytes": [], "symbols": 0, "invalid": 0}
    i, nib, invalid, n = start + 10, [], 0, 0
    while i + 5 <= len(bits):
        s = bits[i:i + 5]
        n += 1
        if s == "01101":
            break
        if s in FIVE_FOUR:
            nib.append(FIVE_FOUR[s])
        else:
            invalid += 1
        i += 5
    data = [nib[j] | (nib[j + 1] << 4) for j in range(0, len(nib) - 1, 2)]
    return {"code": "4B5B", "aligned": True, "offset": start % 5, "bytes": data, "symbols": n, "invalid": invalid}


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def ethernet_frame(dst: bytes, src: bytes, ethertype: int, payload: bytes) -> bytes:
    """Preamble, start frame delimiter, header, payload padded to 46 bytes, and the CRC-32 frame check sequence."""
    body = dst + src + ethertype.to_bytes(2, "big") + payload.ljust(46, b"\x00")
    return b"\x55" * 7 + b"\xd5" + body + crc32(body).to_bytes(4, "little")


def parse_ethernet(data: bytes) -> dict | None:
    """Find the start frame delimiter, split the header and check the CRC."""
    i = data.find(b"\x55\xd5")
    if i < 0:
        return None
    f = data[i + 2:]
    if len(f) < 64:
        return None
    for end in range(len(f), 63, -1):
        body, fcs = f[:end - 4], f[end - 4:end]
        if crc32(body).to_bytes(4, "little") == fcs:
            return {"dst": body[:6].hex(":"), "src": body[6:12].hex(":"), "ethertype": f"0x{int.from_bytes(body[12:14], 'big'):04x}", "payload": list(body[14:]), "crc_ok": True}
    return {"dst": f[:6].hex(":"), "src": f[6:12].hex(":"), "ethertype": f"0x{int.from_bytes(f[12:14], 'big'):04x}", "payload": [], "crc_ok": False}
