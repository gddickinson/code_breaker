"""Routes for the File Inspector."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class UploadIn(BaseModel):
    name: str
    data: str


@router.post("/api/files/inspect")
def inspect(body: UploadIn):
    from ..files.service import inspect_upload

    try:
        return inspect_upload(body.name, body.data)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/files/formats")
def formats(q: str = ""):
    from ..files.service import search_formats

    return search_formats(q)
