"""Open a file of a known kind and return something a web page can show: text, a table, an image, a listing or a report."""
import base64
import csv
import io
import json
import tarfile
import wave
import zipfile

import numpy as np

IMAGE_KINDS = {"png", "jpeg", "jpg", "gif", "bmp", "tiff", "webp", "ico", "heic", "jp2"}
TEXT_LIMIT = 20000
ROWS = 60


def _png(img) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _codes(im) -> list[dict]:
    """QR codes and EAN-13 barcodes in the picture, read by the Signal tools."""
    from ..signals.barcodes import read_codes

    try:
        arr = np.array(im.convert("L"))
        if max(arr.shape) > 2500:
            return []
        return read_codes(arr)
    except Exception:  # a picture that cannot be scanned still opens
        return []


def image(path: str) -> dict:
    from PIL import ExifTags, Image

    with Image.open(path) as im:
        info = {"Format": im.format, "Size": f"{im.width} x {im.height}", "Mode": im.mode, "Frames": getattr(im, "n_frames", 1)}
        exif = {}
        try:
            for k, v in (im.getexif() or {}).items():
                name = ExifTags.TAGS.get(k, str(k))
                if name in ("Make", "Model", "DateTime", "Software", "Orientation", "GPSInfo", "Artist", "Copyright"):
                    exif[name] = "present (location data)" if name == "GPSInfo" else str(v)[:80]
        except Exception:  # broken EXIF should not stop the preview
            pass
        codes = _codes(im)
        if codes:
            info["Codes found"] = "; ".join(f"{c['type']}: {c['text']}" for c in codes)
        thumb = im.convert("RGBA") if im.mode not in ("RGB", "RGBA", "L") else im.copy()
        thumb.thumbnail((900, 900))
        return {"view": "image", "src": _png(thumb), "facts": info | exif}


def text(raw: bytes, encoding: str) -> dict:
    t = raw[: TEXT_LIMIT * 4].decode(encoding or "utf-8", errors="replace")[:TEXT_LIMIT]
    stripped = t.strip()
    if stripped[:1] in "[{":
        try:
            return {"view": "text", "text": json.dumps(json.loads(raw.decode(encoding or "utf-8", errors="replace")), indent=1)[:TEXT_LIMIT], "facts": {"Structure": "valid JSON"}}
        except ValueError:
            pass
    lines = stripped.splitlines()[:ROWS + 1]
    if len(lines) > 3:
        try:
            dialect = csv.Sniffer().sniff("\n".join(lines[:20]), delimiters=",;\t|")
            rows = list(csv.reader(lines, dialect))
            if len({len(r) for r in rows[:20]}) == 1 and len(rows[0]) > 1:
                return {"view": "table", "header": rows[0], "rows": rows[1:ROWS + 1], "facts": {"Delimiter": repr(dialect.delimiter), "Columns": len(rows[0])}, "text": t}
        except csv.Error:
            pass
    return {"view": "text", "text": t, "facts": {"Lines shown": t.count("\n") + 1}}


def archive(path: str, kind: str) -> dict:
    rows = []
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for i in z.infolist()[:500]:
                rows.append([i.filename, i.file_size, i.compress_size, "%04d-%02d-%02d" % i.date_time[:3]])
        return {"view": "table", "header": ["Member", "Size", "Compressed", "Date"], "rows": rows, "facts": {"Members": len(rows)}}
    try:
        with tarfile.open(path) as tf:
            for m in tf.getmembers()[:500]:
                rows.append([m.name, m.size, "", ""])
        return {"view": "table", "header": ["Member", "Size", "", ""], "rows": rows, "facts": {"Members": len(rows)}}
    except tarfile.TarError:
        pass
    import bz2
    import gzip
    import lzma
    opener = {"gzip": gzip.open, "bzip2": bz2.open, "xz": lzma.open}.get(kind)
    if opener:
        with opener(path) as f:
            head = f.read(4096)
        return {"view": "text", "text": head.decode("utf-8", errors="replace"), "facts": {"Note": "first 4 KB after decompression"}, "inner": base64.b64encode(head).decode()}
    return {"view": "none", "facts": {"Note": "listing this archive type needs an extra library"}}


def sqlite(path: str) -> dict:
    import apsw

    db = apsw.Connection(path, flags=apsw.SQLITE_OPEN_READONLY)
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    out = {"view": "tables", "tables": [], "facts": {"Tables": len(tables)}}
    for t in tables[:20]:
        cur = db.execute(f'SELECT * FROM "{t.replace(chr(34), "")}" LIMIT 20')
        cols = [d[0] for d in cur.getdescription()]
        rows = [[str(v)[:60] for v in r] for r in cur]
        count = list(db.execute(f'SELECT count(*) FROM "{t.replace(chr(34), "")}"'))[0][0]
        out["tables"].append({"name": t, "rows_total": count, "header": cols, "rows": rows})
    return out


def numpy_file(path: str) -> dict:
    data = np.load(path, allow_pickle=False)
    arrays = dict(data.items()) if hasattr(data, "items") else {"array": data}
    rows = [[k, str(v.shape), str(v.dtype), f"{float(v.min()):.4g}" if v.size and v.dtype.kind in "iuf" else "", f"{float(v.max()):.4g}" if v.size and v.dtype.kind in "iuf" else ""] for k, v in arrays.items()]
    return {"view": "table", "header": ["Array", "Shape", "Type", "Min", "Max"], "rows": rows, "facts": {"Arrays": len(rows)}}


def matlab(path: str) -> dict:
    from scipy.io import whosmat

    rows = [[n, str(s), c] for n, s, c in whosmat(path)]
    return {"view": "table", "header": ["Variable", "Shape", "Class"], "rows": rows, "facts": {"Variables": len(rows)}}


def pdf(path: str) -> dict:
    from pypdf import PdfReader

    r = PdfReader(path)
    meta = {k.strip("/"): str(v)[:80] for k, v in (r.metadata or {}).items()}
    first = "\n\n".join((p.extract_text() or "") for p in r.pages[:3])
    return {"view": "text", "text": first[:TEXT_LIMIT] or "(no text layer: this may be a scanned image, so OCR is needed)", "facts": {"Pages": len(r.pages), "Encrypted": r.is_encrypted} | meta}


def audio_wav(path: str) -> dict:
    with wave.open(path) as w:
        n, rate, ch, width = w.getnframes(), w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(min(n, rate * 30))
    dtype = {1: np.uint8, 2: np.int16, 4: np.int32}.get(width, np.int16)
    x = np.frombuffer(raw, dtype=dtype).astype(float)
    x = x[::ch] if ch > 1 else x
    env = [round(float(abs(c).max()), 1) for c in np.array_split(x, 300)] if len(x) else []
    return {"view": "wave", "envelope": env, "facts": {"Channels": ch, "Sample rate": rate, "Bits": 8 * width, "Duration (s)": round(n / rate, 2)}}


def blend(path: str) -> dict:
    from .blend_inspector import render_markdown

    return {"view": "text", "text": render_markdown(path), "facts": {}}


def open_any(path: str, kind: str, is_text: bool, encoding: str, raw: bytes) -> dict:
    """The best view for this kind; anything that cannot be opened falls back to the hex view on the page."""
    from .readers_data import READERS

    try:
        if kind in READERS:
            return READERS[kind](path)
        if kind in IMAGE_KINDS:
            return image(path)
        if kind in ("zip", "jar", "whl", "apk", "docx", "xlsx", "pptx", "epub", "odt", "ods", "tar", "gzip", "bzip2", "xz"):
            return archive(path, kind)
        if kind in ("sqlite", "sqlite?"):
            return sqlite(path)
        if kind in ("npy", "npz"):
            return numpy_file(path)
        if kind == "mat":
            return matlab(path)
        if kind == "pdf":
            return pdf(path)
        if kind in ("wav", "wave"):
            return audio_wav(path)
        if kind == "blend":
            return blend(path)
        if kind.startswith("pickle"):
            return {"view": "none", "facts": {"Warning": "Pickle files can run code when loaded, so this one is shown as bytes only."}}
        if is_text:
            return text(raw, encoding)
    except Exception as exc:  # a damaged or unusual file still gets the byte-level views
        return {"view": "none", "facts": {"Could not open": f"{type(exc).__name__}: {exc}"[:200]}}
    return {"view": "none", "facts": {}}
