"""Audio Signals and infrared: published check values, decoding at several noise levels, nulls, and the APIs."""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from codebreaker.signals import audio_codes as A, audio_service as S, ax25 as X, ir as IR, logic_service as L
from codebreaker.web.app import app

client = TestClient(app)
rnd = np.random.default_rng(4)


def test_x25_crc_matches_the_published_check_value():
    assert X.crc_x25(b"123456789") == 0x906E


def test_dtmf_all_sixteen_keys():
    assert A.dtmf_decode(A.dtmf_tones("0123456789*#ABCD", rnd))["text"] == "0123456789*#ABCD"


@pytest.mark.parametrize("wpm", [8, 15, 25, 35])
def test_morse_at_several_speeds(wpm):
    r = A.morse_decode(A.morse_audio("CQ DE CODE BREAKER", wpm, rnd, noise=0.1))
    assert r["text"] == "CQ DE CODE BREAKER" and abs(r["wpm"] - wpm) / wpm < 0.15


def test_aprs_packet_through_afsk():
    f = X.frame("N0CALL-9", "APRS", "!4903.50N/07201.75W-Test")
    p = X.deframe(X.demodulate(X.afsk(f, rnd, 0.2)))[0]
    assert p["crc_ok"] and p["source"] == "N0CALL-9" and p["path"] == ["WIDE1-1"] and p["info"].endswith("Test")


def test_noise_decodes_as_nothing():
    noise = np.random.default_rng(9).normal(0, 0.3, 24000).astype(np.float32)
    assert all(r["score"] == 0 for r in S.identify(noise, 8000))


@pytest.mark.parametrize("make,decode,addr,cmd", [(IR.nec, IR.decode_nec, 0x04, 0x5A), (IR.rc5, IR.decode_rc5, 0x05, 0x23)])
def test_infrared_codes(make, decode, addr, cmd):
    f = decode(make(addr, cmd).sample(200e3, rnd, 0, 2)["IR"], 200e3)["frames"][0]
    assert (f["address"], f["command"], f["ok"]) == (addr, cmd, True)


def test_recorded_controls_and_apis():
    a, lg = S.reliability(), L.reliability()
    assert a["correct"] >= 0.9 * a["trials"] and a["null_decoded"] == 0 and lg["bytes_ok"] >= 0.95 * lg["trials"]
    r = client.post("/api/signals/audio", json={"example": "aprs", "message": "API", "noise": 0.1}).json()
    assert r["ranking"][0]["code"].startswith("APRS") and r["audio"].startswith("data:audio/wav")
    assert client.post("/api/signals/audio", json={"example": "nope"}).status_code == 400
    assert client.post("/api/signals/logic", json={"example": "nec", "message": "Z"}).json()["ranking"][0]["protocol"] == "NEC infrared"
