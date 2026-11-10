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


class LogicIn(BaseModel):
    example: str = ""
    message: str = "Code Breaker"
    glitches: int = 3
    csv: str = ""
    rate: float | None = None


@router.post("/api/signals/logic")
def logic(body: LogicIn):
    from ..signals import logic_service as L

    def run():
        if body.csv:
            ch, rate = L.parse_csv(body.csv, body.rate)
            return L.analyse(ch, rate)
        ch, rate, truth = L.example(body.example or "uart", body.message[:64], max(0, min(body.glitches, 20)))
        return L.analyse(ch, rate, truth)
    return guarded(run)


class LineIn(BaseModel):
    example: str = ""
    message: str = "Hello, wire"
    errors: int = 0
    bits: str = ""


@router.post("/api/signals/linecode")
def linecode(body: LineIn):
    from ..signals import linecode_service as L

    def run():
        if body.bits:
            return L.analyse(body.bits)
        bits, truth = L.example(body.example or "8b10b", body.message[:120], max(0, min(body.errors, 20)))
        return L.analyse(bits, truth)
    return guarded(run)


class VideoIn(BaseModel):
    kind: str = "640x480 @ 60 Hz"
    factor: float = 1.0
    noise: float = 0.02


@router.post("/api/signals/video")
def video(body: VideoIn):
    from ..signals import video as V, video_service as S

    if body.kind != "composite" and body.kind not in V.MODES:
        raise HTTPException(400, "Unknown video mode.")
    return guarded(lambda: S.example(body.kind, min(max(body.factor, 0.5), 2.0), min(max(body.noise, 0.0), 0.2)) | {"reliability": S.reliability(), "modes": list(V.MODES)})


class AudioCodeIn(BaseModel):
    example: str = ""
    message: str = "CQ DE CODE BREAKER"
    noise: float = 0.05
    data: str = ""


@router.post("/api/signals/audio")
def audio_codes(body: AudioCodeIn):
    from ..signals import audio_service as S

    if body.data:
        return guarded(S.analyse_upload, body.data)
    if body.example not in ("dtmf", "morse", "aprs"):
        raise HTTPException(400, "Choose dtmf, morse or aprs.")
    return guarded(S.analyse_example, body.example, body.message[:80], min(max(body.noise, 0.0), 0.8))
