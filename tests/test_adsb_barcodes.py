"""ADS-B against published worked examples, single-bit repair, the traffic scene; barcodes and QR codes."""
import base64
import io
import json

import numpy as np
from fastapi.testclient import TestClient

from codebreaker.languages import ROOT
from codebreaker.signals import adsb_service as A, barcodes as B, modes as M
from codebreaker.web.app import app

client = TestClient(app)


def test_published_identification_position_and_velocity():
    i = M.decode("8D4840D6202CC371C32CE0576098")
    assert i["crc_ok"] and i["icao"] == "4840D6" and i["callsign"] == "KLM1023"
    e, o = M.decode("8D40621D58C382D690C8AC2863A7"), M.decode("8D40621D58C386435CC412692AD6")
    assert e["altitude_ft"] == 38000 and M.cpr_global(e["cpr"], o["cpr"], False) == (52.2572, 3.91937)
    v = M.decode("8D485020994409940838175B284F")
    assert (v["speed_kt"], v["heading_deg"], v["vertical_rate_fpm"]) == (159.2, 182.88, -832)


def test_single_bit_repair_and_rejection():
    good = M.bits_of("8D4840D6202CC371C32CE0576098")
    one = good[:40] + ("1" if good[40] == "0" else "0") + good[41:]
    assert M.repair(one) == (good, 40)
    two = one[:50] + ("1" if one[50] == "0" else "0") + one[51:]
    assert M.repair(two)[0] in ("", good) and M.repair(two)[0] != two


def test_encoders_round_trip_through_the_radio_signal():
    r = A.run(5, 0.05, 9)
    assert r["aircraft_right"] == 5 and r["decoded"] == r["messages"]


def test_recorded_adsb_control_and_noise():
    c = A.reliability()
    assert c["null_frames"] == 0 and c["aircraft_right"] >= 0.45 * c["aircraft"]
    low = [r for r in c["rows"] if r["noise"] <= 0.1]
    assert all(r["aircraft_right"] == 6 for r in low)


def test_ean13_reference_and_reading():
    assert B.ean_check("400638133393") == 1 and B.ean_valid("4006381333931") and not B.ean_valid("4006381333932")
    assert B.read_codes(B.ean13_image("400638133393")) == [{"type": "EAN-13", "text": "4006381333931"}]
    rnd = np.random.default_rng(3)
    assert B.read_codes(B.degrade(B.ean13_image("501234567890"), rnd, 15, 1.0, 15))[0]["text"] == "5012345678900"


def test_qr_and_nulls():
    assert B.read_codes(B.qr_image("hello code breaker"))[0]["text"] == "hello code breaker"
    assert B.read_codes(np.full((300, 300), 255, np.uint8)) == []


def test_file_inspector_reads_codes_in_pictures():
    from PIL import Image

    from codebreaker.files import service as S

    buf = io.BytesIO()
    Image.fromarray(B.qr_image("inspect me")).save(buf, "PNG")
    r = S.inspect_upload("code.png", base64.b64encode(buf.getvalue()).decode())
    assert "inspect me" in r["view"]["facts"].get("Codes found", "")


def test_api():
    r = client.post("/api/signals/adsb", json={"hex": "8D4840D6202CC371C32CE0576098"}).json()
    assert r["planes"][0]["callsign"] == "KLM1023"
    assert client.post("/api/signals/adsb", json={"hex": "XYZ"}).status_code == 400
