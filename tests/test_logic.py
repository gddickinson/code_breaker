"""Logic Analyser: each decoder, protocol identification, CSV import and the API."""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from codebreaker.signals import logic_bus as B, logic_decode as D, logic_service as L, logic_synth as S
from codebreaker.web.app import app

client = TestClient(app)
MSG = b"Code Breaker 42!"
rnd = np.random.default_rng(3)


def text(r):
    return bytes(b["value"] for b in r["bytes"])


@pytest.mark.parametrize("baud,parity,invert", [(9600, "N", False), (115200, "E", False), (57600, "N", True)])
def test_uart_finds_baud_polarity_and_bytes(baud, parity, invert):
    ch = S.uart(MSG, baud, parity, invert).sample(baud * 16, rnd, 0.02 / baud, 3)
    r = D.uart(ch["RX"], baud * 16, parity=parity)
    assert (r["baud"], r["inverted"], text(r), r["errors"]) == (baud, invert, MSG, 0)


@pytest.mark.parametrize("mode", range(4))
def test_spi_finds_its_mode(mode):
    ch = S.spi(MSG, 1e6, mode).sample(8e6, rnd, 0, 2)
    r = D.spi(ch["CS"], ch["SCK"], ch["MOSI"], 8e6)
    assert r["mode"] == mode and text(r) == MSG


def test_i2c_address_and_acks():
    ch = S.i2c(0x3C, MSG, 400e3).sample(4e6, rnd, 0, 2)
    r = D.i2c(ch["SCL"], ch["SDA"], 4e6)
    assert r["messages"][0]["address"] == 0x3C and text(r) == MSG and r["errors"] == 0


def test_can_unstuffs_and_checks_crc():
    frames = [(0x123, b"\x01\x02\x03\xff"), (0x7FF, bytes(8))]
    r = B.can(S.can(frames, 500000).sample(8e6, rnd, 0, 2)["CAN"], 8e6)
    assert [(f["id"], bytes(f["data"]), f["crc_ok"]) for f in r["frames"]] == [(0x123, frames[0][1], True), (0x7FF, frames[1][1], True)]


def test_can_crc_catches_a_flipped_bit():
    bits = S.can_bits(0x10, b"AB")
    good = S.crc15(bits[:-15])
    bits[25] ^= 1
    assert S.crc15(bits[:-15]) != good


def test_onewire_reset_presence_and_bytes():
    r = B.onewire(S.onewire(b"\x33\x28").sample(1e6, rnd)["DQ"], 1e6)
    assert r["resets"] == 1 and r["presence"] == 1 and text(r) == b"\x33\x28"


@pytest.mark.parametrize("kind", ["uart", "spi", "i2c", "can", "onewire"])
def test_identify_names_the_protocol(kind):
    ch, rate, truth = L.example(kind, "IDENTIFY ME 7", 3, 5)
    best = L.identify(ch, rate)[0]
    assert best["protocol"] == truth["protocol"] and L.text_of(best) == "IDENTIFY ME 7"


def test_csv_import_round_trip():
    ch, rate, _ = L.example("uart", "CSV", 0, 1)
    x = ch["RX"]
    e = np.concatenate([[0], D.edges(x)])
    csv = "Time,RX\n" + "\n".join(f"{i / rate:.9f},{int(x[i])}" for i in e) + f"\n{(len(x) - 1) / rate:.9f},{int(x[-1])}\n"
    got, r2 = L.parse_csv(csv, rate)
    assert L.text_of(L.identify(got, r2)[0]) == "CSV"


def test_recorded_control_and_api():
    rel = L.reliability()
    assert rel["bytes_ok"] >= 0.9 * rel["trials"]
    r = client.post("/api/signals/logic", json={"example": "can", "message": "API test"}).json()
    assert r["ranking"][0]["protocol"] == "CAN" and r["ranking"][0]["text"] == "API test"
