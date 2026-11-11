"""Routes for the Sound Lab."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class AudioIn(BaseModel):
    data: str = ""
    example: str = ""


@router.get("/api/sounds/examples")
def sound_examples():
    from ..sound.service import examples

    return examples()


@router.post("/api/sounds/analyse")
def sound_analyse(body: AudioIn):
    from ..sound import service

    try:
        return service.analyse_example(body.example) if body.example else service.analyse_upload(body.data)
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


class HideIn(BaseModel):
    text: str
    carrier: str = "noise"
    level: float = -10.0


@router.post("/api/sounds/hide")
def sound_hide(body: HideIn):
    """Text written into the spectrogram of a carrier sound (Round 82)."""
    import base64

    from ..sound import spectro_stego as G
    from ..sound.audio import wav_bytes
    from ..sound.spectro_eval import carrier

    if not body.text.strip() or len(body.text) > 40 or body.carrier not in ("noise", "song", "sweep", "none") or not -40 <= body.level <= 10:
        raise HTTPException(400, "Up to 40 characters, a listed carrier and a level between -40 and 10 dB.")
    h = G.hide(G.text_image(body.text.strip()), seconds=max(2.0, 0.35 * len(body.text)))
    x = h if body.carrier == "none" else G.mix(carrier(body.carrier, len(h), 7), h, body.level)
    return {"wav": "data:audio/wav;base64," + base64.b64encode(wav_bytes(x, G.SR)).decode(), "spectrogram": G.png(G.spectrogram_image(x))}


@router.post("/api/sounds/reveal")
def sound_reveal(body: AudioIn):
    """Look for pictures hidden in a recording's spectrogram: OCR words and the structure score."""
    import base64

    from ..sound import spectro_stego as G
    from ..sound.audio import decode, resample

    try:
        x, sr = decode(base64.b64decode(body.data.split(",", 1)[-1]))
    except Exception as exc:
        raise HTTPException(400, f"The audio could not be read: {exc}") from exc
    x = resample(x, sr, G.SR) if sr != G.SR else x
    return G.detect(x)
