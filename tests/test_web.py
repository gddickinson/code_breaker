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
