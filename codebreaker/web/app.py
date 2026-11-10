"""FastAPI routes for the local Code Breaker app. Start with: python run.py"""
import random
import re
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
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


@app.middleware("http")
async def no_stale_pages(request, call_next):
    """This is a local app under active development, so browsers must not keep old files."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response

_challenges: dict[str, dict] = {}
CHALLENGE_POOL = {
    "easy": ["caesar", "atbash", "affine", "railfence", "scytale"],
    "medium": ["substitution", "vigenere", "beaufort", "columnar", "polybius", "autokey"],
    "hard": ["playfair", "bifid", "adfgx", "hill", "homophonic", "enigma"],
}


VERIFIED = [
    {"name": "Beale cipher 2", "text": "I have deposited in the county of Bedford about four miles from Buford's...", "how": "Book cipher keyed by the Declaration of Independence.", "href": "#/mystery/beale", "solved_by": "Solved in the 19th century"},
    {"name": "Kryptos K1, K2 and K3", "text": "Between subtle shading and the absence of light lies the nuance of iqlusion...", "how": "Quagmire III with KRYPTOS, PALIMPSEST and ABSCISSA; K3 by double grid rotation.", "href": "#/mystery/kryptos", "solved_by": "Solved publicly in the 1990s"},
    {"name": "Zodiac Z408 (92% of letters)", "text": "...because it is so much fun...", "how": "Homophonic annealing, with no key given.", "href": "#/mystery/zodiac", "solved_by": "Solved by Donald and Bettye Harden, 1969"},
    {"name": "Liber Primus pages 56 and 57", "text": "An end within the deep web there exists a page that hashes to...", "how": "Prime-number stream, and plain runes.", "href": "#/mystery/liber_primus", "solved_by": "Solved by the Cicada community"},
    {"name": "Le Figaro ad signed IGNOTA, 1 July 1896", "text": "Ferai tout mon possible pour venir voir enfant dans un mois...", "how": "Reversal then substitution, found by our hunter with no hints.", "href": "#/mystery/figaro_keys", "solved_by": "Already in the Le Figaro database"},
]


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


class CrackIn(BaseModel):
    text: str
    budget: float = 45
    lang: str | None = None


@app.post("/api/crack")
def run_crack(body: CrackIn):
    """Send each stage as one line of JSON as soon as it is finished."""
    import json

    from ..crack import crack
    from ..submissions import record_verdict

    if not body.text.strip():
        raise HTTPException(400, "Paste some ciphertext first.")

    def lines():
        try:
            for ev in crack(body.text, min(max(body.budget, 8), 180), body.lang):
                if ev["event"] == "finish":
                    record_verdict(body.text, ev["verdict"]["level"])
                yield json.dumps(ev, ensure_ascii=False, default=str) + "\n"
        except Exception as exc:  # shown beside the steps that have already arrived
            yield json.dumps({"event": "error", "message": f"{type(exc).__name__}: {exc}"}) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")


class SubmitIn(BaseModel):
    name: str
    text: str
    source: str = ""
    notes: str = ""
    best: dict | None = None


@app.post("/api/submissions")
def add_submission(body: SubmitIn):
    from ..submissions import submit

    return guarded(submit, body.name, body.text, body.source, body.notes, body.best)


@app.get("/api/submissions")
def list_submissions():
    from ..submissions import listing

    return listing()


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


@app.get("/api/codes/open")
def open_codes():
    from .. import leads as L

    db = L.connect()
    rows = [r.as_dict() for r in db.execute("""SELECT c.slug, c.name, c.category, c.status, c.origin, c.tokens, c.symbols, c.source, c.data_path,
        (SELECT count(*) FROM leads l WHERE l.code=c.slug AND l.status NOT IN ('rejected','confirmed')) leads,
        (SELECT count(*) FROM attempts t JOIN avenues a ON a.id=t.avenue WHERE a.code=c.slug) attempts FROM codes c ORDER BY c.name""")]
    closed = re.compile(r"^(solved|yes)|^solved previously|solved in|^partially solved", re.I)
    still_open = [r for r in rows if not closed.search(r["status"] or "") or "privately" in (r["status"] or "")]
    return {"codes": still_open, "extra": [{"name": "Le Figaro personal ads", "count": 1257, "note": "Listed as undecrypted in Didier Muller's database. Counted as one group here. A few appear below with candidate readings.", "href": "#/mystery/figaro_keys"}]}


@app.get("/api/solutions")
def solutions():
    from .. import leads as L

    db = L.connect()
    items = []
    for r in db.execute("""SELECT l.*, c.name, c.source FROM leads l JOIN codes c ON c.slug=l.code
                           WHERE l.origin IN ('figaro hunt','figaro keys') AND l.status NOT IN ('rejected') ORDER BY c.name"""):
        d = r.as_dict()
        text = f"{d['detail']} {d['evidence']}"
        if "partly read" in text.lower():
            d["tier"] = "partial"
        elif "Passes control" in text:
            d["tier"] = "passes"
        else:
            d["tier"] = "strong"
        items.append(d)
    return {"verified": VERIFIED, "candidates": items}


class CubeIn(BaseModel):
    facelets: str


@app.post("/api/cube/solve")
def cube_solve(body: CubeIn):
    import kociemba

    if body.facelets == "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB":
        return {"moves": []}
    return {"moves": guarded(kociemba.solve, body.facelets).split()}


@app.get("/api/publications")
def publications(q: str = "", topic: str = "", page: int = 0):
    from .. import leads as L

    db = L.connect()
    where, args = ["1=1"], []
    if topic:
        where.append("topic=?")
        args.append(topic)
    for w in q.split()[:6]:
        where.append("(title LIKE ? OR authors LIKE ? OR venue LIKE ?)")
        args += [f"%{w}%"] * 3
    cond = " AND ".join(where)
    total = db.execute(f"SELECT count(*) FROM publications WHERE {cond}", tuple(args)).fetchone()[0]
    rows = [r.as_dict() for r in db.execute(f"SELECT * FROM publications WHERE {cond} ORDER BY citations DESC, year DESC LIMIT 40 OFFSET ?", tuple(args) + (max(page, 0) * 40,))]
    topics = [{"topic": r[0], "n": r[1]} for r in db.execute("SELECT topic, count(*) FROM publications GROUP BY 1 ORDER BY 2 DESC")]
    return {"total": total, "rows": rows, "topics": topics, "page": page}


class ImageIn(BaseModel):
    image: str


@app.post("/api/sudoku/read")
def sudoku_read(body: ImageIn):
    from ..sudoku_vision import decode_image, read_grid

    return {"grid": guarded(lambda: read_grid(decode_image(body.image)))}


@app.get("/api/theory/bigrams")
def theory_bigrams():
    """English letter-pair probabilities, for the inference simulations."""
    import numpy as np

    from ..text import to_ints

    t = to_ints(corpus_text("en"))
    c = np.bincount(t[:-1] * 26 + t[1:], minlength=676).astype(float) + 0.5
    m = c.reshape(26, 26)
    return {"transition": (m / m.sum(1, keepdims=True)).round(5).tolist(), "sample": letters(corpus_text("en"))[60000:60900]}


@app.get("/api/leads/feed")
def lead_feed():
    from .. import leads as L

    db = L.connect()
    verdicts = {r[0]: r[1] for r in db.execute("""SELECT CASE WHEN verdict LIKE 'Readable%' THEN 'Readable' WHEN verdict LIKE 'Structure%' THEN 'Structure only' WHEN verdict LIKE 'No evidence%' THEN 'No evidence' ELSE 'Inconclusive' END v, count(*) FROM attempts GROUP BY v""")}
    latest = [r.as_dict() for r in db.execute("SELECT t.at, c.name, a.strategy, a.param, a.lang, t.z, t.verdict FROM attempts t JOIN avenues a ON a.id=t.avenue JOIN codes c ON c.slug=a.code ORDER BY t.id DESC LIMIT 14")]
    hourly = [{"hour": r[0], "attempts": r[1]} for r in db.execute("SELECT substr(at,1,13), count(*) FROM attempts GROUP BY 1 ORDER BY 1")]
    events = [r.as_dict() for r in db.execute("SELECT l.created, c.name, l.title, l.status FROM leads l JOIN codes c ON c.slug=l.code ORDER BY l.created DESC LIMIT 20")]
    return {"verdicts": verdicts, "latest": latest, "hourly": hourly, "events": events, "summary": L.summary(db)}


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
    if name == "anneal":
        import numpy as np

        from ..text import to_ints

        t = to_ints(corpus_text("en"))
        c = np.bincount(t[:-2] * 676 + t[1:-1] * 26 + t[2:], minlength=17576).astype(float)
        table = np.log10((c + 0.3) / c.sum()).round(2).tolist()
        r = random.Random()
        text = letters(corpus_text("en"))
        start = r.randrange(20000, len(text) - 20000)
        return {"trigrams": table, "passage": text[start:start + 520]}
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


from .routes_devices import router as _devices  # noqa: E402  (after app exists, to keep this file short)

app.include_router(_devices)
from .routes_files import router as _files  # noqa: E402

app.include_router(_files)
from .routes_sounds import router as _sounds  # noqa: E402

app.include_router(_sounds)
from .routes_codes import router as _codes  # noqa: E402

app.include_router(_codes)
