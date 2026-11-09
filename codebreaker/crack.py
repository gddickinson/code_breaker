"""The full crack: inspect, identify, try every method across languages, and test the best reading against shuffles."""
import re
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait

from . import analysis, classifier
from . import crack_steps as S
from . import crack_worker as W
from .ciphers import REGISTRY
from .languages import LANGS
from .text import letters

READABLE = 0.72
MARGIN = 0.2
MIN_LETTERS = 40
KEY_BITS = {"caesar": 5, "rot13": 0, "atbash": 0, "affine": 9, "morse": 0, "tap": 0, "a1z26": 0, "baconian": 1, "polybius": 90, "railfence": 5, "scytale": 5, "gronsfeld": 34, "trithemius": 5}
FAMILY_BITS = {"Monoalphabetic": 88, "Polyalphabetic": 90, "Transposition": 60, "Polygraphic": 110, "Fractionating": 110, "Machines": 90, "Book and homophonic": 120, "Codes": 0}
ORDER = ["Monoalphabetic", "Codes", "Transposition", "Polyalphabetic", "Polygraphic", "Fractionating", "Machines", "Book and homophonic"]
KEYWORDS = {"Monoalphabetic": ("monoalphabetic", "substitution"), "Polyalphabetic": ("polyalphabetic", "vigenere"), "Transposition": ("transposition",), "Polygraphic": ("polygraphic", "playfair"), "Fractionating": ("adfg", "polybius"), "Codes": ("morse", "baconian", "binary")}


def plan(guesses: list, identified: list) -> list[str]:
    """Most likely first, but every attack stays on the list: a guess only sets the order."""
    attackable = [k for k, c in REGISTRY.items() if c.attack]
    first = [g["id"] for g in guesses if g["id"] in attackable]
    text = " ".join(x["family"].lower() for x in identified)
    fams = [f for f, words in KEYWORDS.items() if any(w in text for w in words)]
    rank = {f: i for i, f in enumerate(fams + [f for f in ORDER if f not in fams])}
    rest = sorted((k for k in attackable if k not in first), key=lambda k: rank.get(REGISTRY[k].family, 99))
    return first + rest


def verdict(best: dict | None, nulls: list, letters_n: int, tried: int) -> dict:
    if best is None:
        return {"level": "none", "label": "Nothing was recovered", "why": "No method produced a usable reading."}
    known = [n for n in nulls if n is not None]
    top = max(known) if known else None
    if best.get("trusted") is False:
        return {"level": "none", "label": "Not cracked", "why": f"The closest result came from {best['cipher']}, but {letters_n} letters are too few for that method: with so many possible keys, almost any short text can be made to look like words. No method with few enough keys produced a reading."}
    if best["coverage"] >= READABLE and top is not None and best["coverage"] - top >= MARGIN and letters_n >= MIN_LETTERS:
        return {"level": "readable", "label": "Readable result", "why": f"{best['cipher']} reads at {best['coverage']:.0%} dictionary coverage. The same attack on shuffled letters reached at most {top:.0%}. {tried} attempts were made, so read the text yourself to confirm."}
    if best["coverage"] >= 0.5:
        return {"level": "partial", "label": "Possible reading, not proven", "why": f"Best coverage is {best['coverage']:.0%}" + (f", with shuffled letters reaching {top:.0%}." if top is not None else ". The null test could not run.") + (" The text is too short to be sure." if letters_n < MIN_LETTERS else " Check it by eye.")}
    return {"level": "none", "label": "Not cracked", "why": f"The best of {tried} attempts covers only {best['coverage']:.0%} of the text with real words. The system may not be one of those tried, or the text may be too short."}


def _quality(a: dict) -> tuple:
    """Exact decodings first, then readings long enough to trust; ties go to the simplest system."""
    return (bool(a.get("decoded")), a.get("trusted", True), a["coverage"], a["score"], -a.get("rank", 99))


def unicity(cid: str) -> int:
    """Letters needed before this method's key is pinned down: key bits over French or English redundancy."""
    return int(KEY_BITS.get(cid, FAMILY_BITS.get(REGISTRY[cid].family if cid in REGISTRY else "", 90)) / 3.2) + 1


def trusted(a: dict, n_letters: int) -> bool:
    return not a.get("cid") or n_letters >= unicity(a["cid"])


def step(sid: str, title: str, summary: str, **data) -> dict:
    return {"event": "step", "id": sid, "title": title, "summary": summary, **data}


def _prelude(raw: str, lang: str | None):
    """Stages that are quick enough to show at once."""
    info = S.inspect(raw)
    yield step("inspect", "Look at the text", f"{info['length']} symbols, {info['symbols']} different, in {info['groups']} groups.", info=info)
    checks = S.plain_check(raw)
    best = max(checks, key=lambda c: c["coverage"], default=None)
    yield step("plain", "Check whether it is already plain text", f"Best fit is {best['name']} at {best['coverage']:.0%} word coverage." if best else "Too few letters to test.", rows=checks)
    found = S.encodings(raw)
    yield step("encodings", "Try keyless encodings", f"{len(found)} decoding(s) produced text." if found else "No encoding applied.", found=found)
    strict = next((f for f in found if f["strict"]), None)
    if strict:
        yield {"event": "_decoded", "found": strict, "info": info}
        return
    if info["letters"] >= 8:
        rep = S.periods(raw)
        yield step("stats", "Measure the statistics", f"Index of coincidence {rep['ic']}. English is near 0.066 and random letters near 0.038.", bars=rep["bars"], bars_title="Mean column IC by key length", kasiski=rep["kasiski"])
        langs = S.language_guess(raw)
        yield step("language", "Compare with known languages", f"Closest as it stands: {langs[0]['name']}.", rows=langs)
    identified = analysis.identify(raw)
    guesses = (classifier.classify(raw, 8) or []) if info["letters"] >= 20 else []
    yield step("identify", "Guess the system", "Rules and a neural network each make a guess. These only set the order of attack.", rules=identified, network=guesses)
    yield {"event": "_plan", "order": plan(guesses, identified), "info": info, "plain": best, "found": found}


def _decoded_finish(found: dict, reads: dict, start: float) -> tuple:
    """An exact decoding that reads as language needs no key search, so it ends the crack."""
    r = S.readable(found["text"], reads["lang"])
    row = {"event": "attempt", "kind": "attempt", "cid": "", "cipher": found["name"], "family": "Encoding", "lang": reads["lang"], "method": "exact decoding, no key to search", "key": "", "plaintext": found["text"][:900], "seconds": 0, "decoded": True, "trusted": True, **r, "spaced": found["text"][:900]}
    v = {"level": "readable", "label": "Decoded", "why": f"This is valid {found['name']}, and it decodes to text that reads as {reads['name']}. No key was searched for, so this is not a lucky match."}
    end = {"event": "finish", "verdict": v, "best": row, "nulls": [], "tried": 1, "readings": 1, "not_applicable": 0, "unfinished": 0, "seconds": round(time.time() - start, 1), "top": [{k: row[k] for k in ("cipher", "lang", "coverage", "score", "method", "key")}]}
    return row, end


def crack(raw: str, budget: float = 45, lang: str | None = None, workers: int = 7, depth: int = 0):
    """Yield events as each stage finishes, stopping at the time budget."""
    raw = raw.strip()
    if not raw:
        raise ValueError("Paste some ciphertext first.")
    start = time.time()
    order, info, plain, found = [], {}, None, []
    for ev in _prelude(raw, lang):
        if ev["event"] == "_decoded":
            reads = S.natural(ev["found"]["text"])
            if reads:
                row, end = _decoded_finish(ev["found"], reads, start)
                yield step("decoded", "Exact decoding found", f"{ev['found']['name']} gives text that reads as {reads['name']}.")
                yield row
                yield end
                return
            if depth < 3:
                yield step("layer", "Decode a layer and continue", f"{ev['found']['name']} decodes cleanly, but the result is not language yet, so every method now runs on the decoded text.", found=[ev["found"]])
                yield from crack(ev["found"]["text"], max(8.0, budget - (time.time() - start)), lang, workers, depth + 1)
                return
        elif ev["event"] == "_plan":
            order, info, plain, found = ev["order"], ev["info"], ev["plain"], ev["found"]
        else:
            yield ev
    primary = lang or "en"
    attempts = []
    for f in found:
        for code in LANGS:
            r = S.readable(f["text"], code)
            attempts.append({"event": "attempt", "kind": "attempt", "cid": "", "cipher": f["name"], "family": "Encoding", "lang": code, "method": "reversible decoding, no key", "key": "", "plaintext": f["text"][:900], "seconds": 0, **r})
    for a in sorted(attempts, key=lambda x: -x["coverage"])[:2]:
        yield a
    attempts = sorted(attempts, key=lambda x: -x["coverage"])[:2]
    if plain and plain["coverage"] >= READABLE:
        plain_row = {"event": "attempt", "kind": "attempt", "cid": "", "cipher": "Already plain text", "family": "None", "lang": plain["lang"], "method": "no decryption needed", "key": "", "plaintext": letters(raw)[:900], "seconds": 0, **S.readable(raw, plain["lang"])}
        attempts.append(plain_row)
        yield plain_row
    jobs = []
    if info["letters"] >= 8:
        jobs += [("trace", n, raw, primary) for n in ("frequency", "caesar", "vigenere")]
        if info["letters"] >= 30:
            jobs.append(("trace", "climb", raw, primary))
    if re.search(r"\d", raw) and re.search(r"[A-Za-z]", raw) and len(raw.split()) >= 3:
        jobs.append(("beam", raw))
    if not info["letters"] or info["symbols"] > 26 or (re.search(r"\d", raw) and not re.search(r"[A-Za-z]", raw)):
        jobs += [("symbols", raw, l) for l in ([lang] if lang else ["en", "fr"])]
    langs = [lang] if lang else list(LANGS)
    for l in langs:
        jobs += [("attack", cid, raw, l) for cid in order]
    yield step("attack", "Try every method", f"{len(order)} attacks in {len(langs)} language(s), most likely first, for up to {budget:.0f} seconds.", planned=len([j for j in jobs if j[0] == "attack"]))
    reserve = max(2.0, budget * 0.12)
    failed, done = 0, 0
    best = max(attempts, key=_quality, default=None)
    ex = ProcessPoolExecutor(max(workers, 1))
    pending, nulls = {}, []
    try:
        q = iter(jobs)
        def fill():
            while len(pending) < workers + 2:
                spec = next(q, None)
                if spec is None:
                    return
                pending[ex.submit(W.job, spec)] = spec
        fill()
        while pending and time.time() - start < budget - reserve:
            ready, _ = wait(pending, timeout=0.25, return_when=FIRST_COMPLETED)
            for f in ready:
                spec = pending.pop(f)
                r = f.result() if not f.exception() else None
                done += 1
                if r is None or r["kind"] == "failed":
                    failed += 1
                    continue
                if r["kind"] == "trace":
                    if r["data"]:
                        yield {"event": "trace", **r}
                    continue
                r["trusted"] = trusted(r, info["letters"])
                attempts.append(r)
                if best is None or _quality(r) > _quality(best):
                    best = r
                yield {"event": "attempt", **r, "elapsed": round(time.time() - start, 1)}
            fill()
        for f in pending:
            f.cancel()
        unfinished = sum(1 for s in pending.values() if s[0] == "attack") + sum(1 for s in q if s[0] == "attack")
        pending.clear()
        if best and best.get("cid"):
            yield step("null", "Test the best result against shuffled letters", "A real solve should read far better than the same attack on scrambled text.")
            nulls_f = [ex.submit(W.job, ("null", best["cid"], raw, best["lang"], s)) for s in range(3)]
            for f in nulls_f:
                left = max(0.5, budget + 8 - (time.time() - start))
                try:
                    nulls.append(f.result(timeout=left)["coverage"])
                except Exception:  # a shuffle that runs out of time gives no evidence
                    nulls.append(None)
    finally:
        for p in list((ex._processes or {}).values()):
            p.kill()
        ex.shutdown(wait=False, cancel_futures=True)
    usable = sum(1 for a in attempts)
    tried = usable + failed
    v = verdict(best, nulls if best and best.get("cid") else ([0.0] if best else []), info["letters"], tried)
    ranked = sorted(attempts, key=_quality, reverse=True)
    yield {"event": "finish", "verdict": v, "best": best, "nulls": nulls, "tried": tried, "readings": usable, "not_applicable": failed, "unfinished": unfinished, "seconds": round(time.time() - start, 1), "top": [{k: a[k] for k in ("cipher", "lang", "coverage", "score", "method", "key")} for a in ranked[:5]]}
