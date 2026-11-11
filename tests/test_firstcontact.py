"""Round 84: First Contact lab: the Arecibo bits from the saved source, the layout decoder, language-like profiles."""
import json

import numpy as np
from fastapi.testclient import TestClient

from codebreaker import firstcontact as F
from codebreaker.web.app import app


def test_arecibo_bits_recorded():
    b = F.arecibo_bits()
    assert len(b) == 1679 and set(b) == {"0", "1"}
    assert b[:23] == "00000010101010000000000"  # first row, as printed on the saved page


def test_arecibo_decodes_at_23_and_controls():
    r = F.decode_layout(F.arecibo_bits(), shuffles=50)
    assert r["best_width"] == 23 and r["rows"] == 73 and r["z"] >= F.PICTURE_Z
    rnd = np.random.default_rng(3)
    assert F.decode_layout(F.picture(19, 31, rnd), shuffles=40)["best_width"] == 19
    assert F.decode_layout("".join(map(str, rnd.integers(0, 2, 19 * 31))), shuffles=40)["z"] < F.PICTURE_Z


def test_profiles_separate_random_from_structure():
    rnd = np.random.default_rng(1)
    assert "no sequential" in F.profile(list(rnd.integers(0, 20, 3000)))["verdict"]
    assert F.profile(list("abcabcabdabcabcabd" * 200))["z_H2"] > 5
    r = json.loads(F.RESULT.read_text())
    assert r["references"]["Random letters (26)"]["z_H2"] < 5 and r["references"]["English letters"]["z_H2"] > 50


def test_routes():
    c = TestClient(app)
    assert c.post("/api/contact/layout", json={"text": F.arecibo_bits()}).json()["best_width"] == 23
    assert c.post("/api/contact/profile", json={"text": "the cat sat on the mat " * 30}).json()["z_H2"] > 5
    assert c.post("/api/contact/profile", json={"text": "ab"}).status_code == 400
