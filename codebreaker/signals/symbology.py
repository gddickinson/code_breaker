"""Barcodes and 2D codes: make them, read them, show how a QR code is laid out, and test its error correction.
Uses zxing-cpp (many symbologies) and segno (QR details), cross-checked with the app's own EAN-13 code."""
import base64

import cv2
import numpy as np
import segno
import zxingcpp
from segno import consts

from . import barcodes as own

F = zxingcpp.BarcodeFormat
# name: (format, example, family, what it is for)
KINDS = {
    "QR Code": (F.QRCode, "https://example.org/code-breaker", "matrix", "Phones, tickets, payments; up to 7,089 digits with four levels of error correction."),
    "Micro QR": (F.MicroQRCode, "CB-2026", "matrix", "A small QR with one finder pattern, for tiny parts and labels."),
    "Data Matrix": (F.DataMatrix, "PART-0042-LOT-7", "matrix", "Marking electronic parts, medicines and aircraft parts; very small and robust."),
    "Aztec": (F.Aztec, "TICKET 12345 SEAT 7C", "matrix", "Rail and airline boarding passes; a central bullseye means no quiet zone is needed."),
    "PDF417": (F.PDF417, "DRIVER LICENCE DATA 1234567890", "stacked", "Stacked rows of a linear code; identity cards, driving licences and boarding passes."),
    "Code 128": (F.Code128, "SHIP-2026-11-09", "linear", "Shipping and logistics labels; all 128 ASCII characters with a modulo-103 check."),
    "Code 39": (F.Code39, "CODE-39", "linear", "Industry and defence labels; letters, digits and a few symbols, self-checking."),
    "Code 93": (F.Code93, "CODE93", "linear", "A denser successor to Code 39 with two check characters."),
    "Codabar": (F.Codabar, "A12345B", "linear", "Libraries and blood banks; digits and a few symbols between start and stop letters."),
    "ITF": (F.ITF, "12345678901231", "linear", "Interleaved 2 of 5: pairs of digits in bars and spaces; outer cartons (ITF-14)."),
    "EAN-13": (F.EAN13, "400638133393", "linear", "Retail products worldwide; 12 digits plus a check digit. Books use the 978 or 979 prefix."),
    "EAN-8": (F.EAN8, "9638507", "linear", "Small retail packs; 7 digits plus a check digit."),
    "UPC-A": (F.UPCA, "03600029145", "linear", "Retail products in North America; 11 digits plus a check digit."),
    "UPC-E": (F.UPCE, "0425261", "linear", "A compressed UPC for small packs."),
}


# Error-correction choices offered as L/M/Q/H; Aztec takes a percentage and PDF417 a level from 0 to 8.
EC_MAP = {"QR Code": {e: e for e in "LMQH"}, "Micro QR": {"L": "L", "M": "M", "Q": "Q", "H": "Q"},
          "Aztec": {"L": "10", "M": "23", "Q": "36", "H": "50"}, "PDF417": {"L": "2", "M": "4", "Q": "5", "H": "6"}}


def png(img: np.ndarray, scale: int = 1) -> str:
    if scale > 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    ok, buf = cv2.imencode(".png", img)
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode()


def create(kind: str, text: str, ec: str = "M") -> dict:
    fmt, _, family, _ = KINDS[kind]
    opts = {"ec_level": EC_MAP[kind][ec]} if kind in EC_MAP else {}
    try:
        b = zxingcpp.create_barcode(text, fmt, **opts)
    except Exception as exc:  # the text is not allowed in this symbology
        raise ValueError(f"{kind} cannot hold that text: {exc}") from exc
    img = np.array(zxingcpp.write_barcode_to_image(b, scale=4 if family != "linear" else 3, add_quiet_zones=True))
    if kind == "QR Code":  # drawn from segno so the picture is the same symbol as the anatomy below it
        q = segno.make(text, error=ec.lower(), micro=False, boost_error=False)
        m = np.array([[0 if v else 255 for v in row] for row in q.matrix], np.uint8)
        img = cv2.copyMakeBorder(cv2.resize(m, None, fx=5, fy=5, interpolation=cv2.INTER_NEAREST), 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
    if family == "linear":
        img = cv2.resize(img, (img.shape[1], 140), interpolation=cv2.INTER_NEAREST)
    read = read_codes(img)
    out = {"kind": kind, "text": read[0]["text"] if read else b.text, "image": png(img), "read_back": read, "family": family}
    if kind == "QR Code":
        out["anatomy"] = qr_anatomy(text, ec)
    if kind in ("EAN-13",):
        out["check"] = ean_steps(b.text[:12])
    return out


def read_codes(img: np.ndarray) -> list[dict]:
    """zxing-cpp reads every supported symbology; EAN and UPC results are also checked against their check digit."""
    res = []
    for r in zxingcpp.read_barcodes(img):
        item = {"format": str(r.format).split(".")[-1], "text": r.text, "ec_level": r.ec_level or "", "symbology": r.symbology_identifier, "valid": bool(r.valid)}
        if item["format"].replace("-", "") in ("EAN13", "UPCA"):
            item["check_digit_ok"] = own.ean_valid(r.text)
        res.append(item)
    return res


def ean_steps(d12: str) -> dict:
    """The check digit: weights 1 and 3 alternately, then whatever brings the total to a multiple of 10."""
    rows = [[i + 1, int(c), 1 if i % 2 == 0 else 3, int(c) * (1 if i % 2 == 0 else 3)] for i, c in enumerate(d12)]
    total = sum(r[3] for r in rows)
    check = (10 - total % 10) % 10
    first = own.FIRST[int(d12[0])]
    return {"rows": rows, "total": total, "check": check, "code": d12 + str(check), "parity": first, "note": f"The first digit, {d12[0]}, is not drawn as bars: it is carried by the pattern of L and G codes in the left half ({first})."}


def qr_anatomy(text: str, ec: str = "M", cell: int = 12) -> dict:
    """The QR matrix with each kind of module coloured: finders, timing, alignment, format and version information, data."""
    q = segno.make(text, error=ec.lower(), micro=False, boost_error=False)
    m = np.array([list(r) for r in q.matrix], dtype=np.uint8)
    n, v = m.shape[0], q.version
    kind = np.zeros_like(m)  # 0 data, 1 finder and separator, 2 timing, 3 alignment, 4 format, 5 version, 6 dark module
    for r0, c0 in ((0, 0), (0, n - 8), (n - 8, 0)):
        kind[r0:r0 + 8, c0:c0 + 8] = 1
    kind[6, 8:n - 8], kind[8:n - 8, 6] = 2, 2
    pos = consts.ALIGNMENT_POS[v - 1] if v > 1 else []
    for r in pos:
        for c in pos:
            if kind[r, c] != 1:
                kind[r - 2:r + 3, c - 2:c + 3] = 3
    for i in list(range(0, 9)) + list(range(n - 8, n)):
        if kind[8, i] == 0:
            kind[8, i] = 4
        if kind[i, 8] == 0:
            kind[i, 8] = 4
    if v >= 7:
        kind[0:6, n - 11:n - 8] = 5
        kind[n - 11:n - 8, 0:6] = 5
    kind[n - 8, 8] = 6
    colours = {0: (0, 160, 90), 1: (180, 60, 230), 2: (0, 170, 230), 3: (255, 120, 40), 4: (200, 200, 60), 5: (60, 140, 140), 6: (220, 0, 0)}  # RGB, as in barcodes_info.js
    img = np.full((n * cell, n * cell, 3), 255, np.uint8)
    for r in range(n):
        for c in range(n):
            col = colours[int(kind[r, c])]
            fill = tuple(int(x * 0.45) for x in col) if m[r, c] else tuple(int(255 - (255 - x) * 0.25) for x in col)
            img[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell] = fill[::-1]
    counts = {name: int((kind == k).sum()) for k, name in enumerate(["data and error correction", "finder patterns", "timing", "alignment", "format information", "version information", "dark module"])}
    return {"image": png(img), "version": v, "size": n, "error_level": q.error, "mask": q.mask, "mode": q.mode, "modules": counts}


def _qr_read(mod: np.ndarray, text: str) -> bool:
    big = cv2.resize(mod, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST)
    big = cv2.copyMakeBorder(big, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255)
    return any(r.text == text for r in zxingcpp.read_barcodes(big))


def damage_test(text: str = "https://example.org/code-breaker", trials: int = 8, seed: int = 1) -> dict:
    """Cover a growing square of the symbol with random noise (a stain or a logo), away from the three finder patterns.
    Reports, for each error-correction level, the share of trials read at each blot size. Scattered single-module
    noise is a harsher test: it spoils many codewords at once and can hit the finders and format bits."""
    rnd = np.random.default_rng(seed)
    shares = [round(x, 2) for x in np.arange(0.02, 0.36, 0.04)]
    out = {}
    for ec in "LMQH":
        q = segno.make(text, error=ec.lower(), micro=False, boost_error=False)
        base = np.array([[0 if v else 255 for v in row] for row in q.matrix], np.uint8)
        n = base.shape[0]
        rates = []
        for share in shares:
            s = int(round(np.sqrt(share) * n))
            ok = 0
            for _ in range(trials):
                img = base.copy()
                y, x = rnd.integers(8, max(9, n - 8 - s + 1), 2)
                img[y:y + s, x:x + s] = rnd.choice(np.array([0, 255], np.uint8), (s, s))
                ok += _qr_read(img, text)
            rates.append(ok / trials)
        survived = [sh for sh, r in zip(shares, rates) if r >= 0.5]
        out[ec] = {"version": q.version, "rates": rates, "largest_read": float(max(survived)) if survived else 0.0}
    clean = segno.make(text, error="l", micro=False, boost_error=False)
    control = _qr_read(np.array([[0 if v else 255 for v in row] for row in clean.matrix], np.uint8), text)
    return {"shares": shares, "levels": out, "clean_read": control, "nominal": {"L": 0.07, "M": 0.15, "Q": 0.25, "H": 0.30}}
