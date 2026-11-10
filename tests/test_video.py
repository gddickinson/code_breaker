"""Video Signals: every mode decodes, unknown timing and noise are refused, composite decodes, and the API."""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from codebreaker.signals import video as V, video_service as S
from codebreaker.signals.raw_detect import scene
from codebreaker.web.app import app

client = TestClient(app)


@pytest.mark.parametrize("mode", list(V.MODES))
def test_each_mode_is_identified_and_rebuilt(mode):
    r = S.example(mode, 1.17, 0.03, 4)
    assert r["ok"] and r["mode"] == mode and r["match"] > 0.9


def test_published_line_rates():
    assert abs(V.MODES["640x480 @ 60 Hz"][8] / 800 - 31469) < 2
    assert abs(V.MODES["1024x768 @ 60 Hz"][8] / 1344 - 48363) < 2


def test_noise_and_unknown_timing_are_refused():
    rnd = np.random.default_rng(3)
    ch = {c: rnd.normal(0.3, 0.2, 300000).astype(np.float32) for c in "RGB"}
    ch["HSYNC"], ch["VSYNC"] = (rnd.random(300000) > 0.5).astype(np.float32), (rnd.random(300000) > 0.9).astype(np.float32)
    assert not V.vga_decode(ch, 25e6)["ok"]
    V.MODES["test custom"] = (640, 16, 64, 120, 480, 1, 3, 16, 31.5e6, False, False)
    try:
        ch, fs = V.vga_signal(scene(640, 480, 1), "test custom", 1.0, 0.02, rnd)
    finally:
        del V.MODES["test custom"]
    r = V.vga_decode(ch, fs)
    assert not r["ok"] and "no standard mode" in r["reason"]


def test_composite_and_recorded_control():
    r = S.example("composite", 1.0, 0.02, 6)
    assert r["ok"] and r["match"] > 0.85 and 15.6 < r["measured"]["line_khz"] < 15.8
    rel = S.reliability()
    assert rel["decoded"] == rel["cases"] and rel["null_decoded"] == 0


def test_api():
    r = client.post("/api/signals/video", json={"kind": "800x600 @ 60 Hz"}).json()
    assert r["mode"] == "800x600 @ 60 Hz" and r["image"].startswith("data:image/png")
    assert client.post("/api/signals/video", json={"kind": "nonsense"}).status_code == 400
