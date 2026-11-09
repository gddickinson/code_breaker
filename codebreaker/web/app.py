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
