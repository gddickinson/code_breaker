from fastapi.testclient import TestClient

from codebreaker.web.app import app

client = TestClient(app)


def test_every_cipher_page_loads():
    for c in client.get("/api/ciphers").json()["ciphers"]:
        assert client.get(f"/api/ciphers/{c['id']}").status_code == 200, c["id"]


def test_encrypt_endpoint_and_bad_key():
    r = client.post("/api/ciphers/vigenere/run", json={"op": "encrypt", "text": "ATTACKATDAWN", "key": {"key": "LEMON"}})
    assert r.json()["output"] == "LXFOPVEFRNHR"
    assert client.post("/api/ciphers/affine/run", json={"op": "decrypt", "text": "ABC", "key": {"a": "2", "b": "1"}}).status_code == 400


def test_analyze_and_translate():
    assert client.post("/api/analyze", json={"text": "HELLO" * 10}).status_code == 200
    assert client.post("/api/translate", json={"text": "bonjour le monde"}).status_code == 200


def test_challenge_flow():
    c = client.get("/api/challenge/easy").json()
    r = client.post("/api/challenge/check", json={"token": c["token"], "reveal": True}).json()
    assert client.post("/api/challenge/check", json={"token": c["token"], "answer": r["plain"]}).json()["solved"]


def test_cases():
    for c in client.get("/api/mysteries").json()["cases"]:
        assert client.get(f"/api/mysteries/{c['id']}").status_code == 200, c["id"]


def test_autobreak_reports_clearly():
    from codebreaker import classifier

    r = client.post("/api/autobreak", json={"text": "WKH TXLFN EURZQ IRA MXPSV RYHU WKH ODCB GRJ DQG UXQV DZDB IURP WKH IDUPHU" * 3})
    assert r.status_code == 200
    if classifier.PATH.exists():
        assert r.json()["best"] is not None


def test_history_links_all_resolve():
    import json
    import re
    from pathlib import Path

    from codebreaker.ciphers import REGISTRY
    from codebreaker.mysteries.casefiles import CASES

    static = Path(__file__).resolve().parent.parent / "codebreaker/web/static"
    events = json.loads((static / "history.json").read_text())
    ids = {e["id"] for e in events}
    assert len(ids) == len(events)
    machines = set(re.findall(r"machine\\/(\w+)\$/", "".join(p.read_text() for p in static.glob("*.js"))))
    for e in events:
        for _, href in e["links"]:
            kind = href.removeprefix("#/").split("/")
            if kind[0] == "cipher":
                assert kind[1] in REGISTRY, href
            elif kind[0] == "mystery":
                assert kind[1] in CASES, href
            elif kind[0] == "history":
                assert kind[1] in ids, href
            elif kind[0] == "machine":
                assert kind[1] in machines, href
            else:
                assert kind[0] in ("", "machines", "workbench"), href


def test_latin_translation_when_model_is_available():
    from codebreaker.translate import latin_to_english

    out = latin_to_english("Gallia est omnis divisa in partes tres.")
    if out is not None:
        assert "part" in out.lower()
