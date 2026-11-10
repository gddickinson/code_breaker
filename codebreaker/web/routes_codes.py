"""Routes for the Barcodes & QR page: make, read, QR anatomy and the damage test."""
import base64

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class MakeIn(BaseModel):
    kind: str = "QR Code"
    text: str
    ec: str = "M"


class ImageIn(BaseModel):
    image: str  # a data URL from the page


@router.get("/api/codes/kinds")
def kinds():
    from ..signals.symbology import KINDS, EC_MAP

    return [{"kind": k, "example": v[1], "family": v[2], "use": v[3], "ec": k in EC_MAP} for k, v in KINDS.items()]


@router.post("/api/codes/make")
def make(body: MakeIn):
    from ..signals.symbology import KINDS, create

    if body.kind not in KINDS or body.ec not in "LMQH" or not body.text or len(body.text) > 2000:
        raise HTTPException(400, "Choose a listed code, an error level of L, M, Q or H, and up to 2,000 characters.")
    try:
        return create(body.kind, body.text, body.ec)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/codes/read")
def read(body: ImageIn):
    from ..signals import barcodes
    from ..signals.symbology import read_codes

    try:
        raw = base64.b64decode(body.image.split(",", 1)[-1])
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_GRAYSCALE)
    except Exception as exc:
        raise HTTPException(400, "That is not an image.") from exc
    if img is None:
        raise HTTPException(400, "That is not an image.")
    if max(img.shape) > 2400:
        f = 2400 / max(img.shape)
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    own = barcodes.scan_ean(img)
    return {"codes": read_codes(img), "own_ean": own, "size": [int(img.shape[1]), int(img.shape[0])]}


@router.get("/api/codes/damage")
def damage(text: str = "https://example.org/code-breaker", seed: int = 1):
    from ..signals.symbology import damage_test

    if not text or len(text) > 200:
        raise HTTPException(400, "Use 1 to 200 characters.")
    return damage_test(text, seed=seed)
