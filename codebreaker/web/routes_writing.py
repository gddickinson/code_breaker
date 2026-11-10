"""Routes for the Scripts & Glyphs page: sign tables, sign-by-sign reading and spelling Latin text in a script."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ReadIn(BaseModel):
    text: str


class WriteIn(BaseModel):
    text: str
    script: str


@router.get("/api/writing/scripts")
def scripts():
    from ..writing.signs import summary
    from ..writing.transliterate import SUBSTITUTE

    return [{"id": k, **v, "can_write": k in SUBSTITUTE} for k, v in summary().items()]


@router.get("/api/writing/signs/{script}")
def signs(script: str):
    from ..writing.signs import SCRIPTS
    from ..writing.transliterate import catalogue

    if script not in SCRIPTS:
        raise HTTPException(404, "Unknown script.")
    return catalogue(script)


@router.post("/api/writing/read")
def read(body: ReadIn):
    from ..writing.transliterate import read as _read

    if not body.text.strip() or len(body.text) > 5000:
        raise HTTPException(400, "Paste or type up to 5,000 characters.")
    return _read(body.text)


@router.post("/api/writing/write")
def write(body: WriteIn):
    from ..writing.transliterate import SUBSTITUTE, write as _write

    if body.script not in SUBSTITUTE or not body.text.strip() or len(body.text) > 500:
        raise HTTPException(400, "Choose a script that can be written and up to 500 characters.")
    return _write(body.text, body.script)
