"""Barcodes and QR codes in images: EAN-13 drawn from its definition (for tests) and read back with OpenCV,
with every EAN result checked against its check digit."""
import cv2
import numpy as np

L = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011"]
G = ["0100111", "0110011", "0011011", "0100001", "0011101", "0111001", "0000101", "0010001", "0001001", "0010111"]
R = ["".join("1" if c == "0" else "0" for c in x) for x in L]
FIRST = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG", "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]


def ean_check(d12: str) -> int:
    return (10 - sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d12)) % 10) % 10


def ean_valid(code: str) -> bool:
    return len(code) == 13 and code.isdigit() and ean_check(code[:12]) == int(code[12])


def ean13_image(d12: str, module: int = 3, height: int = 120) -> np.ndarray:
    """Quiet zone, guard bars, six left digits in L or G code (the pattern encodes the first digit), six right digits in R code."""
    code = d12 + str(ean_check(d12))
    left = "".join((L if p == "L" else G)[int(c)] for p, c in zip(FIRST[int(code[0])], code[1:7]))
    right = "".join(R[int(c)] for c in code[7:])
    bits = "0" * 11 + "101" + left + "01010" + right + "101" + "0" * 11
    row = np.array([0 if b == "1" else 255 for b in bits], np.uint8).repeat(module)
    img = np.tile(row, (height, 1))
    return cv2.copyMakeBorder(img, 20, 20, 0, 0, cv2.BORDER_CONSTANT, value=255)


def qr_image(text: str, scale: int = 8) -> np.ndarray:
    q = cv2.QRCodeEncoder.create().encode(text)
    q = cv2.resize(q, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    return cv2.copyMakeBorder(q, 4 * scale, 4 * scale, 4 * scale, 4 * scale, cv2.BORDER_CONSTANT, value=255)


def read_codes(img: np.ndarray) -> list[dict]:
    """Every code OpenCV, the own EAN reader and zxing-cpp find; EAN and UPC results that fail their check digit are dropped."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    out = []
    try:
        ok, texts, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(gray)
        if ok:
            out += [{"type": "QR code", "text": t} for t in texts if t]
    except cv2.error:
        pass
    for code in scan_ean(gray):
        out.append({"type": "EAN-13", "text": code})
    try:  # zxing-cpp adds Data Matrix, Aztec, PDF417, Code 128 and the rest (see symbology.py)
        import zxingcpp

        found = {c["text"] for c in out}
        for r in zxingcpp.read_barcodes(gray):
            name = str(r.format).split(".")[-1]
            if r.text and r.text not in found and not (name in ("EAN-13", "UPC-A", "EAN13", "UPCA") and not ean_valid(r.text.zfill(13))):
                out.append({"type": "QR code" if name in ("QRCode", "QR Code") else name, "text": r.text})
                found.add(r.text)
    except ImportError:
        pass
    seen, unique = set(), []
    for c in out:
        if (c["type"], c["text"]) not in seen:
            seen.add((c["type"], c["text"]))
            unique.append(c)
    return unique


def _widths(code: str) -> tuple:
    """A 7-module digit pattern as the widths of its four runs."""
    runs, cur, n = [], code[0], 0
    for c in code:
        if c == cur:
            n += 1
        else:
            runs.append(n)
            cur, n = c, 1
    return tuple(runs + [n])


# R patterns are L patterns inverted, so they share bar widths: which table applies depends on the side of the code.
LEFT = {**{_widths(x): (str(d), "L") for d, x in enumerate(L)}, **{_widths(x): (str(d), "G") for d, x in enumerate(G)}}
RIGHT = {_widths(x): (str(d), "R") for d, x in enumerate(R)}


def _digit(runs: list[float], unit: float, right: bool):
    w = [max(1, round(r / unit)) for r in runs]
    if sum(w) != 7:
        w = [max(1, round(r / sum(runs) * 7)) for r in runs]
    return (RIGHT if right else LEFT).get(tuple(w))


def _scan_row(row: np.ndarray) -> str | None:
    """Run lengths along one row; find the start guard, read 12 digits, and accept only a valid check digit."""
    b = (row < (int(row.min()) + int(row.max())) / 2).astype(np.int8)
    e = np.flatnonzero(np.diff(b)) + 1
    if len(e) < 60:
        return None
    runs = np.diff(e).astype(float)
    starts = [i for i in range(len(runs) - 58) if b[e[i]] == 1]
    for i in starts:
        unit = runs[i:i + 3].mean()
        if not all(0.5 * unit < r < 1.6 * unit for r in runs[i:i + 3]):
            continue
        j, digits, kinds = i + 3, [], []
        for k in range(12):
            if k == 6:
                j += 5
            got = _digit(list(runs[j:j + 4]), unit, k >= 6)
            if got is None:
                break
            digits.append(got[0])
            kinds.append(got[1])
            j += 4
        if len(digits) != 12 or "R" in kinds[:6] or any(k != "R" for k in kinds[6:]):
            continue
        first = "".join(kinds[:6])
        if first not in FIRST:
            continue
        code = str(FIRST.index(first)) + "".join(digits)
        if ean_valid(code):
            return code
    return None


def scan_ean(gray: np.ndarray, angles=(0, -6, 6, -12, 12, -20, 20, -28, 28)) -> list[str]:
    """Scan rows of the image at several rotations; any decode must pass its check digit."""
    h, w = gray.shape
    found = []
    for a in angles:
        img = gray if a == 0 else cv2.warpAffine(gray, cv2.getRotationMatrix2D((w / 2, h / 2), a, 1), (w, h), borderValue=255)
        for y in np.linspace(h * 0.2, h * 0.8, 15).astype(int):
            code = _scan_row(img[y])
            if code and code not in found:
                found.append(code)
        if found:
            break
    return found


def degrade(img: np.ndarray, rnd: np.random.Generator, angle: float = 0.0, blur: float = 0.0, noise: float = 0.0) -> np.ndarray:
    pad = cv2.copyMakeBorder(img, 60, 60, 60, 60, cv2.BORDER_CONSTANT, value=255)
    h, w = pad.shape[:2]
    out = cv2.warpAffine(pad, cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1), (w, h), borderValue=255)
    if blur:
        out = cv2.GaussianBlur(out, (0, 0), blur)
    return np.clip(out + rnd.normal(0, noise, out.shape), 0, 255).astype(np.uint8)


def control(trials: int = 30, seed: int = 2) -> dict:
    """QR and EAN-13 images, tilted up to 25 degrees, blurred and noisy; plus blank and random images that must read nothing."""
    import random

    rnd, r = np.random.default_rng(seed), random.Random(seed)
    qr = ean = wrong = 0
    for t in range(trials):
        ang, bl, nz = r.uniform(-25, 25), r.choice([0, 0.8, 1.5]), r.choice([0, 10, 25])
        msg = f"https://example.org/item/{t}"
        qr += any(c["text"] == msg for c in read_codes(degrade(qr_image(msg), rnd, ang, bl, nz)))
        d12 = "".join(str(r.randrange(10)) for _ in range(12))
        got = read_codes(degrade(ean13_image(d12), rnd, ang, bl, nz))
        ean += any(c["text"] == d12 + str(ean_check(d12)) for c in got)
        wrong += any(c["type"] == "EAN-13" and c["text"] != d12 + str(ean_check(d12)) for c in got)
    nulls = [read_codes((rnd.random((400, 400)) * 255).astype(np.uint8)) for _ in range(5)] + [read_codes(np.full((300, 300), 255, np.uint8))]
    return {"trials": trials, "qr_read": qr, "ean_read": ean, "ean_wrong": wrong, "null_images": len(nulls), "null_codes": sum(len(x) for x in nulls)}
