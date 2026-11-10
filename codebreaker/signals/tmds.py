"""TMDS (DVI 1.0, HDMI): 8-bit pixels become 10-bit symbols with few transitions and a balanced running count.
Bits are given in transmission order, q_out[0] first."""

CONTROL = {(0, 0): "1101010100", (0, 1): "0010101011", (1, 0): "0101010100", (1, 1): "1010101011"}  # q_out[9:0]


def _ones(bits: list[int]) -> int:
    return sum(bits)


def encode_byte(d: int, cnt: int) -> tuple[list[int], int]:
    """One pixel byte: transition-minimise with XOR or XNOR, then invert if that improves DC balance."""
    D = [(d >> i) & 1 for i in range(8)]
    n1 = _ones(D)
    xnor = n1 > 4 or (n1 == 4 and D[0] == 0)
    qm = [D[0]]
    for i in range(1, 8):
        qm.append(1 - (qm[i - 1] ^ D[i]) if xnor else qm[i - 1] ^ D[i])
    qm8 = 0 if xnor else 1
    n1m, n0m = _ones(qm), 8 - _ones(qm)
    if cnt == 0 or n1m == n0m:
        q = (qm if qm8 else [1 - b for b in qm]) + [qm8, 1 - qm8]
        cnt += (n1m - n0m) if qm8 else (n0m - n1m)
    elif (cnt > 0 and n1m > n0m) or (cnt < 0 and n0m > n1m):
        q = [1 - b for b in qm] + [qm8, 1]
        cnt += 2 * qm8 + (n0m - n1m)
    else:
        q = qm + [qm8, 0]
        cnt += -2 * (1 - qm8) + (n1m - n0m)
    return q, cnt


def control_bits(c0: int, c1: int) -> list[int]:
    word = CONTROL[(c0, c1)]
    return [int(ch) for ch in reversed(word)]


def encode(pixels: bytes, blanking: int = 12) -> str:
    """A video line on one channel: control tokens during blanking, then pixel data."""
    out, cnt = [], 0
    for _ in range(blanking):
        out += control_bits(0, 0)
    for p in pixels:
        q, cnt = encode_byte(p, cnt)
        out += q
    for _ in range(4):
        out += control_bits(0, 0)
    return "".join(map(str, out))


def decode_symbol(q: list[int]) -> int:
    d = [1 - b for b in q[:8]] if q[9] else list(q[:8])
    out = [d[0]] + [(d[i] ^ d[i - 1]) if q[8] else 1 - (d[i] ^ d[i - 1]) for i in range(1, 8)]
    return sum(b << i for i, b in enumerate(out))


TOKENS = {"".join(map(str, control_bits(*k))): k for k in CONTROL}


def decode(bits: str) -> dict:
    """Align on control tokens (they repeat during every blanking period), then decode the data symbols."""
    best = None
    for off in range(10):
        syms = [bits[i:i + 10] for i in range(off, len(bits) - 9, 10)]
        tokens = sum(s in TOKENS for s in syms)
        if best is None or tokens > best[0]:
            best = (tokens, off, syms)
    tokens, off, syms = best
    if tokens < 2:
        return {"code": "TMDS", "aligned": False, "bytes": [], "symbols": 0, "invalid": 0, "tokens": tokens}
    data, transitions_bad = [], 0
    for s in syms:
        if s in TOKENS:
            continue
        q = [int(c) for c in s]
        if sum(a != b for a, b in zip(q[:8], q[1:8])) > 5:
            transitions_bad += 1
        data.append(decode_symbol(q))
    return {"code": "TMDS", "aligned": True, "offset": off, "bytes": data, "symbols": len(syms), "tokens": tokens, "invalid": transitions_bad}
