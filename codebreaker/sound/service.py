"""What the Sound Lab page calls."""
import base64
import json

from ..languages import ROOT
from . import audio, identify, song, synth

SOUNDS = ROOT / "data/sources/sounds"
MAX_BYTES = 40 * 1024 * 1024


def examples() -> list[dict]:
    out = [{"id": "synthetic", "title": "Synthetic song with a known syllable grammar", "source": "generated", "license": ""}]
    src = SOUNDS / "sources.json"
    if src.exists():
        for r in json.loads(src.read_text()):
            if (SOUNDS / r["file"]).exists():
                out.append({"id": r["file"], "title": f"{r['species']} ({r['title'][5:60]})", "source": r["page"], "license": r["license"]})
    return out


def _run(x, sr, truth: str = "", source: dict | None = None) -> dict:
    r = song.analyse(x, sr)
    r["birds"] = identify.birds(x, sr)
    r["sounds"] = identify.sounds(x, sr)
    if truth:
        r["truth"] = truth
        r["agreement"] = round(song.agreement(truth, r["sequence"]), 3) if len(truth) == len(r["sequence"]) else None
    r["source"] = source or {}
    return r


def analyse_upload(b64: str) -> dict:
    data = base64.b64decode(b64.split(",", 1)[-1])
    if not data:
        raise ValueError("No audio was received.")
    if len(data) > MAX_BYTES:
        raise ValueError("That file is too large here (40 MB limit).")
    x, sr = audio.decode(data, 60)
    return _run(x, sr)


def analyse_example(eid: str) -> dict:
    if eid == "synthetic":
        x, sr, truth = synth.song(40, 3)
        return _run(x, sr, truth, {"title": "Generated"})
    ex = next((e for e in examples() if e["id"] == eid), None)
    if ex is None:
        raise ValueError("No such example.")
    x, sr = audio.load(str(SOUNDS / eid), 60)
    return _run(x, sr, source={"title": ex["title"], "url": ex["source"], "license": ex["license"]})
