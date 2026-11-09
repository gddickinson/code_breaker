"""What the File Inspector page calls: identify, scan, describe and open one uploaded file."""
import base64
import os
import tempfile
from pathlib import Path

from . import carve
from .file_inspector import inspect_file
from .format_db import db
from .readers import open_any
from .security_scanner import scan_file

MAX_BYTES = 32 * 1024 * 1024
CIPHER_HINT = 0.3


def _next_steps(info, raw: bytes, ent: float) -> list[dict]:
    steps = []
    if info.is_text:
        letters = sum(c.isalpha() for c in raw[:4000].decode("utf-8", errors="ignore"))
        steps.append({"label": "Try to crack it in the Workbench", "action": "workbench"} if letters > 20 else {})
    if not info.is_text and ent <= 7.9 and info.detected_kind in ("unknown", "data", "binary", ""):
        steps.append({"label": "Rebuild it as a raw camera or sensor frame", "action": "signals"})
    if ent > 7.9:
        steps.append({"label": "Near-random bytes: compressed or encrypted. Look for embedded signatures and headers below.", "action": ""})
    return [s for s in steps if s]


def inspect_upload(name: str, b64: str) -> dict:
    raw = base64.b64decode(b64.split(",", 1)[-1])
    if not raw:
        raise ValueError("The file is empty.")
    if len(raw) > MAX_BYTES:
        raise ValueError("That file is too large here (32 MB limit).")
    suffix = Path(name).suffix[:16]
    fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="cb_inspect_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        info = inspect_file(tmp)
        scan = scan_file(tmp)
        entry = db().lookup_by_extension(suffix) or db().lookup_by_filename(name) or db().lookup_by_id(info.detected_kind)
        view = open_any(tmp, info.detected_kind, info.is_text, info.encoding, raw)
        ent = carve.entropy(raw)
        return {
            "name": name, "size": len(raw), "size_human": info.size_human, "extension": info.extension,
            "kind": info.detected_kind, "via": info.detected_via, "description": info.description,
            "is_text": info.is_text, "encoding": info.encoding, "hex": info.hex_preview,
            "entropy": round(ent, 3), "entropy_map": carve.entropy_map(raw), "strings": carve.strings(raw),
            "embedded": carve.embedded(raw, info.detected_kind), "risk": scan.risk_level,
            "findings": [{"severity": x.severity, "category": x.category, "description": x.description, "detail": x.detail} for x in scan.findings],
            "format": entry.to_markdown() if entry else "", "view": view, "next": _next_steps(info, raw, ent),
            "text_for_workbench": raw[:20000].decode(info.encoding or "utf-8", errors="replace") if info.is_text else "",
        }
    finally:
        os.unlink(tmp)


def search_formats(q: str) -> list[dict]:
    return [{"id": e.id, "name": e.name, "extensions": e.extensions, "category": e.category} for e in db().search(q, 30)]
