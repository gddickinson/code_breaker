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


class SketchIn(BaseModel):
    image: str
    scripts: list[str] = []


@router.post("/api/writing/sketch")
def sketch(body: SketchIn):
    from ..writing.glyph_model import load
    from ..writing.glyph_scan import decode_image
    from ..writing.sketch import identify_sketch

    if load() is None:
        raise HTTPException(400, "The glyph recogniser is not trained yet: run python -m codebreaker.writing.glyph_model.")
    return identify_sketch(decode_image(body.image), body.scripts or None)


class SignsIn(BaseModel):
    signs: str


@router.post("/api/writing/script_of")
def script_of(body: SignsIn):
    """Which script a typed or scanned set of signs belongs to: Unicode tells for known signs (no recogniser needed)."""
    from collections import Counter

    from ..writing.signs import SCRIPTS, script_of as which

    c = Counter(which(ch) for ch in body.signs if not ch.isspace())
    return {"counts": {(SCRIPTS[k][0] if k else "not a supported script"): v for k, v in c.most_common()}}
