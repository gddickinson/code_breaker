"""Routes for the First Contact lab: language-likeness profiles and picture layouts from bit streams."""
import json
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TextIn(BaseModel):
    text: str


@router.get("/api/contact/references")
def references():
    from ..firstcontact import RESULT

    return json.loads(RESULT.read_text())


@router.post("/api/contact/profile")
def profile(body: TextIn):
    from ..firstcontact import profile as prof, tokens

    t = tokens(body.text)
    if len(t) < 100 or len(body.text) > 200_000:
        raise HTTPException(400, "Paste at least 100 symbols (characters, or space-separated units), up to 200,000 characters.")
    return prof(t)


@router.post("/api/contact/layout")
def layout(body: TextIn):
    from ..firstcontact import PICTURE_Z, decode_layout

    bits = re.sub(r"[^01]", "", body.text)
    if not 20 <= len(bits) <= 20000:
        raise HTTPException(400, "Send 20 to 20,000 bits (0s and 1s).")
    r = decode_layout(bits, shuffles=100)
    r["picture"] = r["z"] >= PICTURE_Z
    return r


@router.get("/api/contact/arecibo")
def arecibo():
    from ..firstcontact import arecibo_bits

    return {"bits": arecibo_bits(), "source": "https://en.wikipedia.org/wiki/Arecibo_message"}
