"""Codes submitted from the Workbench: saved exactly as given, checked for duplicates, and queued for the hunter."""
import re

from . import leads as L
from .languages import ROOT
from .mysteries.catalog import _avenues
from .mysteries.corpus import _slugify
from .mysteries.sweep import tokens

FOLDER = ROOT / "data/sources/submitted"
MIN_TOKENS = 20
ORIGIN = "submitted from the Workbench"
_VERDICTS: dict[str, str] = {}


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def record_verdict(text: str, level: str) -> None:
    """Remember how the latest finished crack of this text ended."""
    if len(_VERDICTS) > 500:
        _VERDICTS.clear()
    _VERDICTS[_norm(text)] = level


def _duplicate(db, text: str):
    """A tracked code holding the same symbols, ignoring spacing and case."""
    want = _norm(text)
    for r in db.execute("SELECT slug, name, data_path FROM codes WHERE data_path IS NOT NULL"):
        p = ROOT / r["data_path"]
        if p.is_file() and p.stat().st_size < 2_000_000 and _norm(p.read_text(errors="ignore")) == want:
            return {"slug": r["slug"], "name": r["name"]}
    return None


def _free_slug(db, name: str) -> str:
    base = "sub-" + (_slugify(name)[:50] or "untitled")
    slug, n = base, 2
    while list(db.execute("SELECT 1 FROM codes WHERE slug=?", (slug,))):
        slug, n = f"{base}-{n}", n + 1
    return slug


def submit(name: str, text: str, source: str = "", notes: str = "", best: dict | None = None) -> dict:
    name, text, source, notes = name.strip(), text.strip(), source.strip(), notes.strip()
    if not name:
        raise ValueError("Give the code a name.")
    if len(_norm(text)) < 4:
        raise ValueError("Paste the ciphertext first.")
    if len(text) > 200_000:
        raise ValueError("That text is too long to store here (limit 200,000 characters).")
    level = _VERDICTS.get(_norm(text))
    if level is None:
        raise ValueError("Run Crack it on this text first and let it finish. Only codes the Workbench cannot read are added.")
    if level == "readable":
        return {"status": "solved", "message": "The Workbench has already read this one, so it does not need further work."}
    db = L.connect()
    dup = _duplicate(db, text)
    if dup:
        return {"status": "duplicate", **dup}
    slug = _free_slug(db, name)
    FOLDER.mkdir(parents=True, exist_ok=True)
    path = FOLDER / f"{slug}.txt"
    path.write_text(text + "\n")
    seq = tokens(text)
    L.upsert_code(db, slug, name, "cipher", "submitted, being worked on", ORIGIN, str(path.relative_to(ROOT)), len(seq), len(set(seq)), source)
    L.add_fact(db, slug, f"Submitted from the Workbench. Source given: {source or 'none'}.", "workbench")
    if notes:
        L.add_fact(db, slug, f"Submitter's note: {notes}", "workbench")
    before = list(db.execute("SELECT count(*) FROM avenues WHERE code=?", (slug,)))[0][0]
    _avenues(db, slug, len(seq))
    count = list(db.execute("SELECT count(*) FROM avenues WHERE code=?", (slug,)))[0][0] - before
    if best and best.get("reading"):
        L.add_lead(db, slug, f"Workbench reading ({best.get('cipher', 'unknown method')}, {best.get('lang', '')})", str(best["reading"])[:900], f"Workbench verdict: {best.get('verdict', 'not given')}. Coverage {best.get('coverage')}. Needs checking by a person.", "needs_review", "workbench")
    if count == 0:
        L.add_fact(db, slug, f"Only {len(seq)} symbols, below the {MIN_TOKENS} the hunter needs. Kept on file.", "workbench")
    L.log(db, f"Workbench submission added: {name} ({len(seq)} symbols, {count} avenues).")
    db.commit()
    return {"status": "added", "slug": slug, "name": name, "symbols": len(seq), "avenues": count, "hunted": count > 0}


def listing() -> list[dict]:
    db = L.connect()
    rows = db.execute("""SELECT c.slug, c.name, c.tokens, c.updated,
        (SELECT count(*) FROM avenues a WHERE a.code=c.slug) avenues,
        (SELECT coalesce(sum(a.runs),0) FROM avenues a WHERE a.code=c.slug) runs,
        (SELECT count(*) FROM leads l WHERE l.code=c.slug) leads
        FROM codes c WHERE c.origin=? ORDER BY c.updated DESC LIMIT 60""", (ORIGIN,))
    return [{"slug": r[0], "name": r[1], "symbols": r[2], "updated": r[3], "avenues": r[4], "runs": r[5], "leads": r[6]} for r in rows]
