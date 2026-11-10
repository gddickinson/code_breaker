"""Round 42: every documented system on its own writers' unsolved ads, judged against every other documented system.

Systems: the database's substitution tables (with their users) and its three Vigenere keys without W (BCD: 234 and X;
CEAD: C. H. and VE; CD: 54). Each ad is cut into enciphered blocks (plain stretches removed, Round 40). Every system is
applied with no free parameter (tables directly; Vigenere restarting at each block, as C. H. did), so all systems have
the same freedom. If the writer's own system reads the ad, it should rank first among all systems; by chance it ranks
first with probability (own systems) / (all systems). Readings that rank first and reach the word bar are candidates to
check by eye."""
import json
import re
from html import unescape
from math import comb

from ..languages import ROOT, score
from ..validation import coverage
from .figaro_keys import OUT, TABLES, cipher_words
from .figaro_plainness import clean
from .figaro_pooled import plain_mask, signature

RESULT = ROOT / "data/results/figaro_documented.json"
NOW = "ABCDEFGHIJKLMNOPQRSTUVXYZ"
MIN_BLOCK, MIN_LETTERS = 4, 12
WORD_BAR = 0.33  # 0.8 of the coverage of printed C. H. text of this length (Round 41 control)


def vigenere_systems() -> list[dict]:
    raw = (OUT / "codes.html").read_text(encoding="latin-1", errors="ignore")
    out = []
    for sid, name, chunk in re.findall(r"<tr><td>(\d+)</td><td><center>([^<]*)</center>(.*?)(?=<tr><td>\d+</td>|$)", raw, flags=re.S):
        text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", chunk)))
        m = re.search(r"Vigen.re avec la clef ([A-Z]+)", text)
        if m:
            users = text[m.end():].split()
            out.append({"id": sid, "key": m.group(1), "users": [u for u in users if not u.isdigit() or u == name][-3:] + [name]})
    return out


def systems() -> list[dict]:
    out = [{"id": t["id"], "kind": "table", "map": t["map"], "users": set(t["users"])} for t in TABLES]
    out += [{"id": f"vig {v['key']}", "kind": "vigenere", "key": v["key"], "users": set(v["users"])} for v in vigenere_systems()]
    return out


def apply(system: dict, block: str) -> str:
    if system["kind"] == "table":
        return "".join(system["map"].get(c, "?") for c in block)
    k = system["key"]
    b = block.replace("W", "V")
    return "".join(NOW[(NOW.index(c) - NOW.index(k[i % len(k)])) % 25] for i, c in enumerate(b))


def blocks(text: str) -> list[str]:
    """Runs of letters that are not plain French, each at least MIN_BLOCK long."""
    t = clean(text)
    mask, out, cur = plain_mask(t), [], ""
    for c, plain in zip(t, mask):
        if plain:
            if len(cur) >= MIN_BLOCK:
                out.append(cur.upper())
            cur = ""
        else:
            cur += c
    if len(cur) >= MIN_BLOCK:
        out.append(cur.upper())
    return out


def ad_blocks() -> dict:
    ads = {a["image"].replace("/", "_"): a for a in json.loads((OUT / "ads.json").read_text())}
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    out = {}
    for n in sorted(set(otsu) | set(raw)):
        a = ads.get(n)
        if a is None or a["solved"] in (True, "True"):
            continue
        sets = [e for s in (otsu, raw) for e in s.get(n, {}).values() if e]
        t = "".join(max((cipher_words(e) for e in sets), key=lambda w: sum(map(len, w)), default=[]))
        b = blocks(t)
        if sum(map(len, b)) >= MIN_LETTERS:
            out[n] = b
    return out


def judge(blocks_: list[str], allsys: list[dict], own: set) -> dict:
    scored = []
    for s in allsys:
        plain = " ".join(apply(s, b) for b in blocks_)
        scored.append((score(plain.replace(" ", "").replace("?", ""), "fr"), s["id"], plain))
    scored.sort(key=lambda x: -x[0])
    rank = next(i for i, x in enumerate(scored) if x[1] in own) + 1
    best_own = next(x for x in scored if x[1] in own)
    return {"rank": rank, "of": len(scored), "own": best_own[1], "own_score": round(best_own[0], 3), "top": scored[0][1],
            "reading": best_own[2], "coverage": coverage(best_own[2].replace(" ", "").replace("?", ""), "fr")}


def shuffle_null(blocks_: list[str], system: dict, n: int = 600, seed: int = 42) -> list[float]:
    """Coverage of the own system's output on shuffled copies of the blocks (letters shuffled across blocks)."""
    import random

    rnd, flat, sizes = random.Random(seed), list("".join(blocks_)), [len(b) for b in blocks_]
    out = []
    for _ in range(n):
        rnd.shuffle(flat)
        pos, parts = 0, []
        for k in sizes:
            parts.append("".join(flat[pos:pos + k]))
            pos += k
        out.append(coverage("".join(apply(system, b) for b in parts).replace("?", ""), "fr"))
    return out


def run() -> dict:
    allsys = systems()
    users = {}
    for s in allsys:
        for u in s["users"]:
            users.setdefault(u, set()).add(s["id"])
    rows, expected = [], 0.0
    for n, b in ad_blocks().items():
        own = users.get(signature(n))
        if not own:
            continue
        r = judge(b, allsys, own)
        expected += len(own) / len(allsys)
        rows.append({"image": n, "signature": signature(n), "blocks": b, **r, "candidate": r["rank"] == 1 and r["coverage"] >= WORD_BAR})
    firsts = sum(r["rank"] == 1 for r in rows)
    p = expected / len(rows) if rows else 0
    tail = sum(comb(len(rows), k) * p ** k * (1 - p) ** (len(rows) - k) for k in range(firsts, len(rows) + 1))
    rows.sort(key=lambda r: (r["rank"], -r["coverage"]))
    byid = {x["id"]: x for x in allsys}
    first = [r for r in rows if r["rank"] == 1]
    for r in first:
        ns = shuffle_null(r["blocks"], byid[r["own"]])
        r["null_p"] = round((sum(x >= r["coverage"] for x in ns) + 1) / (len(ns) + 1), 4)
        r["candidate"] = r["coverage"] >= WORD_BAR and r["null_p"] <= 0.05 / max(len(first), 1)
    return {"id": "figaro_documented", "systems": len(allsys), "ads": len(rows), "own_first": firsts, "expected_first": round(expected, 1),
            "p_value": tail, "candidates": [r["image"] for r in rows if r["candidate"]], "rows": rows}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print({k: v for k, v in res.items() if k != "rows"})
    for r in res["rows"][:30]:
        print(r["image"][:13], r["signature"], r["own"], f"{r['rank']}/{r['of']}", r["coverage"], r["reading"][:90])
