"""Lens (Round 78b): everything readable or hidden in a picture, camera frame or file, as one list of findings.

A finding has a kind (text, code, sign, lsb, trailing, embedded, metadata, zero_width, whitespace, homoglyph, acrostic),
a label, optional detail, an optional box in image pixels (for the overlay) and a confidence where one exists.
Live camera frames get the quick checks only (text in the detected or Latin script, and codes); photos and uploads
get everything, including translation and the hidden-message tests."""
import base64
import re

import cv2
import numpy as np

from ..translate import available as translators, translate
from . import ocr, stego, textscan

TEXT_EXT = (".txt", ".md", ".csv", ".html", ".htm", ".json", ".xml", ".rtf", ".log")


def _decode(data_url: str) -> bytes:
    return base64.b64decode(data_url.split(",", 1)[-1])


def codes(gray: np.ndarray) -> list[dict]:
    try:
        import zxingcpp
    except ImportError:
        return []
    out = []
    for r in zxingcpp.read_barcodes(gray):
        p = r.position
        xs = [p.top_left.x, p.top_right.x, p.bottom_left.x, p.bottom_right.x]
        ys = [p.top_left.y, p.top_right.y, p.bottom_left.y, p.bottom_right.y]
        out.append({"kind": "code", "label": f"{r.format.name}: {r.text}", "detail": r.text,
                    "box": [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)], "confidence": 1.0})
    return out


def translation(text: str, lang: dict | None) -> dict | None:
    if not text.strip() or not lang or not lang.get("code") or lang["code"] == "en":
        return None
    if lang["code"] != "la" and lang["code"] not in translators():
        return {"note": f"No translator for {lang['name']} is installed yet (more languages: Round 85)."}
    r = translate(text, lang["code"])
    return {"text": r.get("translation"), "note": r.get("note", "")}


def text_findings(o: dict) -> list[dict]:
    out = []
    for w in o["words"]:
        if ocr.readable(w):
            out.append({"kind": "text", "label": w["text"], "box": w["box"], "confidence": round(w["conf"] / 100, 2)})
    return out


def live(data: bytes, session: str | None) -> dict:
    """A live frame through its session (live_session): lines compiled across frames, with tips for the user."""
    from . import live_session

    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("The picture could not be read.")
    r = live_session.live_frame(session, img)
    findings = [{"kind": "text", "label": l["text"], "box": l["box"], "quad": l["quad"], "confidence": l["agreement"], "status": l["status"]} for l in r["lines"]]
    findings += codes(img)
    text = "\n".join(l["text"] for l in sorted(r["lines"], key=lambda l: (l["box"][1], l["box"][0])))
    lang = ocr.language(text, "Latin") if text else None
    return {"size": [int(img.shape[1]), int(img.shape[0])], "session": r["session"], "findings": findings, "text": text, "script": "Latin",
            "language": lang, "tips": r["tips"], "pending": r["pending"], "log": [f"frame {r['frame']}: {len(r['lines'])} line(s) tracked"]}


def analyse_image(data: bytes, live: bool = False, signs: str = "auto", script: str | None = None, session: str | None = None) -> dict:
    """signs: 'auto' (confident signs outside the text and codes), 'always' (every sign found) or 'never'."""
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("The picture could not be read.")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    extra = []
    if session and not live:  # the live session's agreed lines become candidates for the photo
        from . import live_session

        extra = live_session.consensus_for_photo(session, gray)
    o = ocr.read(gray, script, fast=live, extra=extra)
    if session and not live:  # and the photo's lines join the session's vote
        live_session.share_photo(session, gray, o["words"])
    found_codes = codes(gray)
    inside = lambda w, b: b[0] <= w["box"][0] + w["box"][2] / 2 <= b[0] + b[2] and b[1] <= w["box"][1] + w["box"][3] / 2 <= b[1] + b[3]
    o["words"] = [w for w in o["words"] if not any(inside(w, c["box"]) for c in found_codes)]  # a code's pattern is not text
    o["text"] = "\n".join(" ".join(w["text"] for w in line) for line in ocr.group_lines([w for w in o["words"] if ocr.readable(w)]))
    o["language"] = ocr.language(ocr.clean_for_language([w for w in o["words"] if ocr.readable(w)]), o["script"])
    findings = text_findings(o) + found_codes
    res = {"size": [int(gray.shape[1]), int(gray.shape[0])], "script": o["script"], "language": o["language"], "text": o["text"],
           "mean_conf": o["mean_conf"], "findings": findings, "log": [f"script {o['script']} (tried {', '.join(o['scripts_tried'])})",
                                                                         f"{len(o['words'])} words, mean confidence {o['mean_conf']}"]}
    if live:
        return res
    if signs in ("always", "auto"):
        try:
            from ..writing.glyph_scan import scan
            rest = gray.copy()  # signs are looked for where no text or code was read
            bg = int(np.median(gray))
            for f in findings:
                x, y, w, h = f["box"]
                rest[max(0, y - 4):y + h + 4, max(0, x - 4):x + w + 4] = bg
            g = scan(rest)
            votes = {}
            for sg in g["signs"]:
                if sg["confident"]:
                    votes[sg["candidates"][0]["script"]] = votes.get(sg["candidates"][0]["script"], 0) + 1
            top = max(votes.items(), key=lambda kv: kv[1], default=(None, 0))
            if top[1] >= 2:  # signs agree on a script: read again within it
                g = scan(rest, [top[0]])
                res["log"].append(f"signs agree on {top[0]}: rescanned within that script")
            if signs == "auto":
                g["signs"] = [s for s in g["signs"] if s["confident"]]
            for s in g["signs"]:
                c = s["candidates"][0]
                findings.append({"kind": "sign", "label": f"{c['sign']} {c['script']} {('/'.join(c['values']) or c['code'] or '')}".strip(),
                                 "box": s["box"], "confidence": c["p"], "detail": [x["sign"] for x in s["candidates"]], "confident": s["confident"]})
            res["signs_text"] = "".join(s["candidates"][0]["sign"] for s in g["signs"])
            res["log"].append(f"glyph scan: {len(g['signs'])} sign(s), {sum(s['confident'] for s in g['signs'])} confident")
        except RuntimeError as exc:
            res["log"].append(str(exc))
    res["translation"] = translation(o["text"], o["language"])
    st = stego.analyse(data)
    res["stego"] = {k: st[k] for k in ("lossless", "caveat", "metadata", "trailing", "embedded")}
    res["bit_planes"] = {k: v["bit_plane"] for k, v in st["channels"].items()}
    res["stego_channels"] = {k: {a: b for a, b in v.items() if a != "bit_plane"} for k, v in st["channels"].items()}
    findings += st["findings"] + textscan.scan(o["text"])
    res["log"].append(f"hidden-message checks: {len(st['findings'])} in the file, {len(findings) - len(st['findings'])} other findings")
    return res


def analyse_text(text: str) -> dict:
    lang = ocr.language(text, "Latin") if text.strip() else None
    findings = textscan.scan(text)
    return {"text": text[:20000], "language": lang, "translation": translation(text[:5000], lang), "findings": findings,
            "log": [f"{len(text)} characters", f"{len(findings)} hidden-message finding(s)"]}


def analyse_file(name: str, data: bytes) -> dict:
    head = data[:16]
    if head[:8] == b"\x89PNG\r\n\x1a\n" or head[:2] == b"\xff\xd8" or head[:2] == b"BM" or head[:4] in (b"GIF8", b"RIFF", b"II*\x00", b"MM\x00*"):
        return {"type": "image", **analyse_image(data)}
    if head[:4] == b"%PDF":
        import tempfile
        from ..files.document_extract import extract_pdf

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(data)
            f.flush()
            text = extract_pdf(f.name)
        return {"type": "pdf", **analyse_text(text)}
    if name.lower().endswith(TEXT_EXT) or sum(32 <= b < 127 or b in (9, 10, 13) for b in data[:2000]) > 0.9 * min(len(data), 2000):
        return {"type": "text", **analyse_text(data.decode("utf-8", "replace"))}
    from ..files.carve import embedded, strings

    return {"type": "binary", "findings": [{"kind": "embedded", "label": f"{e['kind']} signature at byte {e['offset']}"} for e in embedded(data)[:30]],
            "strings": strings(data)[:60], "log": [f"{len(data)} bytes, not an image or text: strings and embedded files listed"]}
