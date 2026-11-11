"""Workbench crack and submissions."""
import base64
import json
import random

from fastapi.testclient import TestClient

from codebreaker import crack, crack_steps as S, leads as L, submissions as U
from codebreaker.ciphers import REGISTRY
from codebreaker.ciphers.base import DEMO_PLAIN
from codebreaker.text import letters, similarity
from codebreaker.web.app import app

client = TestClient(app)


def test_guess_only_sets_the_order():
    order = crack.plan([{"id": "jefferson", "probability": 0.9}], [{"family": "Periodic polyalphabetic (Vigenere family)"}])
    assert order[0] == "jefferson" and "caesar" in order
    assert len(order) == sum(bool(c.attack) for c in REGISTRY.values())


def test_verdict_needs_margin_length_and_a_null():
    best = {"cipher": "X", "coverage": 0.9}
    assert crack.verdict(best, [0.1, 0.2], 100, 50)["level"] == "readable"
    assert crack.verdict(best, [0.8], 100, 50)["level"] == "partial"
    assert crack.verdict(best, [0.1], 20, 50)["level"] == "partial"
    assert crack.verdict(best, [], 100, 50)["level"] == "partial"
    assert crack.verdict({"cipher": "X", "coverage": 0.2}, [0.1], 100, 50)["level"] == "none"
    assert crack.verdict({"cipher": "X", "coverage": 0.66}, [0.66], 300, 50)["level"] == "none"  # no better than shuffled


def test_ties_are_credited_to_the_simplest_system():
    assert crack._quality({"coverage": 0.8, "score": -4, "rank": 0}) > crack._quality({"coverage": 0.8, "score": -4, "rank": 24})


def test_encodings_decode():
    names = {f["name"]: f["text"] for f in S.encodings("SGVsbG8gdGhlcmUgZnJpZW5k")}
    assert names["Base64"] == "Hello there friend"
    assert S.encodings("48 65 6c 6c 6f 20 79 6f 75")[0]["text"] == "Hello you"


def test_reported_base64_message_is_decoded_not_overfitted():
    ev = events("RGVjaXBoZXJpbmcgaXMgZnVuIQ==", lang=None)
    end = ev[-1]
    assert end["verdict"]["label"] == "Decoded" and end["best"]["spaced"] == "Deciphering is fun!"
    assert not any(e.get("id") == "attack" for e in ev)


def test_encoded_cipher_is_decoded_then_attacked():
    inner = REGISTRY["caesar"].encrypt(DEMO_PLAIN, shift=9)
    ev = events(base64.b64encode(inner.encode()).decode())
    assert any(e.get("id") == "layer" for e in ev)
    assert ev[-1]["verdict"]["level"] == "readable"
    assert similarity(letters(DEMO_PLAIN), letters(ev[-1]["best"]["plaintext"])) > 0.95


def test_natural_separates_language_from_noise():
    assert S.natural("Deciphering is fun!")["lang"] == "en"
    assert S.natural("Wkh txlfn eurzq ira") is None


def test_big_keyspaces_are_not_trusted_on_short_text():
    assert not crack.trusted({"cid": "substitution"}, 15)
    assert crack.trusted({"cid": "substitution"}, 60)
    assert crack.trusted({"cid": "caesar"}, 15)
    assert crack.verdict({"cipher": "X", "coverage": 0.9, "trusted": False}, [0.1], 100, 50)["level"] == "none"


def test_trusted_reading_outranks_a_lucky_short_one():
    assert crack._quality({"coverage": 0.1, "score": -6, "trusted": True}) > crack._quality({"coverage": 0.9, "score": -3, "trusted": False})


def test_short_gibberish_is_not_cracked():
    assert events("XQZJV KPWMF BNTHC", budget=10)[-1]["verdict"]["level"] != "readable"


def test_vigenere_trace_finds_the_key():
    t = REGISTRY["vigenere"].encrypt(DEMO_PLAIN, key="LANTERN")
    assert S.vigenere_columns(t, "en")["key"] == "LANTERN"


def test_caesar_sweep_finds_the_shift():
    assert S.caesar_sweep(REGISTRY["caesar"].encrypt(DEMO_PLAIN, shift=11), "en")["best"] == 11


def events(text, budget=14, lang="en"):
    r = client.post("/api/crack", json={"text": text, "budget": budget, "lang": lang})
    assert r.status_code == 200
    return [json.loads(l) for l in r.text.splitlines() if l.strip()]


def test_crack_streams_steps_and_solves():
    ev = events(REGISTRY["caesar"].encrypt(DEMO_PLAIN, shift=7))
    assert {"inspect", "identify", "attack"} <= {e.get("id") for e in ev}
    assert any(e["event"] == "trace" for e in ev)
    end = ev[-1]
    assert end["event"] == "finish" and end["verdict"]["level"] == "readable"
    assert similarity(letters(DEMO_PLAIN), letters(end["best"]["plaintext"])) > 0.95


def test_random_letters_are_not_called_cracked():
    rnd = random.Random(2)
    end = events("".join(rnd.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(160)))[-1]
    assert end["verdict"]["level"] != "readable"


def test_empty_text_is_rejected():
    assert client.post("/api/crack", json={"text": "  "}).status_code == 400


def test_submission_is_saved_queued_and_deduplicated(tmp_path, monkeypatch):
    import shutil

    db = tmp_path / "leads.db"
    shutil.copy(L.DB if hasattr(L, "DB") else "data/leads.db", db)
    monkeypatch.setattr(L, "DB", db, raising=False)
    monkeypatch.setattr(U, "FOLDER", U.ROOT / "data/sources/submitted")
    text = "QWERT YUIOP ASDFG HJKLZ XCVBN MQWER TYUIO PLKJH"
    U.record_verdict(text, "none")
    try:
        r = U.submit("Pytest code", text, "unit test", "note")
        assert r["status"] == "added" and r["avenues"] > 0
        assert (U.ROOT / f"data/sources/submitted/{r['slug']}.txt").read_text().strip() == text
        assert U.submit("Another name", text.lower().replace(" ", ""))["status"] == "duplicate"
        assert any(x["slug"] == r["slug"] for x in U.listing())
    finally:
        for f in (U.ROOT / "data/sources/submitted").glob("sub-pytest-code*.txt"):
            f.unlink()


def test_submission_requires_a_finished_unreadable_crack():
    text = "ZXCVB NMASD FGHJK LQWER TYUIO PZXCV BNMAS DFGHJ"
    U._VERDICTS.pop(U._norm(text), None)
    assert client.post("/api/submissions", json={"name": "Test", "text": text}).status_code == 400
    U.record_verdict(text, "readable")
    assert client.post("/api/submissions", json={"name": "Test", "text": text}).json()["status"] == "solved"


def test_a_solved_crack_records_its_verdict():
    text = REGISTRY["caesar"].encrypt(DEMO_PLAIN, shift=5)
    events(text)
    assert U._VERDICTS[U._norm(text)] == "readable"


def test_submission_needs_name_and_text():
    assert client.post("/api/submissions", json={"name": "", "text": "ABCDEFG"}).status_code == 400
    assert client.post("/api/submissions", json={"name": "x", "text": ""}).status_code == 400


def test_peel_removes_encodings_in_layers():
    inner = REGISTRY["caesar"].encrypt(DEMO_PLAIN[:120], shift=4)
    wrapped = base64.b64encode(base64.b64encode(inner.encode())).decode()
    got, layers = U.peel(wrapped)
    assert got == inner and layers == ["Base64", "Base64"]
    assert U.peel("ORDINARY CIPHER TEXT HERE") == ("ORDINARY CIPHER TEXT HERE", [])


def test_hunter_cracks_a_submitted_vigenere(tmp_path, monkeypatch):
    import shutil

    from codebreaker.mysteries import hunter as H

    db = tmp_path / "leads.db"
    shutil.copy(L.DB, db)
    monkeypatch.setattr(L, "DB", db)
    inner = REGISTRY["vigenere"].encrypt(DEMO_PLAIN, key="MIRADOR")
    text = base64.b64encode(inner.encode()).decode()
    U.record_verdict(text, "none")
    try:
        r = U.submit("Pytest vigenere", text, "unit test")
        assert r["layers"] == ["Base64"]
        conn = L.connect()
        path = list(conn.execute("SELECT data_path FROM codes WHERE slug=?", (r["slug"],)))[0][0]
        assert path.endswith(".inner.txt")
        assert list(conn.execute("SELECT count(*) FROM avenues WHERE code=? AND strategy='crack'", (r["slug"],)))[0][0] == 1
        out = H.work({"id": 0, "code": r["slug"], "path": path, "strategy": "crack", "param": "25", "lang": "en", "level": 0, "seed": 1, "tests": 1, "control": None, "ck": "x"})
        assert out["verdict"].startswith(H.WORKBENCH)
        got = letters(out["reading"])
        assert len(got) > 100 and letters(DEMO_PLAIN).startswith(got)
    finally:
        for f in (U.ROOT / "data/sources/submitted").glob("sub-pytest-vigenere*"):
            f.unlink()
