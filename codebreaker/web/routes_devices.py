"""Routes for Live Devices and the Signal Workbench."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class TextIn(BaseModel):
    text: str


def guarded(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except HTTPException:
        raise
    except Exception as exc:  # bad input is reported to the page
        raise HTTPException(400, f"{type(exc).__name__}: {exc}") from exc


router = APIRouter()


@router.get("/api/devices")
def devices(refresh: bool = False):
    from ..devices.discover import discover

    return discover(refresh)


class SerialIn(BaseModel):
    port: str
    baud: int = 9600
    seconds: float = 120


def _lines(gen):
    import json

    def out():
        try:
            for ev in gen:
                yield json.dumps(ev, default=str) + "\n"
        except Exception as exc:  # the stream reports the problem and ends
            yield json.dumps({"event": "error", "message": f"{type(exc).__name__}: {exc}"}) + "\n"
    return StreamingResponse(out(), media_type="application/x-ndjson")


@router.post("/api/devices/serial")
def serial_monitor(body: SerialIn):
    from ..devices.discover import serial_ports
    from ..devices.streams import serial_stream

    from ..devices.sim import SIMS

    known = {p["id"] for p in serial_ports()} | set(SIMS)
    if body.port not in known:
        raise HTTPException(400, "That port is not attached.")
    return _lines(serial_stream(body.port, body.baud, body.seconds))


@router.get("/api/devices/network")
def network_monitor(seconds: float = 60):
    from ..devices.streams import network_stream

    return _lines(network_stream(seconds))


@router.post("/api/devices/analyse")
def analyse_bytes(body: TextIn):
    """Analyse pasted hex or text the same way as a live stream."""
    import re as _re

    from ..devices.analysis import analyse
    t = body.text.strip()
    h = _re.sub(r"[\s:,-]|0x", "", t)
    data = bytes.fromhex(h) if h and _re.fullmatch(r"(?:[0-9a-fA-F]{2})+", h) else t.encode()
    return analyse(data)


class RawIn(BaseModel):
    data: str
    format: str | None = None
    width: int | None = None
    offset: int = 0
    bayer: str | None = None


@router.post("/api/signals/raw")
def raw_frame(body: RawIn):
    from ..signals import service

    if body.format and body.width:
        return guarded(service.render, body.data, body.format, body.width, body.offset, body.bayer)
    return guarded(service.analyse, body.data)


@router.get("/api/signals/example/{kind}")
def raw_example(kind: str):
    from ..signals import service

    if kind not in service.EXAMPLES:
        raise HTTPException(404, "No such example.")
    return service.make_example(kind)
