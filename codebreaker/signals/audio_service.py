"""Audio Signals page: which code is in this sound (DTMF, Morse or APRS), what it says, and how reliable that is."""
import base64
import json
import random

import numpy as np

from ..languages import ROOT
from ..sound.audio import decode as decode_audio, resample
from . import audio_codes as A, ax25 as X

RESULT = ROOT / "data/results/audio_codes_control.json"


def identify(x: np.ndarray, sr: int) -> list[dict]:
    x = x / (np.max(np.abs(x)) + 1e-9)
    rows = []
    d = A.dtmf_decode(resample(x, sr, A.SR), A.SR)
    rows.append({"code": "DTMF touch tones", "text": d["text"], "score": 1.2 if d["symbols"] >= 1 else 0.0, "detail": {"keys": d["symbols"]}})
    m = A.morse_decode(resample(x, sr, A.SR), A.SR)
    good = m["symbols"] >= 2 and m.get("unknown", 0) <= 0.2 * m["symbols"]
    rows.append({"code": "Morse code", "text": m["text"], "score": round(1.0 - m.get("unknown", 0) / max(m["symbols"], 1), 3) if good else 0.0, "detail": {"wpm": m.get("wpm"), "unknown": m.get("unknown", 0)}})
    frames = X.deframe(X.demodulate(resample(x, sr, X.SR), X.SR))
    ok = [f for f in frames if f.get("crc_ok")]
    rows.append({"code": "APRS (AX.25 over AFSK)", "text": " | ".join(f"{f['source']} > {f['destination']}: {f['info']}" for f in ok), "score": 1.4 if ok else 0.0, "detail": {"frames": len(frames), "crc_ok": len(ok), "packets": ok}})
    return sorted(rows, key=lambda r: -r["score"])


def example(kind: str, message: str, noise: float = 0.05, seed: int = 1) -> tuple[np.ndarray, int, dict]:
    rnd = np.random.default_rng(seed)
    if kind == "dtmf":
        keys = "".join(c for c in message.upper() if c in "0123456789*#ABCD") or "0123456789"
        return A.dtmf_tones(keys, rnd, noise=noise), A.SR, {"code": "DTMF touch tones", "text": keys}
    if kind == "morse":
        text = " ".join("".join(c for c in w if c in A.MORSE) for w in message.upper().split()) or "SOS"
        return A.morse_audio(text, 18, rnd, noise=noise), A.SR, {"code": "Morse code", "text": text}
    info = "!4903.50N/07201.75W-" + message[:60]
    return X.afsk(X.frame("N0CALL-9", "APRS", info), rnd, noise), X.SR, {"code": "APRS (AX.25 over AFSK)", "text": f"N0CALL-9 > APRS: {info}"}


def control(seed: int = 3) -> dict:
    rnd, rows = random.Random(seed), []
    for kind in ("dtmf", "morse", "aprs"):
        for t in range(6):
            msg = "".join(rnd.choice("0123456789") for _ in range(6)) if kind == "dtmf" else " ".join("".join(rnd.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(rnd.randint(2, 5))) for _ in range(3))
            x, sr, truth = example(kind, msg, (0.05, 0.2)[t % 2], 100 + t + len(rows))
            best = identify(x, sr)[0]
            rows.append({"kind": truth["code"], "got": best["code"] if best["score"] else "", "ok": best["code"] == truth["code"] and best["text"] == truth["text"]})
    nrnd, false = np.random.default_rng(seed), 0
    for t in range(8):
        n = 8000 * 3
        noise = nrnd.normal(0, 0.3, n)
        if t % 2:
            noise += 0.5 * np.sin(2 * np.pi * nrnd.uniform(300, 3000) * np.arange(n) / 8000)
        false += bool(identify(noise.astype(np.float32), 8000)[0]["score"])
    return {"trials": len(rows), "correct": sum(r["ok"] for r in rows), "null_trials": 8, "null_decoded": false, "rows": rows}


def reliability() -> dict:
    if not RESULT.exists():
        RESULT.write_text(json.dumps(control(), indent=1))
    d = json.loads(RESULT.read_text())
    return {k: d[k] for k in ("trials", "correct", "null_trials", "null_decoded")}


def analyse_example(kind: str, message: str, noise: float) -> dict:
    x, sr, truth = example(kind, message, noise)
    return {"ranking": identify(x, sr), "truth": truth, "audio": _wav_b64(x, sr), "reliability": reliability()}


def analyse_upload(b64: str) -> dict:
    data = base64.b64decode(b64.split(",", 1)[-1])
    if not data:
        raise ValueError("No audio was received.")
    x, sr = decode_audio(data, 60)
    return {"ranking": identify(x, sr), "truth": {}, "reliability": reliability()}


def _wav_b64(x: np.ndarray, sr: int) -> str:
    from ..sound.audio import wav_bytes

    return "data:audio/wav;base64," + base64.b64encode(wav_bytes(np.clip(x / (np.max(np.abs(x)) + 1e-9) * 0.8, -1, 1), sr)).decode()
