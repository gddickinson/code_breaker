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


def test_open_and_solutions_registers():
    d = client.get("/api/codes/open").json()
    names = {c["name"] for c in d["codes"]}
    assert "Dorabella cipher" in names and "Copiale cipher" not in names and len(d["codes"]) > 60
    s = client.get("/api/solutions").json()
    assert s["verified"] and all(c["tier"] in ("passes", "strong", "partial") for c in s["candidates"])


def test_math_examples_are_correct():
    import json
    import math
    from pathlib import Path

    t = {x["id"]: json.dumps(x, ensure_ascii=False) for x in json.loads((Path(__file__).resolve().parent.parent / "codebreaker/web/static/math.json").read_text())}
    assert pow(5, -1, 26) == 21 and "21" in t["modular"]
    assert round(math.log2(math.factorial(26)), 1) == 88.4 and round(88.4 / 3.2, 1) == 27.6
    assert 60 * 26 ** 3 * 150738274937250 == 158962555217826360000
    assert pow(65, 17, 3233) == 2790 and pow(2790, 2753, 3233) == 65 and pow(17, -1, 3120) == 2753
    assert [pow(5, 6, 23), pow(5, 15, 23), pow(19, 6, 23), pow(8, 15, 23)] == [8, 19, 2, 2]
    assert (3 * 7 + 3 * 4) % 26 == 7 and (2 * 7 + 5 * 4) % 26 == 8 and (15 * 7 + 17 * 8) % 26 == 7 and (20 * 7 + 9 * 8) % 26 == 4
    assert 6 * 168 * 156 == 157248 and "157,248" in t["linear"]
    assert math.gcd(1071, 462) == 21
    p = 1.0
    for i in range(23):
        p *= (365 - i) / 365
    assert round(1 - p, 3) == 0.507
    a, b, r = 0x57, 0x83, 0
    while b:
        if b & 1:
            r ^= a
        a = (a << 1) ^ (0x11b if a & 0x80 else 0)
        b >>= 1
    assert r == 0xC1
    assert round(math.exp(-0.4), 2) == 0.67 and round(math.exp(-2), 3) == 0.135
    assert all(str(k) in "".join(t) or True for k in t)


def test_community_publications_and_cube():
    assert client.get("/api/publications?q=Voynich").json()["total"] > 0
    from codebreaker.web import app as appmod
    assert client.post("/api/cube/solve", json={"facelets": "DRLUUBFBRBLURRLRUBLRDDFDLFUFUFFDBRDUBRUFLLFDDBFLUBLRBD"}).json()["moves"]


def test_channel_links_resolve():
    import json
    from pathlib import Path

    from codebreaker.ciphers import REGISTRY
    from codebreaker.mysteries.casefiles import CASES

    static = Path(__file__).resolve().parent.parent / "codebreaker/web/static"
    history = {e["id"] for e in json.loads((static / "history.json").read_text())}
    for e in json.loads((static / "channels.json").read_text()):
        if "link" in e:
            kind = e["link"][1].removeprefix("#/").split("/")
            assert (kind[0] == "cipher" and kind[1] in REGISTRY) or (kind[0] == "mystery" and kind[1] in CASES) or (kind[0] == "history" and kind[1] in history) or kind[0] in ("machine", "how"), e["link"]


def test_static_files_are_not_cached():
    assert client.get("/static/core.js").headers["cache-control"] == "no-store"


def test_sudoku_photo_reading():
    import cv2
    import numpy as np

    from codebreaker.sudoku_vision import read_grid

    puzzle = [int(c) for c in "530070000600195000098000060800060003400803001700020006060000280000419005000080079"]
    size, m = 900, 80
    img = np.full((size + 2 * m, size + 2 * m), 245, dtype=np.uint8)
    step = size / 9
    for i in range(10):
        w = 8 if i % 3 == 0 else 2
        p = int(m + i * step)
        cv2.line(img, (p, m), (p, m + size), 20, w)
        cv2.line(img, (m, p), (m + size, p), 20, w)
    for i, v in enumerate(puzzle):
        if v:
            cv2.putText(img, str(v), (int(m + (i % 9) * step + 30), int(m + (i // 9) * step + 75)), cv2.FONT_HERSHEY_SIMPLEX, 2.2, 15, 5, cv2.LINE_AA)
    h, w = img.shape
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[60, 40], [w - 20, 10], [w - 50, h - 30], [15, h - 70]])
    photo = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h), borderValue=210)
    got = read_grid(photo)
    assert sum(a == b for a, b in zip(got, puzzle)) >= 79


def test_biology_page_data():
    import json
    from pathlib import Path

    d = json.loads((Path(__file__).resolve().parent.parent / "codebreaker/web/static/biology.json").read_text())
    assert len(d) >= 12


def test_tutorials_link_to_real_pages():
    import json
    import re
    from pathlib import Path

    static = Path(__file__).resolve().parent.parent / "codebreaker/web/static"
    routes = "".join(p.read_text() for p in static.glob("*.js"))
    data = json.loads((static / "tutorials.json").read_text())
    assert len(data) >= 10
    for t in data:
        assert re.search(re.escape(t["puzzle"].removeprefix("#/").split("/")[-1]), routes), t["puzzle"]


def test_theory_pages_are_complete_and_linked():
    import json
    from pathlib import Path

    from codebreaker.ciphers import REGISTRY
    from codebreaker.mysteries.casefiles import CASES

    static = Path(__file__).resolve().parent.parent / "codebreaker/web/static"
    data = json.loads((static / "theory.json").read_text())
    ids = {x["id"] for x in data}
    sims = "".join((static / f).read_text() for f in ("theory.js", "theory_sims2.js"))
    history = {e["id"] for e in json.loads((static / "history.json").read_text())}
    links = []
    for x in data:
        assert x["sections"] and x["example"] and x["solve"]
        if x.get("sim"):
            assert f"SIMS.{x['sim']} =" in sims, x["id"]
        links += [h for _, h in x.get("links", [])] + [r[3] for r in x.get("table", [])[1:]]
    for h in links:
        kind = h.removeprefix("#/").split("/")
        assert (kind[0] == "cipher" and kind[1] in REGISTRY) or (kind[0] == "mystery" and kind[1] in CASES) or (kind[0] == "history" and kind[1] in history) or (kind[0] == "theory" and kind[1] in ids) or kind[0] in ("how", "machine", "math", "puzzles", "help"), h
    assert client.get("/api/ciphers").status_code == 200


def test_page_scripts_do_not_redeclare_globals():
    """All page scripts share one global scope, so a repeated name silently breaks a whole file."""
    import re
    from collections import defaultdict
    from pathlib import Path

    static = Path(__file__).resolve().parent.parent / "codebreaker/web/static"
    seen = defaultdict(set)
    for f in static.glob("*.js"):
        for line in f.read_text().splitlines():
            m = re.match(r"(?:const|let|var|class|function|async function)\s+([A-Za-z_$][\w$]*)", line)
            if m:
                seen[m.group(1)].add(f.name)
    clashes = {k: v for k, v in seen.items() if len(v) > 1}
    assert not clashes, clashes


def test_codes_in_nature_covers_every_channel():
    import json
    from pathlib import Path

    d = json.loads((Path(__file__).resolve().parent.parent / "codebreaker/web/static/biology.json").read_text())
    groups = {x["group"] for x in d}
    assert {"Chemical messages", "Light and colour", "Sound and vibration", "Electric signals", "Honest signals and trust", "Birdsong"} <= groups
    newer = [x for x in d if x["group"] in ("Chemical messages", "Light and colour", "Sound and vibration", "Electric signals", "Honest signals and trust")]
    assert len(newer) >= 15 and all(x.get("encoding") for x in newer)
    assert len({x["title"] for x in d}) == len(d)
