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
