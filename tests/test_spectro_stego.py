"""Round 82: pictures hidden in sound, revealed in the spectrogram."""
import base64
import json

import numpy as np
from fastapi.testclient import TestClient

from codebreaker.sound import spectro_stego as G
from codebreaker.sound.spectro_eval import RESULT, carrier
from codebreaker.web.app import app


def test_hidden_word_read_and_structure_raised():
    h = G.hide(G.text_image("SECRET"), seconds=4)
    noise = carrier("noise", len(h), 3)
    d = G.detect(G.mix(noise, h, 0))
    assert "SECRET" in [w["text"].upper() for w in d["words"]]
    thr = json.loads(RESULT.read_text())["carriers"]["noise"]["structure_threshold"]  # highest of 20 clean noises
    assert G.structure(G.mix(noise, h, -10)) > thr > G.structure(noise)
    assert not G.detect(noise)["words"]


def test_recorded_controls():
    r = json.loads(RESULT.read_text())["carriers"]
    assert r["noise"]["by_level_db"]["-10"]["structure_detected"] >= 0.9 and r["noise"]["by_level_db"]["0"]["ocr_read_word"] >= 0.9
    assert all(v["ocr_false_alarms_on_clean"] == 0 for v in r.values())


def test_routes():
    c = TestClient(app)
    r = c.post("/api/sounds/hide", json={"text": "CODE", "carrier": "sweep", "level": -5}).json()
    assert r["wav"].startswith("data:audio/wav;base64,")
    d = c.post("/api/sounds/reveal", json={"data": r["wav"]}).json()
    assert "words" in d and d["structure"] > 0
    assert c.post("/api/sounds/hide", json={"text": "x" * 50}).status_code == 400
