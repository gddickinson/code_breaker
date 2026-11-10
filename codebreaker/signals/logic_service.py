"""Logic Analyser: which protocol is on these wires, and what does it say? Plus examples, CSV import and the control."""
import csv
import io
import itertools
import json
import random

import numpy as np

from ..languages import ROOT
from . import ir as IR, logic_bus as B, logic_decode as D, logic_synth as S, logic_usb as U

RESULT = ROOT / "data/results/logic_control.json"
MAX_SAMPLES = 20_000_000


# How hard each protocol's own checks are to pass by chance: a CRC-15 almost never; two framing bits per UART byte often.
NEEDED = {"CAN": 1, "I2C": 2, "USB": 2, "NEC infrared": 1, "RC5 infrared": 1}  # units needed before the evidence counts fully
EVIDENCE = {"NEC infrared": 1.3, "RC5 infrared": 1.05, "USB": 1.4, "CAN": 1.4, "I2C": 1.2, "1-Wire": 1.2, "SPI": 1.1, "UART": 1.0}


def looks_like_clock(x: np.ndarray) -> bool:
    """A clock's high and low runs are nearly all one length; data lines are not."""
    runs = np.diff(D.edges(D.debounce(x)))
    if len(runs) < 16:
        return False
    w = np.median(runs)
    return float(np.mean(np.abs(runs - w) <= max(1, 0.15 * w))) > 0.85


def _score(r: dict, ch: dict) -> float:
    """Share of decoded units that pass the protocol's checks, weighted by how strong those checks are."""
    n = len(r.get("bytes", []))
    p = r["protocol"]
    if p in ("NEC infrared", "RC5 infrared"):
        n = len(r.get("frames", []))
        ok = sum(f["ok"] for f in r.get("frames", []))
    elif p == "USB":
        n = len(r.get("packets", []))
        ok = sum(1 for x in r.get("packets", []) if x.get("ok") and "error" not in x)
    elif p == "CAN":
        n = len(r.get("frames", []))
        ok = sum(f["crc_ok"] for f in r.get("frames", []))
    elif p == "1-Wire":
        ok = n if r.get("resets") and r.get("presence") else 0
    elif p == "SPI":
        cs = D.debounce(ch[r["wiring"]["CS"]])
        ok = n if len(D.edges(cs)) <= 4 and looks_like_clock(ch[r["wiring"]["SCK"]]) else 0
    elif p == "I2C":
        scl, sda = D.debounce(ch[r["wiring"]["SCL"]]), D.debounce(ch[r["wiring"]["SDA"]])
        high_changes = int(np.sum((np.diff(sda.astype(np.int8)) != 0) & (scl[1:] == 1) & (scl[:-1] == 1)))
        # Real I2C changes data while the clock is high only for START and STOP: two per message.
        distinct = len({b["value"] for b in r.get("bytes", [])})
        # A line held low reads as zero bytes that all look acknowledged; real traffic varies.
        ok = n - r.get("errors", 0) if r.get("messages") and high_changes <= 2 * len(r["messages"]) + 2 and (distinct > 1 or n < 3) else 0
    else:
        ok = 0 if looks_like_clock(ch[r["wiring"]["RX"]]) else n - r.get("errors", 0)
    return 0.0 if n == 0 else (ok / n) * min(1.0, n / NEEDED.get(p, 4)) * EVIDENCE.get(p, 1.0)


def identify(ch: dict, rate: float) -> list[dict]:
    """Every decoder on every plausible wiring, best first."""
    names = [k for k, v in ch.items() if len(D.edges(v)) >= 4]
    trials = []
    for a in names:
        trials += [(D.uart(ch[a], rate), {"RX": a}), (B.can(ch[a], rate), {"CAN": a}), (B.onewire(ch[a], rate), {"DQ": a}), (IR.decode_nec(ch[a], rate), {"IR": a}), (IR.decode_rc5(ch[a], rate), {"IR": a})]
    for a, b in itertools.permutations(names, 2):
        trials.append((D.i2c(ch[a], ch[b], rate), {"SCL": a, "SDA": b}))
        trials.append((U.decode(ch[a], ch[b], rate), {"D+": a, "D-": b}))
    # A chip-select line may change only twice, so it is chosen from every channel that changes at all.
    selects = [k for k, v in ch.items() if len(D.edges(D.debounce(v))) >= 2]
    if len(selects) >= 3 and names:
        cs = min(selects, key=lambda k: len(D.edges(D.debounce(ch[k]))))
        sck = max(names, key=lambda k: len(D.edges(ch[k])))
        for m in [k for k in names if k not in (cs, sck)]:
            trials.append((D.spi(ch[cs], ch[sck], ch[m], rate), {"CS": cs, "SCK": sck, "MOSI": m}))
    out = []
    for r, wiring in trials:
        r["wiring"] = wiring
        r["score"] = round(_score(r, ch), 3)
        if r["score"] > 0:
            out.append(r)
    return sorted(out, key=lambda r: -r["score"])


def text_of(r: dict) -> str:
    return "".join(chr(b["value"]) if 32 <= b["value"] < 127 else "." for b in r.get("bytes", []))


def example(kind: str, message: str = "Code Breaker", glitches: int = 3, seed: int = 1) -> tuple[dict, float, dict]:
    data, rnd = message.encode()[:64], np.random.default_rng(seed)
    if kind == "uart":
        return S.uart(data, 115200, "E").sample(115200 * 16, rnd, 0.02 / 115200, glitches), 115200 * 16, {"protocol": "UART", "settings": "115200 baud, 8E1"}
    if kind == "spi":
        return S.spi(data, 1e6, 3).sample(8e6, rnd, 0, glitches), 8e6, {"protocol": "SPI", "settings": "mode 3, 1 MHz"}
    if kind == "i2c":
        return S.i2c(0x50, data, 100e3).sample(2e6, rnd, 0, glitches), 2e6, {"protocol": "I2C", "settings": "address 0x50, 100 kHz"}
    if kind == "can":
        frames = [(0x100 + i, data[i:i + 8]) for i in range(0, len(data), 8)]
        return S.can(frames, 250000).sample(4e6, rnd, 0, glitches), 4e6, {"protocol": "CAN", "settings": "250 kbit/s"}
    if kind == "nec":
        return IR.nec(0x04, data[0] if data else 0x08, 2).sample(200e3, rnd, 0, glitches), 200e3, {"protocol": "NEC infrared", "settings": "address 0x04"}
    if kind == "rc5":
        return IR.rc5(0x05, (data[0] if data else 12) & 0x3F, 1).sample(200e3, rnd, 0, glitches), 200e3, {"protocol": "RC5 infrared", "settings": "address 5"}
    if kind == "usb":
        packets = [(0x9, 3, 1), (0xB, 0, 0, data[:64]), (0x2,)]
        return U.transaction(packets, "full").sample(48e6, rnd, 0, glitches), 48e6, {"protocol": "USB", "settings": "full speed, address 3, endpoint 1"}
    return S.onewire(data).sample(1e6, rnd, 0, 0), 1e6, {"protocol": "1-Wire", "settings": "standard speed"}


def parse_csv(text: str, rate: float | None = None) -> tuple[dict, float]:
    """Logic-analyser CSV (sigrok, Saleae and similar): a time column then one 0/1 column per channel.

    Exports that list only changes are expanded onto an even sample grid."""
    rows = list(csv.reader(io.StringIO(text.strip())))
    head = [h.strip() for h in rows[0]]
    body = [[float(v) for v in r] for r in rows[1:] if r and all(v.strip() for v in r)]
    arr = np.array(body)
    t, vals = arr[:, 0], arr[:, 1:]
    if rate is None:
        steps = np.diff(t)
        steps = steps[steps > 0]
        rate = float(1 / np.min(steps)) if len(steps) else 1.0
    idx = np.round((t - t[0]) * rate).astype(int)
    n = int(idx[-1]) + 1
    if n > MAX_SAMPLES:
        raise ValueError("That capture is too long to expand here.")
    ch = {}
    for j, name in enumerate(head[1:]):
        x = np.zeros(n, np.uint8)
        for k in range(len(idx)):
            x[idx[k]:idx[k + 1] if k + 1 < len(idx) else n] = vals[k, j] > 0.5
        ch[name or f"D{j}"] = x
    return ch, rate


def waveform(ch: dict, rate: float, points: int = 3000) -> dict:
    """Each channel as (time, level) steps for drawing, thinned to keep the page light."""
    out = {}
    for k, x in ch.items():
        e = D.edges(x)
        if len(e) > points:
            e = e[:: int(np.ceil(len(e) / points))]
        steps = [[0.0, int(x[0])]] + [[round(i / rate, 9), int(x[i])] for i in e]
        out[k] = steps
    return {"channels": out, "duration": len(next(iter(ch.values()))) / rate}


def control(trials: int = 80, seed: int = 9) -> dict:
    rnd, rows = random.Random(seed), []
    kinds = ["uart", "spi", "i2c", "can", "onewire", "usb", "nec", "rc5"]
    for t in range(trials):
        kind = kinds[t % len(kinds)]
        msg = "".join(rnd.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ") for _ in range(rnd.randint(6, 20)))
        ch, rate, truth = example(kind, msg, rnd.randint(0, 4), t)
        ranked = identify(ch, rate)
        best = ranked[0] if ranked else {"protocol": "", "bytes": []}
        want = {"NEC infrared": msg[:1], "RC5 infrared": chr(ord(msg[0]) & 0x3F)}.get(truth["protocol"], msg)
        got = text_of(best) if truth["protocol"] not in ("NEC infrared", "RC5 infrared") else "".join(chr(f["command"]) for f in best.get("frames", [])[:1])
        rows.append({"kind": truth["protocol"], "got": best["protocol"], "protocol_ok": best["protocol"] == truth["protocol"], "bytes_ok": got == want})
    return {"trials": trials, "protocol_ok": sum(r["protocol_ok"] for r in rows), "bytes_ok": sum(r["bytes_ok"] for r in rows), "rows": rows}


def reliability() -> dict:
    if not RESULT.exists():
        RESULT.write_text(json.dumps(control(), indent=1))
    d = json.loads(RESULT.read_text())
    return {"trials": d["trials"], "protocol_ok": d["protocol_ok"], "bytes_ok": d["bytes_ok"]}


def analyse(ch: dict, rate: float, truth: dict | None = None) -> dict:
    ranked = identify(ch, rate)
    keep = ("protocol", "score", "wiring", "baud", "bitrate", "mode", "inverted", "parity", "errors", "messages", "frames", "resets", "presence", "speed", "packets")
    rows = [{k: r[k] for k in keep if k in r} | {"text": text_of(r), "hex": " ".join(f"{b['value']:02X}" for b in r.get("bytes", [])[:256]), "marks": [[round(b["t"], 9), b["value"], b["ok"]] for b in r.get("bytes", [])[:400]]} for r in ranked[:6]]
    return {"rate": rate, "channels": list(ch), "ranking": rows, "wave": waveform(ch, rate), "truth": truth or {}, "reliability": reliability()}
