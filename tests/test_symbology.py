"""Barcodes & QR page: every creatable code reads back, readers agree with each other, anatomy and damage controls."""
import base64

import cv2
import numpy as np
import pytest
import zxingcpp
from fastapi.testclient import TestClient

from codebreaker.signals import barcodes as B
from codebreaker.signals import symbology as S
from codebreaker.web.app import app


def _img(data_url):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data_url.split(",", 1)[1]), np.uint8), cv2.IMREAD_GRAYSCALE)


@pytest.mark.parametrize("kind", list(S.KINDS))
def test_every_kind_round_trips(kind):
    example = S.KINDS[kind][1]
    for ec in "LH":
        r = S.create(kind, example, ec)
        assert r["read_back"], kind
        if kind != "UPC-E":  # UPC-E reads back in its expanded UPC-A form
            assert example[:5] in r["read_back"][0]["text"]
        assert S.read_codes(_img(r["image"]))[0]["text"] == r["read_back"][0]["text"]


def test_readers_cross_check_ean():
    assert [c["text"] for c in S.read_codes(B.ean13_image("400638133393"))] == ["4006381333931"]
    z = np.array(zxingcpp.write_barcode_to_image(zxingcpp.create_barcode("501234567890", zxingcpp.BarcodeFormat.EAN13), scale=3))
    assert B.scan_ean(z) == ["5012345678900"]
    assert S.ean_steps("400638133393")["check"] == 1 and S.ean_steps("501234567890")["code"] == "5012345678900"


def test_opencv_reads_segno_qr():
    q = S.create("QR Code", "made by segno", "Q")["anatomy"]
    assert q["error_level"] == "Q"
    import segno

    m = np.array([[0 if v else 255 for v in row] for row in segno.make("opencv check", error="m", micro=False).matrix], np.uint8)
    img = cv2.copyMakeBorder(cv2.resize(m, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST), 32, 32, 32, 32, cv2.BORDER_CONSTANT, value=255)
    assert cv2.QRCodeDetector().detectAndDecode(img)[0] == "opencv check"
    assert cv2.QRCodeDetector().detectAndDecode(_img(S.create("QR Code", "zxing made", "M")["image"]))[0] == "zxing made"


def test_qr_anatomy_counts():
    a = S.qr_anatomy("Code Breaker", "H")
    assert a["size"] == 17 + 4 * a["version"]
    assert a["modules"]["finder patterns"] == 3 * 64 and a["modules"]["dark module"] == 1
    assert sum(a["modules"].values()) == a["size"] ** 2
    big = S.qr_anatomy("x" * 200, "M")
    assert big["version"] >= 7 and big["modules"]["version information"] == 36


def test_damage_orders_levels_and_has_control():
    d = S.damage_test(trials=6)
    assert d["clean_read"]
    lv = d["levels"]
    assert lv["H"]["largest_read"] > lv["L"]["largest_read"]
    assert lv["H"]["largest_read"] >= lv["Q"]["largest_read"] >= lv["M"]["largest_read"] >= lv["L"]["largest_read"]
    assert all(v["rates"][-1] == 0 for v in lv.values())  # a blot over a third of the symbol is never read


def test_blank_and_noise_find_nothing():
    rnd = np.random.default_rng(3)
    assert S.read_codes(np.full((300, 300), 255, np.uint8)) == []
    assert S.read_codes(rnd.integers(0, 256, (300, 300), dtype=np.uint8)) == []


def test_api():
    c = TestClient(app)
    assert len(c.get("/api/codes/kinds").json()) == len(S.KINDS)
    r = c.post("/api/codes/make", json={"kind": "Aztec", "text": "TICKET 1", "ec": "H"}).json()
    assert r["read_back"][0]["text"] == "TICKET 1"
    got = c.post("/api/codes/read", json={"image": r["image"]}).json()
    assert got["codes"][0]["format"] == "Aztec"
    assert c.post("/api/codes/make", json={"kind": "EAN-13", "text": "HELLO", "ec": "M"}).status_code == 400
    assert c.post("/api/codes/make", json={"kind": "Nope", "text": "x"}).status_code == 400
    assert c.post("/api/codes/read", json={"image": "data:image/png;base64,AAAA"}).status_code == 400
    assert c.get("/api/codes/damage?text=hello").json()["clean_read"]
