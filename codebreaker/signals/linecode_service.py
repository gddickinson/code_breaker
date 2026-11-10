"""Which line code is this bitstream, and what does it carry? Examples, identification and the control."""
import json
import random

from ..languages import ROOT
from . import eightb10b as E, linecode as C, tmds as T

RESULT = ROOT / "data/results/linecode_control.json"
MAC_A, MAC_B = bytes.fromhex("02005e10a001"), bytes.fromhex("02005e10b002")


def example(kind: str, message: str = "Hello, wire", errors: int = 0, seed: int = 1) -> tuple[str, dict]:
    rnd, data = random.Random(seed), message.encode()[:200]
    if kind == "manchester":
        bits = C.manchester(C.bits_lsb(C.ethernet_frame(MAC_A, MAC_B, 0x88B5, data)))
        truth = {"code": "Manchester", "carrier": "10BASE-T Ethernet frame"}
    elif kind == "4b5b":
        bits = C.nrzi(C.encode_4b5b(data))
        truth = {"code": "4B5B", "carrier": "NRZI line, as on FDDI and 100BASE-FX"}
    elif kind == "8b10b":
        bits = E.encode(data)
        truth = {"code": "8b/10b", "carrier": "commas and data, as on gigabit Ethernet, SATA or PCIe 1-2"}
    else:
        bits = T.encode(data)
        truth = {"code": "TMDS", "carrier": "one HDMI or DVI data channel"}
    bits = "".join(rnd.choice("01") for _ in range(rnd.randint(0, 9))) + bits
    b = list(bits)
    for _ in range(errors):
        p = rnd.randrange(len(b))
        b[p] = "1" if b[p] == "0" else "0"
    return "".join(b), truth


SFD_BITS = C.bits_lsb(b"\x55\x55\xd5")  # the end of the preamble and the start frame delimiter, as sent


def ethernet_in(bits: str) -> dict | None:
    """Byte-align on the preamble's end and the start frame delimiter, then parse and check the frame."""
    i = bits.find(SFD_BITS)
    return C.parse_ethernet(C.bytes_lsb(bits[i:])) if i >= 0 else None


def text(values: list[int]) -> str:
    return "".join(chr(v) if 32 <= v < 127 else "." for v in values)


def identify(bits: str) -> list[dict]:
    """Decode with every code; rank by the share of symbols that are valid, with strong checks counting extra."""
    bits = "".join(c for c in bits if c in "01")
    rows = []
    m = C.unmanchester(bits)
    eth = ethernet_in(m["bits_ieee"])
    frac = 1 - m["invalid"] / max(m["symbols"], 1)
    rows.append({"code": "Manchester", "score": round(frac * (1.3 if eth and eth["crc_ok"] else 1.0) if frac > 0.97 else 0.0, 3), "valid": round(frac, 3), "detail": eth or {}, "bytes": eth["payload"] if eth else []})
    for name, dec, plain in (("4B5B", lambda s: C.decode_4b5b(C.unnrzi(s)), True), ("8b/10b", E.decode, True), ("TMDS", T.decode, True)):
        r = dec(bits)
        n = max(r.get("symbols", 0), 1)
        valid = 1 - (r.get("invalid", 0) + r.get("disparity_errors", 0)) / n if r.get("aligned") else 0.0
        strong = {"4B5B": 1.1, "8b/10b": 1.2, "TMDS": 1.0}[name]
        rows.append({"code": name, "score": round(valid * strong if valid > 0.9 and r.get("bytes") else 0.0, 3), "valid": round(valid, 3), "detail": {k: v for k, v in r.items() if k not in ("bytes", "code")}, "bytes": r.get("bytes", [])})
    for r in rows:
        r["text"] = text(r["bytes"])
    return sorted(rows, key=lambda r: -r["score"])


def stats(bits: str) -> dict:
    """Properties line codes exist to guarantee: short runs (clock recovery) and balance (no DC)."""
    runs, cur, n, bal, worst = [], bits[:1], 0, 0, 0
    for c in bits:
        if c == cur:
            n += 1
        else:
            runs.append(n)
            cur, n = c, 1
        bal += 1 if c == "1" else -1
        worst = max(worst, abs(bal))
    runs.append(n)
    return {"bits": len(bits), "longest_run": max(runs) if bits else 0, "ones_share": round(bits.count("1") / max(len(bits), 1), 3), "worst_imbalance": worst}


def control(trials: int = 48, seed: int = 4) -> dict:
    rnd, rows = random.Random(seed), []
    kinds = ["manchester", "4b5b", "8b10b", "tmds"]
    for t in range(trials):
        msg = "".join(rnd.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ") for _ in range(rnd.randint(8, 40)))
        bits, truth = example(kinds[t % 4], msg, 0, t)
        best = identify(bits)[0]
        rows.append({"kind": truth["code"], "got": best["code"], "ok": best["code"] == truth["code"], "bytes_ok": best["text"].startswith(msg)})
    return {"trials": trials, "code_ok": sum(r["ok"] for r in rows), "bytes_ok": sum(r["bytes_ok"] for r in rows), "rows": rows}


def reliability() -> dict:
    if not RESULT.exists():
        RESULT.write_text(json.dumps(control(), indent=1))
    d = json.loads(RESULT.read_text())
    return {k: d[k] for k in ("trials", "code_ok", "bytes_ok")}


def analyse(bits: str, truth: dict | None = None) -> dict:
    bits = "".join(c for c in bits if c in "01")[:400000]
    if len(bits) < 40:
        raise ValueError("Give at least 40 bits.")
    return {"stats": stats(bits), "ranking": identify(bits), "preview": bits[:400], "truth": truth or {}, "reliability": reliability()}
