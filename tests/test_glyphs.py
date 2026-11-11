"""Round 78: glyph rendering, the scanner's segmentation and, when the model is trained, recognition."""
import base64
import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from codebreaker.web.app import app
from codebreaker.writing import glyph_model as M
from codebreaker.writing import glyph_render as R
from codebreaker.writing import glyph_scan as S
from codebreaker.writing.glyph_eval import page

needs_model = pytest.mark.skipif(M.load() is None, reason="glyph model not trained (python -m codebreaker.writing.glyph_model)")


def test_classes_drawn_and_merged():
    cls = R.classes()
    scripts = {c["script"] for c in cls}
    assert len(cls) > 2700 and {"egyptian", "linear_b", "runic", "ogham", "cuneiform"} <= scripts
    assert any(len(c["signs"]) > 1 for c in cls)  # identical drawings merged


def test_distortions_keep_the_sign():
    rnd = np.random.default_rng(0)
    a = R.raw(R.classes()[0]["signs"][0], R.classes()[0]["script"])
    for kind in ("normal", "hard", "unseen", "train"):
        img = R.sample(a, rnd, kind)
        assert img.shape == (R.SIZE, R.SIZE) and img.max() > 100


def test_segmentation_and_order_on_a_page():
    img, truth = page("linear_b", np.random.default_rng(3))
    bx = S.reading_order(S.boxes(S.ink_mask(img)))
    assert len(bx) == len(truth)
    assert [b[1] < img.shape[0] / 2 for b in bx] == [True] * 6 + [False] * 6


def test_blank_paper_has_no_signs():
    rnd = np.random.default_rng(5)
    img = np.clip(rnd.normal(215, 12, (180, 420)) + cv2.GaussianBlur(rnd.normal(0, 25, (180, 420)), (0, 0), 6), 0, 255).astype(np.uint8)
    assert not S.boxes(S.ink_mask(img))


@needs_model
def test_recognition_on_a_page_and_api():
    img, truth = page("runic", np.random.default_rng(11))
    res = S.scan(img, ["runic"])
    want = ["".join(R.classes()[k]["signs"]) for k, _ in truth]
    got = ["".join([s["candidates"][0]["sign"]] + s["candidates"][0]["also"]) for s in res["signs"]]
    assert sum(a == b for a, b in zip(got, want)) >= 10
    ok, enc = cv2.imencode(".png", img)
    r = TestClient(app).post("/api/writing/scan", json={"image": "data:image/png;base64," + base64.b64encode(enc).decode(), "scripts": ["runic"]})
    assert r.status_code == 200 and len(r.json()["signs"]) == 12


@needs_model
def test_recorded_evaluation():
    res = json.loads(M.RESULT.read_text())
    assert res["held_out"]["top5"] > 0.95 and res["threshold"] < 0.8 and res["unseen"]["top5"] > 0.8
    assert "unseen" in res
