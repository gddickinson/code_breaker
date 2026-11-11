"""Round 79: which script a set of signs belongs to, the drawing pad, and real photographs."""
import base64
import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from codebreaker.web.app import app
from codebreaker.writing import glyph_model as M
from codebreaker.writing import script_id as S
from codebreaker.writing import sketch as K

needs_model = pytest.mark.skipif(M.load() is None, reason="glyph model not trained")


def test_script_id_recorded():
    r = json.loads(S.RESULT.read_text())["results"]
    assert r["clean_4"]["accuracy"] >= 0.95 and r["clean_1"]["accuracy"] >= 0.9
    for n in (1, 4, 12):  # under unseen distortions it abstains rather than naming a wrong script
        v = r[f"unseen_{n}"]
        assert v["accuracy"] + v["abstained"] >= 0.95
    assert json.loads(S.RESULT.read_text())["non_script_controls"]["blobs"]["named_a_script"] <= 0.05


def test_sketch_recorded():
    assert json.loads(K.RESULT.read_text())["mean_top5_within_script"] >= 0.85


def test_skeleton_is_thin():
    a = np.zeros((60, 60), np.uint8)
    cv2.rectangle(a, (10, 25), (50, 35), 255, -1)
    assert 0 < (K.skeleton(a) > 0).sum() < 0.3 * (a > 0).sum()


@needs_model
def test_pad_and_script_routes():
    from codebreaker.writing.glyph_render import classes, raw
    cls = classes()
    k = next(i for i, c in enumerate(cls) if c["script"] == "runic" and c["signs"][0] == "ᚠ")
    img = 255 - K.fit(K.skeleton(K.fit(raw("ᚠ", "runic"), 192, 20)), 280, 30)
    img = cv2.dilate(255 - img, np.ones((7, 7), np.uint8))
    url = "data:image/png;base64," + base64.b64encode(cv2.imencode(".png", 255 - img)[1]).decode()
    c = TestClient(app)
    r = c.post("/api/writing/sketch", json={"image": url, "scripts": ["runic"]}).json()
    assert "ᚠ" in [x["sign"] for x in r["candidates"][:5]]
    assert c.post("/api/writing/script_of", json={"signs": "ᚠᚢᚦ 𓄿"}).json()["counts"]["Runes"] == 3


def test_photo_finetune_recorded():
    from codebreaker.writing.glyph_photo_train import RESULT
    r = json.loads(RESULT.read_text())
    assert r["after"]["photos_top1_top5"][0] > 0.8 and r["before"]["photos_top1_top5"][0] < 0.1
    assert r["after"]["font_top1"] >= r["before"]["font_top1"] - 0.01 and r["test_photos"] > 500
