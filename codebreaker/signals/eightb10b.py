"""8b/10b (Widmer and Franaszek, IBM 1983): DC-balanced symbols with a running disparity, used by gigabit Ethernet,
Fibre Channel, SATA, PCI Express 1-2, USB 3 and DisplayPort. Bits are listed in transmission order, abcdei fghj."""

# 5b/6b: value EDCBA -> (code when running disparity is negative, code when positive)
SIX = {0: ("100111", "011000"), 1: ("011101", "100010"), 2: ("101101", "010010"), 3: ("110001", "110001"), 4: ("110101", "001010"), 5: ("101001", "101001"), 6: ("011001", "011001"), 7: ("111000", "000111"), 8: ("111001", "000110"), 9: ("100101", "100101"), 10: ("010101", "010101"), 11: ("110100", "110100"), 12: ("001101", "001101"), 13: ("101100", "101100"), 14: ("011100", "011100"), 15: ("010111", "101000"), 16: ("011011", "100100"), 17: ("100011", "100011"), 18: ("010011", "010011"), 19: ("110010", "110010"), 20: ("001011", "001011"), 21: ("101010", "101010"), 22: ("011010", "011010"), 23: ("111010", "000101"), 24: ("110011", "001100"), 25: ("100110", "100110"), 26: ("010110", "010110"), 27: ("110110", "001001"), 28: ("001110", "001110"), 29: ("101110", "010001"), 30: ("011110", "100001"), 31: ("101011", "010100")}
# 3b/4b: value HGF -> codes; 7 has a primary and an alternate form
FOUR = {0: ("1011", "0100"), 1: ("1001", "1001"), 2: ("0101", "0101"), 3: ("1100", "0011"), 4: ("1101", "0010"), 5: ("1010", "1010"), 6: ("0110", "0110"), 7: ("1110", "0001")}
FOUR_A7 = ("0111", "1000")
K28 = {1: ("0011111001", "1100000110"), 5: ("0011111010", "1100000101"), 7: ("0011111000", "1100000111")}
COMMA = ("0011111", "1100000")


def _balance(code: str) -> int:
    return code.count("1") - code.count("0")


def encode_byte(value: int, rd: int, k: int | None = None) -> tuple[str, int]:
    """One 10-bit symbol and the new running disparity (-1 or +1). k=28 with value 0xBC gives K28.5."""
    if k is not None:
        sym = K28[value >> 5][0 if rd < 0 else 1]
        return sym, -rd if _balance(sym) else rd
    x, y = value & 31, value >> 5
    six = SIX[x][0 if rd < 0 else 1]
    if _balance(six):
        rd = -rd
    alt = y == 7 and ((rd < 0 and x in (17, 18, 20)) or (rd > 0 and x in (11, 13, 14)))
    four = (FOUR_A7 if alt else FOUR[y])[0 if rd < 0 else 1]
    if _balance(four):
        rd = -rd
    return six + four, rd


def encode(data: bytes, commas: int = 4, rd: int = -1) -> str:
    out = []
    for _ in range(commas):
        s, rd = encode_byte(0xBC, rd, k=28)
        out.append(s)
    for b in data:
        s, rd = encode_byte(b, rd)
        out.append(s)
    return "".join(out)


def _tables() -> dict:
    t = {}
    for rd in (-1, 1):
        for v in range(256):
            s, _ = encode_byte(v, rd)
            t.setdefault(s, ("D", v))
        for y in K28:
            s, _ = encode_byte(y << 5 | 28, rd, k=28)
            t[s] = ("K", y << 5 | 28)
    return t


TABLE = _tables()


def align(bits: str) -> int | None:
    """The comma (0011111 or 1100000) can only occur at a symbol boundary in valid 8b/10b."""
    hits = [bits.find(c) for c in COMMA if bits.find(c) >= 0]
    return min(hits) % 10 if hits else None


def decode(bits: str) -> dict:
    """Symbols from the first comma; invalid codes and running-disparity violations are counted."""
    off = align(bits)
    if off is None:
        return {"code": "8b/10b", "aligned": False, "bytes": [], "symbols": 0, "invalid": 0, "disparity_errors": 0, "commas": 0}
    out, invalid, rd_err, commas, rd = [], 0, 0, 0, None
    syms = [bits[i:i + 10] for i in range(off, len(bits) - 9, 10)]
    for s in syms:
        hit = TABLE.get(s)
        if hit is None:
            invalid += 1
            continue
        bal = _balance(s[:6]) + _balance(s[6:])
        if bal not in (-2, 0, 2):
            invalid += 1
        if rd is not None and ((rd < 0 and bal < 0) or (rd > 0 and bal > 0)):
            rd_err += 1
        if bal:
            rd = 1 if bal > 0 else -1
        elif rd is None:
            rd = -1
        if hit[0] == "K":
            commas += 1
        else:
            out.append(hit[1])
    return {"code": "8b/10b", "aligned": True, "offset": off, "bytes": out, "symbols": len(syms), "invalid": invalid, "disparity_errors": rd_err, "commas": commas}
