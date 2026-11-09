"""File Inspector: identification, previews, carving and the API."""
import base64
import io
import os
import zipfile

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from codebreaker.files import carve, service as S
from codebreaker.web.app import app

client = TestClient(app)


def b64(x: bytes) -> str:
    return base64.b64encode(x).decode()


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 10, 10)).save(buf, "PNG")
    return buf.getvalue()


def test_image_is_identified_by_magic_and_previewed():
    r = S.inspect_upload("photo.dat", b64(png()))
    assert r["kind"] == "png" and r["view"]["view"] == "image" and r["view"]["facts"]["Size"] == "40 x 30"


def test_extension_mismatch_is_flagged():
    r = S.inspect_upload("report.pdf", b64(png()))
    assert r["kind"] == "png" and r["risk"] != "clean"


def test_zip_is_listed_without_reporting_its_own_headers():
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("a.txt", "hello")
        zf.writestr("b.txt", "world")
    r = S.inspect_upload("a.zip", b64(z.getvalue()))
    assert [row[0] for row in r["view"]["rows"]] == ["a.txt", "b.txt"] and r["embedded"] == []


def test_hidden_file_is_found_at_its_offset():
    data = os.urandom(300) + png() + os.urandom(100)
    assert carve.embedded(data)[0]["offset"] == 300


def test_csv_becomes_a_table_and_text_goes_to_the_workbench():
    r = S.inspect_upload("d.csv", b64(b"a,b,c\n1,2,3\n4,5,6\n7,8,9\n"))
    assert r["view"]["view"] == "table" and r["view"]["header"] == ["a", "b", "c"]
    t = S.inspect_upload("msg.txt", b64(b"WKH TXLFN EURZQ IRA MXPSV RYHU WKH ODCB GRJ"))
    assert any(n["action"] == "workbench" for n in t["next"])


def test_numpy_and_random_bytes():
    buf = io.BytesIO()
    np.save(buf, np.arange(12, dtype=np.int16).reshape(3, 4))
    r = S.inspect_upload("a.npy", b64(buf.getvalue()))
    assert r["view"]["rows"][0][1] == "(3, 4)"
    rnd = S.inspect_upload("x.bin", b64(os.urandom(20000)))
    assert rnd["entropy"] > 7.9


def test_pickle_is_never_loaded():
    import pickle

    r = S.inspect_upload("x.pkl", b64(pickle.dumps({"a": 1})))
    assert r["view"]["view"] == "none" and "Pickle" in r["view"]["facts"].get("Warning", "Pickle")


def test_api_and_format_search():
    assert client.post("/api/files/inspect", json={"name": "e.bin", "data": ""}).status_code == 400
    assert client.post("/api/files/inspect", json={"name": "p.png", "data": b64(png())}).json()["kind"] == "png"
    assert any(".parquet" in x["extensions"] for x in client.get("/api/files/formats?q=parquet").json())
