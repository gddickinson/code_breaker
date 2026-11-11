"""Routes for the Lens page: pictures, camera frames, text and files read and searched for hidden messages."""
import base64
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
MAX = 20_000_000


class ImageIn(BaseModel):
    image: str
    live: bool = False
    signs: str = "auto"
    script: str | None = None
    session: str | None = None
    ai: bool = False


class TextIn(BaseModel):
    text: str


class FileIn(BaseModel):
    name: str
    data: str  # base64 or data URL


DEBUG = Path(__file__).resolve().parents[2] / "data/lens_debug"


def _keep(data: bytes, kind: str) -> None:
    """The last still picture and the last live frame, overwritten each time, for checking what the lens saw.
    Local only and not committed (data/lens_debug is in .gitignore). Skipped under the test suite, whose sample
    pictures used to overwrite the user's own captures."""
    import os

    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    try:
        DEBUG.mkdir(parents=True, exist_ok=True)
        ext = "json" if kind.endswith("_result") else "png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "jpg"
        for old in DEBUG.glob(f"last_{kind}.*"):
            old.unlink()
        (DEBUG / f"last_{kind}.{ext}").write_bytes(data)
    except OSError:
        pass


@router.post("/api/lens/image")
def image(body: ImageIn):
    from ..lens.service import analyse_image

    if len(body.image) > MAX or body.signs not in ("auto", "always", "never"):
        raise HTTPException(400, "Send a picture under about 15 MB.")
    data = base64.b64decode(body.image.split(",", 1)[-1])
    _keep(data, "live" if body.live else "still")
    try:
        if body.live and not body.script:
            from ..lens.service import live
            res = live(data, body.session)
        else:
            res = analyse_image(data, body.live, body.signs, body.script or None, body.session, body.ai)
        _keep(json.dumps({k: res.get(k) for k in ("script", "language", "text", "mean_conf", "translation")}, ensure_ascii=False).encode(), f"{'live' if body.live else 'still'}_result")
        return res
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/ai/status")
def ai_status():
    from ..ai_local import status

    return status()


@router.post("/api/lens/text")
def text(body: TextIn):
    from ..lens.service import analyse_text

    if not body.text.strip() or len(body.text) > 200_000:
        raise HTTPException(400, "Paste up to 200,000 characters.")
    return analyse_text(body.text)


@router.post("/api/lens/file")
def file(body: FileIn):
    from ..lens.service import analyse_file

    if len(body.data) > MAX:
        raise HTTPException(400, "Files up to about 15 MB.")
    try:
        return analyse_file(body.name, base64.b64decode(body.data.split(",", 1)[-1]))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/lens/scripts")
def scripts():
    from ..lens.ocr import TESS

    return sorted(p.stem for p in (TESS / "script").glob("*.traineddata"))


@router.get("/api/lens/sample")
def sample():
    """A demo picture made on the spot: a French sentence, a QR code and a line of runes."""
    import io

    import cv2
    import numpy as np
    import segno
    from PIL import Image, ImageDraw, ImageFont

    from ..writing.glyph_render import FONTS

    im = Image.new("L", (960, 420), 236)
    d = ImageDraw.Draw(im)
    d.text((30, 40), "Rendez-vous demain à midi près du pont.", font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 38), fill=20)
    d.text((30, 250), "ᚠᚢᚦᚨᚱᚲ", font=ImageFont.truetype(str(FONTS["runic"]), 90), fill=25)
    buf = io.BytesIO()
    segno.make_qr("CODE BREAKER").save(buf, kind="png", scale=6)
    qr = Image.open(io.BytesIO(buf.getvalue())).convert("L")
    im.paste(qr, (740, 150))
    arr = np.asarray(im)
    ok, enc = cv2.imencode(".png", arr)
    import base64
    return {"image": "data:image/png;base64," + base64.b64encode(enc.tobytes()).decode()}


@router.get("/api/translate/languages")
def translate_languages():
    from ..langid import NAMES, SRC
    from ..translate import available

    have = set(available()) | {"la"}
    codes = sorted({p.stem for p in SRC.glob("*.txt")} | have | {"en"})
    return [{"code": c, "name": NAMES.get(c, c), "translator": c in have or c == "en"} for c in sorted(codes, key=lambda c: NAMES.get(c, c))]
