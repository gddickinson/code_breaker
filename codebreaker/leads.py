"""SQLite store of every code, fact, lead, avenue and attempt. The project's long-term memory."""
from datetime import datetime, timezone

from .languages import ROOT
from .litedb import Connection

DB = ROOT / "data/leads.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS codes(slug TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT, status TEXT, origin TEXT, data_path TEXT, tokens INTEGER, symbols INTEGER, source TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY, code TEXT REFERENCES codes(slug), fact TEXT, source TEXT, added TEXT, UNIQUE(code, fact));
CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY, code TEXT REFERENCES codes(slug), title TEXT, detail TEXT, evidence TEXT, status TEXT DEFAULT 'open', origin TEXT, created TEXT, updated TEXT, UNIQUE(code, title));
CREATE TABLE IF NOT EXISTS avenues(id INTEGER PRIMARY KEY, code TEXT REFERENCES codes(slug), strategy TEXT, param TEXT DEFAULT '', lang TEXT DEFAULT '', priority REAL DEFAULT 1, status TEXT DEFAULT 'open', runs INTEGER DEFAULT 0, level INTEGER DEFAULT 0, last_run TEXT, best_z REAL, best_score REAL, notes TEXT DEFAULT '', UNIQUE(code, strategy, param, lang));
CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, avenue INTEGER REFERENCES avenues(id), at TEXT, seed INTEGER, level INTEGER, z REAL, score REAL, control REAL, verdict TEXT, reading TEXT);
CREATE TABLE IF NOT EXISTS journal(id INTEGER PRIMARY KEY, at TEXT, entry TEXT);
CREATE INDEX IF NOT EXISTS av_pick ON avenues(status, runs, priority);
"""
LEAD_STATES = ("open", "needs_review", "testing", "promising", "rejected", "confirmed")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> Connection:
    db = Connection(DB, timeout=30)
    db.executescript(SCHEMA)
    return db


def upsert_code(db, slug, name, category, status, origin="", data_path=None, tokens=None, symbols=None, source=""):
    """Add or refresh a code without losing data recorded by an earlier, richer entry."""
    db.execute("""INSERT INTO codes VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET
        category=COALESCE(excluded.category,category), status=excluded.status, origin=COALESCE(NULLIF(excluded.origin,''),origin),
        data_path=COALESCE(excluded.data_path,data_path), tokens=COALESCE(excluded.tokens,tokens), symbols=COALESCE(excluded.symbols,symbols),
        source=COALESCE(NULLIF(excluded.source,''),source), updated=excluded.updated""", (slug, name, category, status, origin, data_path, tokens, symbols, source, now()))


def add_fact(db, code, fact, source=""):
    db.execute("INSERT OR IGNORE INTO facts(code,fact,source,added) VALUES(?,?,?,?)", (code, fact, source, now()))


def add_lead(db, code, title, detail, evidence="", status="open", origin="analysis"):
    db.execute("INSERT OR IGNORE INTO leads(code,title,detail,evidence,status,origin,created,updated) VALUES(?,?,?,?,?,?,?,?)", (code, title, detail, evidence, status, origin, now(), now()))


def set_lead(db, lead_id, status, note=""):
    if status not in LEAD_STATES:
        raise ValueError(f"Unknown lead status {status}")
    db.execute("UPDATE leads SET status=?, detail=CASE WHEN ?='' THEN detail ELSE detail||char(10)||? END, updated=? WHERE id=?", (status, note, f"[{now()[:10]}] {note}", now(), lead_id))


def add_avenue(db, code, strategy, param="", lang="", priority=1.0, notes=""):
    db.execute("INSERT OR IGNORE INTO avenues(code,strategy,param,lang,priority,notes) VALUES(?,?,?,?,?,?)", (code, strategy, param, lang, priority, notes))


def log(db, entry):
    db.execute("INSERT INTO journal(at,entry) VALUES(?,?)", (now(), entry))


def summary(db) -> dict:
    one = lambda q: db.execute(q).fetchone()[0]
    return {"codes": one("SELECT count(*) FROM codes"), "with_data": one("SELECT count(*) FROM codes WHERE data_path IS NOT NULL"), "facts": one("SELECT count(*) FROM facts"), "leads": one("SELECT count(*) FROM leads"),
            "open_leads": one("SELECT count(*) FROM leads WHERE status NOT IN ('rejected','confirmed')"), "avenues": one("SELECT count(*) FROM avenues"), "attempts": one("SELECT count(*) FROM attempts"),
            "readable": one("SELECT count(*) FROM attempts WHERE verdict LIKE 'Readable%'")}
