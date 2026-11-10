"""Aircraft page: encode a small air-traffic scene into ADS-B signals, decode it back, and measure the decoder."""
import json
import math
import random

import numpy as np

from ..languages import ROOT
from . import modes as M

RESULT = ROOT / "data/results/adsb_control.json"
HOME = (51.47, -0.45)


def _hex(bits: str) -> str:
    return f"{int(bits, 2):0{len(bits) // 4}X}"


def _frame(icao: int, me: str) -> str:
    assert len(me) == 56, len(me)
    return M.with_parity(_hex("10001" + "101" + f"{icao:024b}" + me))


def ident(icao: int, callsign: str) -> str:
    chars = "".join(f"{M.CHARS.index(c) if c in M.CHARS and c != '#' else 32:06b}" for c in callsign.upper().ljust(8)[:8])
    return _frame(icao, "00100" + "000" + chars)


def position(icao: int, lat: float, lon: float, alt_ft: int, odd: bool) -> str:
    """Compact position reporting: 17-bit fractions of a latitude and a longitude zone."""
    i = int(odd)
    dlat = 360 / (4 * M.NZ - i)
    yz = math.floor(131072 * (lat % dlat) / dlat + 0.5)
    rlat = dlat * (yz / 131072 + math.floor(lat / dlat))
    dlon = 360 / max(M._nl(rlat) - i, 1)
    xz = math.floor(131072 * (lon % dlon) / dlon + 0.5)
    n = round((alt_ft + 1000) / 25)
    a = f"{n:011b}"
    alt = a[:7] + "1" + a[7:]
    return _frame(icao, "01011" + "00" + "0" + alt + "0" + str(i) + f"{yz % 131072:017b}" + f"{xz % 131072:017b}")


def velocity(icao: int, speed_kt: float, heading: float, vrate: int) -> str:
    ve, vn = speed_kt * math.sin(math.radians(heading)), speed_kt * math.cos(math.radians(heading))
    ew, ns = round(abs(ve)) + 1, round(abs(vn)) + 1
    vr = abs(vrate) // 64 + 1
    # Type code 19, subtype 1, intent change, IFR, a 3-bit navigation accuracy, then the velocity fields: 56 bits.
    return _frame(icao, "10011" + "001" + "0" + "0" + "000" + str(int(ve < 0)) + f"{ew:010b}" + str(int(vn < 0)) + f"{ns:010b}" + "0" + str(int(vrate < 0)) + f"{vr:09b}" + "00" + "0" + "0000000")


def scene(n: int, rnd: random.Random) -> list[dict]:
    out = []
    for k in range(n):
        out.append({"icao": f"{rnd.randrange(0x400000, 0x4FFFFF):06X}", "callsign": rnd.choice(["BAW", "KLM", "DLH", "EZY", "RYR", "AFR"]) + str(rnd.randrange(10, 9999)), "lat": round(HOME[0] + rnd.uniform(-1.5, 1.5), 4), "lon": round(HOME[1] + rnd.uniform(-2.5, 2.5), 4), "alt": rnd.randrange(30, 400) * 100, "speed": rnd.randrange(150, 480), "heading": rnd.randrange(0, 360), "vrate": rnd.choice([0, 0, -1, 1]) * rnd.randrange(1, 30) * 64})
    return out


def messages(planes: list[dict]) -> list[str]:
    out = []
    for p in planes:
        icao = int(p["icao"], 16)
        out += [ident(icao, p["callsign"]), position(icao, p["lat"], p["lon"], p["alt"], False), position(icao, p["lat"], p["lon"], p["alt"], True), velocity(icao, p["speed"], p["heading"], p["vrate"])]
    return out


def track(frames: list[dict]) -> list[dict]:
    """Combine messages by aircraft address; a position needs one even and one odd report."""
    planes = {}
    for f in frames:
        if not f.get("crc_ok") or "icao" not in f:
            continue
        p = planes.setdefault(f["icao"], {"icao": f["icao"], "messages": 0})
        p["messages"] += 1
        if f.get("callsign"):
            p["callsign"] = f["callsign"]
        if "cpr" in f:
            p["odd" if f["cpr_odd"] else "even"] = f["cpr"]
            p["alt"] = f["altitude_ft"]
            p["newest_odd"] = f["cpr_odd"]
        if "speed_kt" in f:
            p |= {"speed": f["speed_kt"], "heading": f["heading_deg"], "vrate": f["vertical_rate_fpm"]}
    for p in planes.values():
        if "even" in p and "odd" in p:
            pos = M.cpr_global(p.pop("even"), p.pop("odd"), p.pop("newest_odd"))
            if pos:
                p["lat"], p["lon"] = pos
    return sorted(planes.values(), key=lambda p: p.get("callsign", ""))


def run(n: int, noise: float, seed: int) -> dict:
    rnd = random.Random(seed)
    truth = scene(n, rnd)
    msgs = messages(truth)
    rnd.shuffle(msgs)
    signal = M.ppm(msgs, np.random.default_rng(seed), noise)
    frames = M.demodulate(signal)
    got = {p["icao"]: p for p in track(frames)}
    right = 0
    for t in truth:
        g = got.get(t["icao"], {})
        right += g.get("callsign") == t["callsign"] and g.get("alt") == t["alt"] and abs(g.get("lat", 99) - t["lat"]) < 0.001 and abs(g.get("lon", 99) - t["lon"]) < 0.001 and abs(g.get("speed", -9) - t["speed"]) < 2
    return {"truth": truth, "planes": list(got.values()), "messages": len(msgs), "decoded": len(frames), "aircraft_right": right, "samples": len(signal)}


def control() -> dict:
    rows = [{"noise": nz, **{k: v for k, v in run(6, nz, 50 + i).items() if k in ("messages", "decoded", "aircraft_right")}} for i, nz in enumerate([0.05, 0.1, 0.15, 0.2, 0.25, 0.3] * 2)]
    rng, false = np.random.default_rng(1), 0
    for _ in range(6):
        false += len(M.demodulate(np.abs(rng.normal(0, 0.3, 200000)).astype(np.float32)))
    return {"rows": rows, "aircraft": 6 * len(rows), "aircraft_right": sum(r["aircraft_right"] for r in rows), "null_frames": false}


def reliability() -> dict:
    if not RESULT.exists():
        RESULT.write_text(json.dumps(control(), indent=1))
    return json.loads(RESULT.read_text())
