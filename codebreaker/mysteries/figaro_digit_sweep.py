"""Sweep every documented digit table over the ads: mixed letter-digit words and pure number sequences."""
import json
import random
import re
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher
from html import unescape

from ..languages import ROOT
from ..segment import segment
from ..text import letters
from ..validation import coverage
from .figaro_digit_family import digit_tables, read_share, apply
from .figaro_digit_words import shuffled
from .figaro_keys import OUT

RESULT = ROOT / "data/results/figaro_digit_sweep.json"
MIN_NUMBERS = 12


def numeric_tables() -> list[dict]:
    """Tables whose cipher symbols are numbers, keeping the first letter of each cell."""
    raw = (OUT / "codes.html").read_text(encoding="latin-1", errors="ignore")
    parts = re.split(r"<tr><td>(\d+)</td><td><center>([^<]*)</center>", raw)
    out = []
    for i in range(1, len(parts) - 2, 3):
        m = re.search(r"<table.*?</table>", parts[i + 2], flags=re.S | re.I)
        if not m:
            continue
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), flags=re.S | re.I)
        cells = [[unescape(re.sub(r"<[^>]+>|\s+", "", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, flags=re.S | re.I)] for r in rows]
        if len(cells) < 2:
            continue
        key = {c: p[0].upper() for c, p in zip(cells[0][1:], cells[1][1:]) if c.isdigit() and p and p[0].isalpha()}
        if len(key) >= 12 and any(len(c) >= 2 for c in key):
            out.append({"id": parts[i], "name": unescape(parts[i + 1]), "key": key, "users": unescape(re.sub(r"<[^>]+>", " ", parts[i + 2][m.end():])).replace("\xa0", " ").split()[1:8]})
    return out


def numbers(lines: list[str]) -> list[str]:
    """Numbers from a line that is mostly numbers."""
    nums = re.findall(r"\d+", " ".join(lines))
    letters_n = len(re.findall(r"[A-Za-z]", " ".join(lines)))
    return [str(int(n)) for n in nums] if len(nums) >= MIN_NUMBERS and letters_n <= len(nums) else []


def mixed_words(lines: list[str]) -> str:
    """Every alphanumeric word of a letter-digit ad, keeping words made only of digits."""
    toks = [t.upper() for l in lines for t in re.split(r"[^A-Za-z0-9]+", l) if len(t) >= 2]
    if sum(bool(re.search(r"\d", t) and re.search(r"[A-Z]", t)) for t in toks) < 2:
        return ""
    return " ".join(toks)


def signature(name: str) -> str:
    return name.rsplit("-", 1)[-1].replace(".jpg", "") if "-" in name else ""


def _decode(nums: list[str], key: dict) -> str:
    return "".join(key.get(n, "") for n in nums)


def _best_numeric(nums: list[str], tables: list[dict]) -> tuple:
    best = (0.0, None, "")
    for t in tables:
        p = _decode(nums, t["key"])
        if len(p) >= 0.8 * len(nums):
            c = coverage(p, "fr")
            if c > best[0]:
                best = (c, t, p)
    return best


def _job(a):
    name, lines, seed, mixed, nums_t = a
    out, rnd = [], random.Random(seed)
    sig = signature(name)
    for lset in lines:
        w = mixed_words(lset)
        if len(w.replace(" ", "")) < 20:
            continue
        for t in mixed:
            v = read_share(w, t["key"])
            if v >= 0.55:
                out.append({"kind": "mixed", "image": name, "table": t["id"], "name": t["name"], "author": sig in t["users"] or any(u in w.split() for u in t["users"]), "read": round(v, 3), "null": round(read_share(shuffled(w, rnd), t["key"]), 3), "text": w, "words": apply(w, t["key"])})
    for lset in lines:
        nums = numbers(lset)
        if not nums:
            continue
        c, t, p = _best_numeric(nums, nums_t)
        if t is None:
            continue
        sh = nums[:]
        rnd.shuffle(sh)
        out.append({"kind": "numeric", "image": name, "table": t["id"], "name": t["name"], "author": sig in t["users"], "read": round(c, 3), "null": round(_best_numeric(sh, nums_t)[0], 3), "text": " ".join(nums), "plain": p, "reading": segment(p.lower(), "fr")})
    return out


def _best_rows(rows):
    best = {}
    for r in rows:
        k = (r["image"], r["kind"])
        if k not in best or r["read"] - r["null"] > best[k]["read"] - best[k]["null"]:
            best[k] = r
    return sorted(best.values(), key=lambda r: -(r["read"] - r["null"]))


def run() -> dict:
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    ads = json.loads((OUT / "ads.json").read_text())
    mixed, nums = digit_tables(), numeric_tables()
    jobs = {True: [], False: []}
    known = {}
    for i, a in enumerate(ads):
        n = a["image"].replace("/", "_")
        lines = [e for s in (otsu, raw) for e in s.get(n, {}).values()]
        if lines:
            jobs[a["solved"]].append((n, lines, 500 + i, mixed, nums))
            if a["solved"]:
                known[n] = letters(re.sub(r"\([a-z]+\)\s*$|\[|\]|\?", "", a["text"]))
    with ProcessPoolExecutor(7) as ex:
        ctrl = _best_rows([r for x in ex.map(_job, jobs[True], chunksize=6) for r in x])
        rows = _best_rows([r for x in ex.map(_job, jobs[False], chunksize=6) for r in x])
    for r in ctrl:
        got = r.get("plain") or "".join(r["words"]).replace(".", "")
        r["match"] = round(SequenceMatcher(None, known[r["image"]], got, autojunk=False).ratio(), 3)
    return {"id": "figaro_digit_sweep", "mixed_tables": len(mixed), "numeric_tables": len(nums), "solved_ads_with_ocr": len(jobs[True]), "control_rows": ctrl, "control_correct": sum(r["match"] >= 0.6 for r in ctrl), "control_hits": len(ctrl), "tested": len(jobs[False]), "rows": rows}


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print({k: v for k, v in out.items() if k not in ("rows", "control_rows")})
    print([(r["image"], r["kind"], r["table"], r["read"], r["null"], r["match"]) for r in out["control_rows"][:15]])
    for r in [x for x in out["rows"] if x["read"] - x["null"] >= 0.3][:32]:
        print(r["kind"][:3], r["image"], r["table"], r["name"], "A" if r["author"] else "-", r["read"], r["null"], (r.get("reading") or " ".join(r["words"]))[:100])
