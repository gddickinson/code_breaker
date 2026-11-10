"""Line codes: published reference values, round trips, code properties, identification and the API."""
import random

import pytest
from fastapi.testclient import TestClient

from codebreaker.signals import eightb10b as E, linecode as C, linecode_service as L, tmds as T
from codebreaker.web.app import app

client = TestClient(app)
DATA = bytes(random.Random(1).randrange(256) for _ in range(400))


def test_reference_symbols_and_crc():
    assert E.encode_byte(0xBC, -1, k=28)[0] == "0011111010" and E.encode_byte(0xBC, 1, k=28)[0] == "1100000101"
    assert E.encode_byte(0xB5, -1)[0] == "1010101010" and E.encode_byte(0x00, -1)[0] == "1001110100"
    assert C.crc32(b"123456789") == 0xCBF43926
    assert "".join(map(str, reversed(T.control_bits(0, 0)))) == "1101010100"


def test_8b10b_round_trip_and_guarantees():
    s = E.encode(DATA)
    d = E.decode("101" + s)
    assert bytes(d["bytes"]) == DATA and d["invalid"] == 0 and d["disparity_errors"] == 0
    assert max(len(r) for r in s.replace("0", " ").split() + s.replace("1", " ").split()) <= 5


def test_8b10b_flags_a_flipped_bit():
    s = list(E.encode(DATA[:50]))
    s[200] = "1" if s[200] == "0" else "0"
    d = E.decode("".join(s))
    assert d["invalid"] + d["disparity_errors"] >= 1


def test_tmds_round_trip_balance_and_transitions():
    cnt, worst, trans = 0, 0, 0
    for b in range(256):
        q, cnt = T.encode_byte(b, cnt)
        worst, trans = max(worst, abs(cnt)), max(trans, sum(a != c for a, c in zip(q[:8], q[1:8])))
    assert worst <= 10 and trans <= 4
    assert bytes(T.decode("1" + T.encode(DATA))["bytes"]) == DATA


def test_4b5b_and_manchester_round_trips():
    assert bytes(C.decode_4b5b(C.unnrzi(C.nrzi(C.encode_4b5b(DATA[:60]))))["bytes"]) == DATA[:60]
    frame = C.ethernet_frame(b"\x02" * 6, b"\x04" * 6, 0x0800, b"payload")
    m = C.unmanchester("1" + C.manchester(C.bits_lsb(frame)))
    assert m["invalid"] == 0 and L.ethernet_in(m["bits_ieee"])["crc_ok"]


@pytest.mark.parametrize("kind", ["manchester", "4b5b", "8b10b", "tmds"])
def test_identification(kind):
    bits, truth = L.example(kind, "IDENTIFY THIS STREAM", 0, 9)
    best = L.identify(bits)[0]
    assert best["code"] == truth["code"] and best["text"].startswith("IDENTIFY THIS STREAM")


def test_recorded_control_and_api():
    rel = L.reliability()
    assert rel["bytes_ok"] >= 0.9 * rel["trials"]
    r = client.post("/api/signals/linecode", json={"example": "tmds", "message": "HDMI"}).json()
    assert r["ranking"][0]["code"] == "TMDS" and r["ranking"][0]["text"].startswith("HDMI")
    assert client.post("/api/signals/linecode", json={"bits": "0101"}).status_code == 400
