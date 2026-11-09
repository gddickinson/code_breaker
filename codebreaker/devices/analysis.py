"""What kind of data is this? Measurements and format checks for an unknown byte stream."""
import json
import math
import re
from collections import Counter

import numpy as np


def entropy(b: bytes) -> float:
    if not b:
        return 0.0
    n = len(b)
    return -sum(c / n * math.log2(c / n) for c in Counter(b).values())


def nmea(lines: list[str]) -> dict | None:
    """GPS and marine sentences: $GPGGA,...*hh with an XOR checksum."""
    ok = bad = 0
    kinds = Counter()
    for l in lines:
        m = re.fullmatch(r"\$([A-Z]{5}),([^*]*)\*([0-9A-F]{2})", l.strip())
        if m:
            x = 0
            for c in (m[1] + "," + m[2]).encode():
                x ^= c
            ok += x == int(m[3], 16)
            bad += x != int(m[3], 16)
            kinds[m[1]] += 1
    return {"valid_checksums": ok, "bad_checksums": bad, "sentences": dict(kinds.most_common(6))} if ok + bad else None


def json_lines(lines: list[str]) -> dict | None:
    good, keys = 0, Counter()
    for l in lines:
        try:
            v = json.loads(l)
        except ValueError:
            continue
        if isinstance(v, dict):
            good += 1
            keys.update(v.keys())
    return {"objects": good, "keys": [k for k, _ in keys.most_common(8)]} if good >= 2 else None


def numeric_columns(lines: list[str]) -> dict | None:
    """Lines of numbers separated by commas, tabs or spaces: sensor readings."""
    rows = [re.split(r"[,\t; ]+", l.strip()) for l in lines if l.strip()]
    nums = [r for r in rows if r and all(re.fullmatch(r"-?\d+(\.\d+)?", x) for x in r)]
    if len(nums) < 3:
        return None
    widths = Counter(len(r) for r in nums)
    w = widths.most_common(1)[0][0]
    cols = np.array([[float(x) for x in r] for r in nums if len(r) == w])
    return {"rows": len(cols), "columns": w, "means": [round(float(v), 3) for v in cols.mean(axis=0)[:8]], "ranges": [[round(float(a), 3), round(float(b), 3)] for a, b in zip(cols.min(axis=0)[:8], cols.max(axis=0)[:8])]}


def key_values(lines: list[str]) -> dict | None:
    pairs = Counter(k for l in lines for k, _ in re.findall(r"([A-Za-z_][\w.]*)\s*[=:]\s*(-?[\w.]+)", l))
    return {"keys": [k for k, _ in pairs.most_common(10)]} if sum(pairs.values()) >= 4 else None


def at_commands(lines: list[str]) -> dict | None:
    n = sum(bool(re.match(r"^(AT[\w+&%#$]*|OK|ERROR|\+[A-Z]+:)", l.strip())) for l in lines)
    return {"lines": n} if n >= 2 else None


def framing(b: bytes, max_period: int = 256) -> dict | None:
    """Fixed-length binary packets: a repeating period in the bytes, and a sync value that starts each one."""
    if len(b) < 64:
        return None
    x = np.frombuffer(b, dtype=np.uint8).astype(float)
    x = x - x.mean()
    if not x.any():
        return None
    best, period = 0.0, 0
    for p in range(2, min(max_period, len(x) // 3)):
        c = float(np.mean(x[:-p] * x[p:])) / float(np.mean(x * x))
        if c > best + 0.02:
            best, period = c, p
    if best < 0.3:
        return None
    arr = np.frombuffer(b, dtype=np.uint8)
    starts = [arr[i::period] for i in range(period)]
    constant = [i for i, s in enumerate(starts) if len(s) > 2 and len(set(s.tolist())) == 1]
    return {"period": period, "correlation": round(best, 3), "constant_offsets": constant[:8], "sync": [f"{int(starts[i][0]):02X}" for i in constant[:4]]}


def analyse(b: bytes) -> dict:
    """Measurements first, then every format check that applies."""
    n = len(b)
    text = b.decode("ascii", errors="replace")
    printable = sum(32 <= c < 127 or c in (9, 10, 13) for c in b) / n if n else 0.0
    lines = [l for l in re.split(r"\r\n|\n|\r", text) if l.strip()][-200:]
    e = entropy(b)
    found = {}
    if printable > 0.85:
        for name, fn in (("NMEA sentences (GPS, marine)", nmea), ("JSON lines", json_lines), ("Numeric columns (sensor readings)", numeric_columns), ("AT commands (modems, radio modules)", at_commands), ("Key and value pairs", key_values)):
            r = fn(lines)
            if r:
                found[name] = r
    else:
        f = framing(b)
        if f:
            found["Fixed-length binary packets"] = f
    if e > 7.6 and n >= 512:
        kind = "random, compressed or encrypted"
    elif printable > 0.85:
        kind = "text"
    elif e < 1.0:
        kind = "mostly constant (idle line or padding)"
    else:
        kind = "binary"
    ends = {"CR LF": text.count("\r\n"), "LF": text.count("\n") - text.count("\r\n"), "CR": text.count("\r") - text.count("\r\n")}
    top = Counter(b).most_common(6)
    return {"bytes": n, "entropy": round(e, 3), "printable": round(printable, 3), "kind": kind, "line_endings": {k: v for k, v in ends.items() if v}, "lines": len(lines), "top_bytes": [[f"{k:02X}", v] for k, v in top], "formats": found}
