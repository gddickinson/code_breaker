"""Round 77: word glosses from Wiktionary, with the quotation control."""
import json

from fastapi.testclient import TestClient

from codebreaker.web.app import app
from codebreaker.writing import glosses as G


def test_sources_recorded():
    meta = json.loads((G.SRC / "sources.json").read_text())
    for lang in G.LANGS:
        assert meta[lang]["licence"] == "CC BY-SA 4.0" and meta[lang]["pages"] > 500
        assert (G.SRC / f"{lang}.json").stat().st_size == meta[lang]["bytes"]


def test_known_words():
    first = lambda r: [(w["word"], w["found"], (w["senses"][:1] or [{}])[0].get("sense", "")) for w in r["words"]]
    eg = first(G.gloss("ꜥnḫwḏꜣsnb", "egyptian"))
    assert [w for w, _, _ in eg] == ["ꜥnḫ", "wḏꜣ", "snb"] and "live" in eg[0][2]
    assert first(G.gloss("konungr ok", "old_norse"))[0][2] == "a king"
    assert "king" in first(G.gloss("𐀷𐀙𐀏", "mycenaean"))[0][2]
    assert G.lookup("pḥ.k", "egyptian")[0] == "pḥ"


def test_quotation_control_beats_random():
    c = G.control("egyptian")
    assert c["quotations"] >= 100 and c["found_real"] > c["found_random_max"] + 0.3


def test_api():
    r = TestClient(app).post("/api/writing/gloss", json={"text": "ꜥnḫ wḏꜣ snb", "lang": "egyptian"}).json()
    assert r["found"] == 3 and "not a translation" in r["note"]
