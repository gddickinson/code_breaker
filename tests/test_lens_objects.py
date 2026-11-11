"""Round 90b: object understanding and tracking (no AI needed for these tests)."""
import random

import numpy as np
import pytest
from fastapi.testclient import TestClient

from codebreaker.lens import objects as O
from codebreaker.lens.objects_eval import background, iou, paste
from codebreaker.lens.objects_track import Tracker


def test_model_grid_uses_multiples_of_28_at_the_model_area():
    g, sx, sy = O.model_grid(np.zeros((540, 960, 3), np.uint8))
    assert g.shape[0] % 28 == 0 and g.shape[1] % 28 == 0 and abs(g.shape[0] * g.shape[1] / O.AREA - 1) < 0.06


def test_parse_reads_json_in_fences_and_lists():
    assert O._parse('```json\n[{"label": "zebra", "bbox_2d": [0, 1, 2, 3]}]\n```')["label"] == "zebra"
    assert O._parse("no json here") is None


def test_iou():
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == pytest.approx(1.0)
    assert iou([0, 0, 10, 10], [20, 20, 5, 5]) == 0.0


def test_tracker_follows_a_moving_picture_and_reports_its_loss():
    rnd = random.Random(1)
    obj = np.random.default_rng(2).integers(0, 255, (60, 60, 3)).astype(np.uint8)
    bg = background(400, 300, rnd)
    first, box = paste(bg, obj, 50, 100, 80)
    t = Tracker(first, box)
    for f in range(1, 15):
        frame, truth = paste(bg, obj, 50 + 8 * f, 100 + 2 * f, 80)
        r = t.update(frame)
    assert iou(r["box"], truth) > 0.7 and not r["lost"]
    assert Tracker(first, box).update(bg)["lost"]


@pytest.mark.skipif(not (O.DIR / "mobilenetv2-12.onnx").exists(), reason="classifier not downloaded")
def test_classifier_returns_ranked_imagenet_classes():
    c = O.classify(np.full((224, 224, 3), 128, np.uint8))
    assert len(c) == 5 and c[0]["p"] >= c[-1]["p"]


def test_track_route_needs_a_session():
    from codebreaker.web.app import app

    r = TestClient(app).post("/api/lens/track", json={"image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGNgAAAAAgABSK+kcQAAAABJRU5ErkJggg==", "session": "none-such"})
    assert r.status_code == 404
