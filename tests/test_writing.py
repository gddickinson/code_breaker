"""Scripts & Glyphs: recorded sources, known sign values, reading and writing (Round 75)."""
import json

from fastapi.testclient import TestClient

from codebreaker.web.app import app
from codebreaker.writing import signs as S
from codebreaker.writing import transliterate as W


def test_sources_recorded_and_unchanged():
    meta = json.loads((S.SRC / "sources.json").read_text())
    for name, m in meta.items():
        text = (S.SRC / f"wp_{name}.txt").read_text()
        assert len(text) == m["bytes"] and m["url"].startswith("https://en.wikipedia.org/wiki/")


def test_egyptian_values_from_the_tables():
    eg = S.tables()["egyptian"]
    kinds = [e.get("kind") for e in eg.values()]
    assert len(eg) == 1072 and kinds.count("uniliteral") == 26 and kinds.count("biliteral") > 140 and kinds.count("triliteral") > 70
    code = {e["code"]: e for e in eg.values()}
    assert code["G1"]["values"] == ["ꜣ"] and code["D21"]["values"] == ["r"] and code["N35"]["values"] == ["n"] and code["X1"]["values"] == ["t"]
    assert code["S29"]["values"] == ["s", "ś"] and code["D4"]["values"] == ["jr"] and code["S34"]["values"] == ["ꜥnḫ"]


def test_other_scripts():
    t = S.tables()
    assert W.read("ᚠᚢᚦᚨᚱᚲ")["transliteration"] == "fuþark"
    assert W.read("ᚁᚂᚃᚄᚅ")["transliteration"] == "blfsn"
    assert t["linear_b"]["𐀀"]["values"] == ["a"] and t["old_persian"]["𐎣"]["values"] == ["ka"] and t["gothic"]["𐌰"]["values"] == ["a"]
    assert all(not any(c in v for c in "{}|=<>") for tab in t.values() for e in tab.values() for v in e["values"])


def test_gardiner_codes_and_unknown_signs():
    r = W.read("G1 D21-N35")
    assert r["from_codes"] == "𓄿𓂋𓈖" and r["transliteration"] == "ꜣ.r.n"
    assert W.from_codes("hello") is None


def test_write_round_trip():
    for script in ("egyptian", "runic", "ogham", "gothic"):
        w = W.write("Bastet", script)
        assert "?" not in w["text"]
        assert W.read(w["text"])["simple"].replace(".", "").replace("a", "a") != ""
    assert W.read(W.write("Cleopatra", "runic")["text"])["transliteration"] == "kleopatra"


def test_api():
    c = TestClient(app)
    assert any(s["id"] == "egyptian" for s in c.get("/api/writing/scripts").json())
    assert len(c.get("/api/writing/signs/ogham").json()) == 29
    assert c.post("/api/writing/read", json={"text": "ᚠᚢᚦᚨᚱᚲ"}).json()["simple"] == "futhark"
    assert c.post("/api/writing/write", json={"text": "Ra", "script": "egyptian"}).status_code == 200
    assert c.post("/api/writing/write", json={"text": "Ra", "script": "cuneiform"}).status_code == 400


def test_downloaded_fonts_unchanged():
    import hashlib
    import re

    d = S.ROOT / "codebreaker/web/static/fonts"
    for name, digest in re.findall(r"\| (\S+\.ttf) \| \S+ \| ([0-9a-f]{64}) \|", (d / "README.md").read_text()):
        assert hashlib.sha256((d / name).read_bytes()).hexdigest() == digest
    assert (d / "OFL.txt").exists()
