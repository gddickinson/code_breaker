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


class GlossIn(BaseModel):
    text: str
    lang: str


@router.post("/api/writing/gloss")
def gloss(body: GlossIn):
    from ..writing.glosses import LANGS, gloss as _gloss

    if body.lang not in LANGS or not body.text.strip() or len(body.text) > 1000:
        raise HTTPException(400, "Choose Egyptian, Mycenaean Greek or Old Norse and up to 1,000 characters.")
    return _gloss(body.text, body.lang)


class ScanIn(BaseModel):
    image: str  # data URL
    scripts: list[str] = []


@router.post("/api/writing/scan")
def scan(body: ScanIn):
    from ..writing.glyph_scan import scan_data_url

    if len(body.image) > 15_000_000:
        raise HTTPException(400, "The picture is too large (over about 10 MB).")
    try:
        return scan_data_url(body.image, body.scripts or None)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc
