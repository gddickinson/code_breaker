"""Round 78b: the Lens page's reading, translation and hidden-message checks."""
import base64
import json

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from codebreaker.lens import ocr, stego, textscan
from codebreaker.lens.stego_controls import RESULT as STEGO, embed
from codebreaker.web.app import app

needs_ocr = pytest.mark.skipif(not ocr.available(), reason="Tesseract data missing (data/models/tessdata_fast)")
client = TestClient(app)


def _png(a):
    return cv2.imencode(".png", a)[1].tobytes()


def _sample():
    return client.get("/api/lens/sample").json()["image"]


@needs_ocr
def test_reads_and_translates_the_sample():
    r = client.post("/api/lens/image", json={"image": _sample()}).json()
    assert r["script"] == "Latin" and r["language"]["code"] == "fr" and "midi" in r["text"]
    assert "bridge" in (r["translation"]["text"] or "").lower()
    kinds = [f["kind"] for f in r["findings"]]
    assert "code" in kinds and all(f.get("box") for f in r["findings"] if f["kind"] in ("text", "code"))


@needs_ocr
def test_other_scripts():
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("L", (900, 90), 255)
    ImageDraw.Draw(im).text((10, 20), "Καλημέρα κόσμε, αυτό είναι δοκιμή.", font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 40), fill=0)
    r = ocr.read(np.asarray(im))
    assert r["script"] == "Greek" and "κόσμε" in r["text"]


def test_lsb_detected_and_controls_recorded():
    res = json.loads(STEGO.read_text())
    assert res["rates"]["0.25"]["detected"] >= 0.9 and res["chi_clean_false_alarms"] <= 0.05 and res["false_alarms_on_former_jpegs"] > 0.5
    rnd = np.random.default_rng(1)
    gx = np.tile(np.linspace(30, 220, 320), (240, 1)) + rnd.normal(0, 6, (240, 320))
    clean = np.clip(gx, 0, 255).astype(np.uint8)
    hidden = embed(clean, 0.5, rnd)
    assert stego.spa(hidden) > res["spa_alarm"] > stego.spa(clean)
    assert any(f["kind"] == "lsb" for f in stego.analyse(_png(hidden))["findings"])
    assert stego.trailing(_png(clean) + b"secret note")["preview"] == "secret note"
    jpg = cv2.imencode(".jpg", clean)[1].tobytes()
    assert not stego.analyse(jpg)["lossless"] and not any(f["kind"] == "lsb" for f in stego.analyse(jpg)["findings"])


def test_text_checks():
    assert textscan.zero_width("Meet​‌​​‌​​‌ me")["as_text"] == "I"
    assert textscan.homoglyphs("Pay the bаnk")[0]["foreign"] == "а"
    lines = ["Silent rivers run", "Every morning comes", "Cold winds blow", "Rain falls softly", "Each night we wait", "Then dawn returns"]
    assert any(f["kind"] == "acrostic" and "SECRET" in f["label"] for f in textscan.scan("\n".join(lines)))
    assert textscan.scan("The cat sat on the mat.\nIt was a sunny day.\nBirds sang.\nWe walked home.\nNothing happened.") == []


def test_text_and_file_routes():
    r = client.post("/api/lens/text", json={"text": "Rendez-vous demain à midi près du pont."}).json()
    assert r["language"]["code"] == "fr"
    data = base64.b64encode("plain words​‌ here".encode()).decode()
    r = client.post("/api/lens/file", json={"name": "note.txt", "data": data}).json()
    assert r["type"] == "text" and any(f["kind"] == "zero_width" for f in r["findings"])


@needs_ocr
def test_small_print_on_a_glossy_label():
    """Round 78b fix: small print under uneven light (as on a photographed tin) must be read; one pass in the
    page-layout mode on the raw picture read 22% of a real label's words, the multi-pass reading about half."""
    from PIL import Image, ImageDraw, ImageFont
    lines = ["NATURAL FLAVORS INCLUDING OIL OF PEPPERMINT", "QUESTIONS COMMENTS CALL TODAY", "Serving size one mint per container",
             "Total sugars one gram added sugars", "Made of sugar gum arabic gelatin"]
    im = Image.new("L", (1280, 420), 200)
    d = ImageDraw.Draw(im)
    for i, t in enumerate(lines):
        d.text((40, 30 + i * 75), t, font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22), fill=40)
    a = np.asarray(im).astype(float) + np.tile(np.linspace(-60, 50, 1280), (420, 1))  # glare across the label
    a = cv2.imdecode(cv2.imencode(".jpg", np.clip(a, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 70])[1], 0)
    r = ocr.read(a)
    want = [w.lower() for t in lines for w in t.split()]
    got = [w["text"].lower().strip(".,") for w in r["words"] if ocr.readable(w)]
    assert r["script"] == "Latin" and sum(w in got for w in want) / len(want) >= 0.8
    assert "peppermint" in r["text"].lower().split("\n")[0]
