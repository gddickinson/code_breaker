"""Raw frame formats and detection, with the per-format control recorded honestly."""
import base64
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from codebreaker.signals import raw_detect as D, raw_formats as F, service as S
from codebreaker.web.app import app

client = TestClient(app)


@pytest.mark.parametrize("fmt", ["gray8", "gray16le", "gray16be", "raw10", "raw12", "kinect11"])
def test_round_trip_preserves_the_picture(fmt):
    img = D.scene(64, 32, 3)
    lum = F.luminance(F.encode(img, fmt), fmt)
    gray = img.mean(axis=2) if fmt == "gray8" else None
    assert len(lum) == 64 * 32
    assert np.corrcoef(lum, D.scene(64, 32, 3)[:, :, 1].reshape(-1))[0, 1] > 0.5


def test_kinect_bit_packing_is_exact():
    depth = np.array([[0, 1, 2047, 1024, 5, 600, 300, 7]], dtype=np.uint16)
    b = F.encode(depth, "kinect11")
    assert len(b) == 11
    assert np.allclose(F.luminance(b, "kinect11") * 2047, depth.reshape(-1))


@pytest.mark.parametrize("kind,w,h", [("kinect11", 640, 480), ("raw10", 752, 480), ("yuyv", 320, 240), ("rgb24", 176, 144), ("gray8", 640, 480)])
def test_reliable_formats_are_detected(kind, w, h):
    data, truth = D.example(kind, w, h, 9)
    got = D.detect(data)["best"]
    assert (got["format"], got["width"]) == (truth["format"], truth["width"])


def test_recorded_control_is_honest():
    rel = S.reliability()
    for k in ("kinect11", "raw10", "yuyv", "rgb24", "gray8"):
        assert rel[k]["correct"] == rel[k]["cases"]
    assert rel["bayer"]["correct"] < rel["bayer"]["cases"]


def test_api_example_analyse_and_render():
    e = client.get("/api/signals/example/kinect11").json()
    d = client.post("/api/signals/raw", json={"data": e["data"]}).json()
    assert d["best"]["format"] == "kinect11" and d["best"]["width"] == 640 and d["preview"].startswith("data:image/png")
    r = client.post("/api/signals/raw", json={"data": e["data"], "format": "gray8", "width": 100})
    assert r.status_code == 200 and r.json()["preview"].startswith("data:image/png")


def test_bad_input_is_rejected():
    assert client.post("/api/signals/raw", json={"data": ""}).status_code == 400
    assert client.get("/api/signals/example/nothing").status_code == 404
