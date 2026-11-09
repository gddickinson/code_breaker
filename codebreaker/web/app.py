"""FastAPI routes for the local Code Breaker app. Start with: python run.py"""
import random
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import analysis, translate as tr
from ..ciphers import REGISTRY
from ..ciphers.runner import attack_demo
from ..languages import LANGS, corpus_text
from ..mysteries import casefiles
from ..segment import segment
from ..text import letters, similarity

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Code Breaker")
_challenges: dict[str, dict] = {}
CHALLENGE_POOL = {
    "easy": ["caesar", "atbash", "affine", "railfence", "scytale"],
    "medium": ["substitution", "vigenere", "beaufort", "columnar", "polybius", "autokey"],
    "hard": ["playfair", "bifid", "adfgx", "hill", "homophonic", "enigma"],
}


class RunIn(BaseModel):
    op: str
    text: str
    key: dict = {}


class AttackIn(BaseModel):
    seed: int | None = None
    lang: str = "en"


class SolveIn(BaseModel):
    text: str
    lang: str = "en"


class TextIn(BaseModel):
    text: str
    source: str | None = None


class AnswerIn(BaseModel):
    token: str
    answer: str = ""
    reveal: bool = False


def get(cid: str):
    if cid not in REGISTRY:
        raise HTTPException(404, "Unknown cipher")
    return REGISTRY[cid]


def clean_key(cipher, key: dict) -> dict:
    kinds = {p.name: p.kind for p in cipher.params}
    return {k: (int(v) if kinds.get(k) == "int" and str(v).strip() != "" else v) for k, v in key.items() if str(v).strip() != "" or k == "keyword"}


def guarded(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except HTTPException:
        raise
    except Exception as exc:  # bad keys and malformed ciphertext are user input errors
        raise HTTPException(400, f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/ciphers")
def ciphers():
    return {"ciphers": [c.card() for c in REGISTRY.values()], "languages": LANGS}


@app.get("/api/ciphers/{cid}")
def cipher(cid: str):
    return guarded(get(cid).detail)


@app.post("/api/ciphers/{cid}/run")
def run(cid: str, body: RunIn):
    c = get(cid)
    fn = c.encrypt if body.op == "encrypt" else c.decrypt
    if fn is None:
        raise HTTPException(400, f"{c.name} is one-way")
    return {"output": guarded(fn, body.text, **clean_key(c, body.key))}


@app.post("/api/ciphers/{cid}/attack")
def attack(cid: str, body: AttackIn):
    return guarded(attack_demo, cid, body.seed, body.lang)


@app.post("/api/ciphers/{cid}/solve")
def solve(cid: str, body: SolveIn):
    c = get(cid)
    if not c.attack:
        raise HTTPException(400, "This cipher has a demonstration attack only")
    r = guarded(c.attack, body.text, body.lang)
    return {**r, "spaced": segment(letters(r["plaintext"]), body.lang)}


@app.post("/api/analyze")
def analyze(body: TextIn):
    return guarded(analysis.report, body.text)


@app.post("/api/autobreak")
def run_autobreak(body: TextIn):
    from ..autobreak import autobreak

    return guarded(autobreak, body.text)


@app.post("/api/translate")
def translate(body: TextIn):
    return guarded(tr.translate, body.text, body.source)


@app.get("/api/challenge/{level}")
def challenge(level: str):
    if level not in CHALLENGE_POOL:
        raise HTTPException(404, "Unknown level")
    r = random.Random()
    c = REGISTRY[r.choice(CHALLENGE_POOL[level])]
    text = letters(corpus_text("en"))
    start = r.randrange(20000, len(text) - 20000)
    plain = text[start:start + 320]
    key = c.keygen(r)
    ct = c.encrypt(plain, **key)
    token = secrets.token_urlsafe(8)
    _challenges[token] = {"plain": c.decrypt(ct, **key), "cipher": c.name, "cipher_id": c.id, "key": key}
    return {"token": token, "ciphertext": ct, "level": level}


@app.post("/api/challenge/check")
def check(body: AnswerIn):
    ch = _challenges.get(body.token)
    if not ch:
        raise HTTPException(404, "Challenge expired")
    if body.reveal:
        return {**ch, "spaced": segment(ch["plain"])}
    acc = similarity(ch["plain"], letters(body.answer))
    return {"accuracy": round(acc, 3), "solved": acc > 0.9, **({**ch, "spaced": segment(ch["plain"])} if acc > 0.9 else {})}


class LeadIn(BaseModel):
    status: str
    note: str = ""


@app.get("/api/leads")
def lead_overview():
    from .. import leads as L

    db = L.connect()
    codes = [r.as_dict() for r in db.execute("""SELECT c.*, (SELECT count(*) FROM leads l WHERE l.code=c.slug AND l.status NOT IN ('rejected','confirmed')) open_leads,
        (SELECT count(*) FROM attempts t JOIN avenues a ON a.id=t.avenue WHERE a.code=c.slug) attempts, (SELECT count(*) FROM avenues a WHERE a.code=c.slug) avenues FROM codes c ORDER BY open_leads DESC, attempts DESC, name""")]
    return {"summary": L.summary(db), "codes": codes, "leads": [r.as_dict() for r in db.execute("SELECT l.*, c.name code_name FROM leads l JOIN codes c ON c.slug=l.code WHERE l.status NOT IN ('rejected') ORDER BY l.updated DESC LIMIT 60")],
            "journal": [r.as_dict() for r in db.execute("SELECT * FROM journal ORDER BY id DESC LIMIT 12")]}


@app.get("/api/leads/{slug}")
def lead_code(slug: str):
    from .. import leads as L

    db = L.connect()
    row = db.execute("SELECT * FROM codes WHERE slug=?", (slug,)).fetchone()
    if row is None:
        raise HTTPException(404, "Unknown code")
    q = lambda sql: [r.as_dict() for r in db.execute(sql, (slug,))]
    return {"code": row.as_dict(), "facts": q("SELECT * FROM facts WHERE code=? ORDER BY id"), "leads": q("SELECT * FROM leads WHERE code=? ORDER BY updated DESC"),
            "avenues": q("SELECT * FROM avenues WHERE code=? ORDER BY COALESCE(best_z,-99) DESC, priority DESC LIMIT 40"), "attempts": q("SELECT t.*, a.strategy, a.param, a.lang FROM attempts t JOIN avenues a ON a.id=t.avenue WHERE a.code=? ORDER BY t.z DESC LIMIT 15")}


@app.post("/api/leads/item/{lead_id}")
def lead_update(lead_id: int, body: LeadIn):
    from .. import leads as L

    db = L.connect()
    guarded(L.set_lead, db, lead_id, body.status, body.note)
    return {"ok": True}


@app.get("/api/machines/{name}")
def machine(name: str):
    """Public wheel data for browser simulations, so they match the Python ciphers."""
    from ..ciphers.machines import LORENZ_SIZES, _discs, _lorenz_wheels

    if name == "jefferson":
        return {"discs": _discs()}
    if name == "bombe":
        from ..attacks.bombe import demo

        return guarded(demo, random.randrange(1, 10**6))
    if name == "lorenz":
        return {"sizes": LORENZ_SIZES, "wheels": _lorenz_wheels()}
    raise HTTPException(404, "Unknown machine")


@app.get("/api/mysteries")
def mysteries():
    return {"cases": casefiles.index()}


@app.get("/api/mysteries/{mid}")
def mystery(mid: str):
    out = casefiles.case(mid)
    if out is None:
        raise HTTPException(404, "Unknown case")
    return out


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")
