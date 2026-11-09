"""The persistent hunt: run the least-explored avenues, log everything, and escalate effort."""
import json
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from .. import leads as L
from ..attacks.classical import solve_symbols
from ..segment import segment
from ..validation import READABLE, null_test, positive_control, verdict
from .corpus import load

BASE_ITERS = {True: 1200000, False: 40000}


def transform(seq: list, strategy: str, param: str) -> list:
    k = int(param) if param else 0
    if strategy == "substitution":
        return list(seq)
    if strategy == "reverse":
        return list(reversed(seq))
    if strategy == "columns":
        return [x for c in range(k) for x in seq[c::k]]
    if strategy == "undo_columns":
        n, out, pos = len(seq), [None] * len(seq), 0
        for c in range(k):
            h = n // k + (c < n % k)
            out[c::k] = seq[pos:pos + h]
            pos += h
        return out
    if strategy == "boustrophedon":
        return [x for r in range(0, len(seq), k) for x in (seq[r:r + k] if (r // k) % 2 == 0 else seq[r:r + k][::-1])]
    if strategy == "spiral":
        rows = len(seq) // k
        from ..ciphers.transposition import _spiral
        out = [None] * len(seq)
        for x, i in zip(seq, _spiral(rows, k)):
            out[i] = x
        return out
    raise ValueError(strategy)


def work(job: dict) -> dict:
    os.nice(10)
    seq = transform(load(job["code"], job["path"]), job["strategy"], job["param"])
    homo = len(set(seq)) > 26
    iters = BASE_ITERS[homo] * (1 + job["level"])
    nt = null_test(seq, job["lang"], homo, n_null=6, seed=job["seed"], iters=iters, restarts=3)
    pc = job["control"] or positive_control(seq, job["lang"], homo, iters=iters, restarts=3, trials=2)
    v = verdict(pc, nt["z"], job["tests"], nt["plaintext"], nt["score"], job["lang"])
    return {**job, "control": pc, "z": nt["z"], "score": nt["score"], "verdict": v, "reading": segment(nt["plaintext"][:220], job["lang"])}


def _controls(db):
    db.execute("CREATE TABLE IF NOT EXISTS controls(key TEXT PRIMARY KEY, value TEXT)")
    return {r[0]: json.loads(r[1]) for r in db.execute("SELECT key, value FROM controls")}


def hunt(minutes: float = 5, workers: int = 9, seed: int | None = None) -> dict:
    db = L.connect()
    controls = _controls(db)
    rng = random.Random(seed if seed is not None else time.time())
    deadline, done, found = time.time() + minutes * 60, 0, []
    tests = {r[0]: r[1] for r in db.execute("SELECT code, count(*) FROM avenues GROUP BY code")}
    with ProcessPoolExecutor(workers) as ex:
        while time.time() < deadline:
            rows = db.execute("""SELECT a.*, c.data_path FROM avenues a JOIN codes c ON c.slug=a.code WHERE a.status='open' AND c.data_path IS NOT NULL
                                 ORDER BY a.runs ASC, a.priority DESC, RANDOM() LIMIT ?""", (workers * 3,)).fetchall()
            if not rows:
                break
            jobs = []
            for a in rows:
                ck = f"{a['code']}|{a['lang']}|{a['level']}"
                jobs.append({"id": a["id"], "code": a["code"], "path": a["data_path"], "strategy": a["strategy"], "param": a["param"], "lang": a["lang"], "level": a["level"], "seed": rng.randrange(10**8), "tests": tests.get(a["code"], 1), "control": controls.get(ck), "ck": ck})
            for f in as_completed([ex.submit(work, j) for j in jobs]):
                try:
                    r = f.result()
                except Exception as exc:
                    L.log(db, f"Avenue failed: {exc!r}")
                    continue
                done += 1
                controls[r["ck"]] = r["control"]
                db.execute("INSERT OR REPLACE INTO controls VALUES(?,?)", (r["ck"], json.dumps(r["control"])))
                db.execute("INSERT INTO attempts(avenue,at,seed,level,z,score,control,verdict,reading) VALUES(?,?,?,?,?,?,?,?,?)", (r["id"], L.now(), r["seed"], r["level"], r["z"], r["score"], r["control"]["mean"], r["verdict"], r["reading"]))
                db.execute("UPDATE avenues SET runs=runs+1, level=level+?, last_run=?, best_z=MAX(COALESCE(best_z,-99),?), best_score=MAX(COALESCE(best_score,-99),?) WHERE id=?", (1 if rng.random() < 0.25 else 0, L.now(), r["z"], r["score"], r["id"]))
                if r["verdict"].startswith(READABLE):
                    found.append(r)
                    L.add_lead(db, r["code"], f"Readable output: {r['strategy']} {r['param']} {r['lang']}".strip(), r["reading"], r["verdict"], "needs_review", "hunter")
                db.commit()
    L.log(db, f"Hunt ran {done} attempts in {minutes} minutes; {len(found)} readable candidates.")
    db.commit()
    return {"attempts": done, "readable": [{"code": r["code"], "strategy": r["strategy"], "param": r["param"], "lang": r["lang"], "reading": r["reading"][:120]} for r in found], **L.summary(db)}
