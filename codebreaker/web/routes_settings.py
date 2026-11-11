"""Settings routes (Round 90d): the optional Claude connection. Changing settings is allowed from this machine only;
no route ever returns the key."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()
LOCAL = {"127.0.0.1", "::1", "localhost"}


class ClaudeIn(BaseModel):
    enabled: bool = False
    acknowledged: bool = False
    key: str | None = None


def _local(request: Request) -> None:
    if (request.client.host if request.client else "") not in LOCAL:
        raise HTTPException(403, "Settings can be changed only from this computer.")


@router.get("/api/settings/claude")
def claude_status():
    from ..ai_claude import status

    return status()


@router.post("/api/settings/claude")
def claude_configure(body: ClaudeIn, request: Request):
    from ..ai_claude import configure

    _local(request)
    try:
        return configure(body.enabled, body.acknowledged, body.key or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/settings/claude/forget")
def claude_forget(request: Request):
    from ..ai_claude import forget_key

    _local(request)
    return forget_key()


@router.post("/api/settings/claude/test")
def claude_test(request: Request):
    from ..ai_claude import test

    _local(request)
    return test()
