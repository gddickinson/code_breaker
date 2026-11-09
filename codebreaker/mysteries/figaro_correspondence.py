"""Ads written with one documented table, read together as a correspondence, with alternate symbol values tested."""
import json
import re
from itertools import product

from .. import leads as L
from ..languages import ROOT
from ..text import A
from .figaro_digit_family import digit_tables, words as vocabulary
from .figaro_digit_words import HAND
from .figaro_keys import OUT
from .figaro_table_cells import mixed_tokens

RESULT = ROOT / "data/results/figaro_correspondence.json"
FAMILIES = {"2119": {"R": "O"}, "2402": {}}


def slug(image: str) -> str:
    m = re.match(r"\d{4}_(\d{4})(\d\d)(\d\d)([a-z]?)(?:-(.+))?\.jpg", image)
    return f"figaro-{m[1]}-{m[2]}-{m[3]}{m[4]}" + (f"-{m[5].lower()}" if m[5] else "")


def read_alt(ad: list, key: dict, alts: dict) -> int:
    """Letters in dictionary words when each listed symbol may take any of its values."""
    v, n = vocabulary(), 0
    for tok in ad:
        options = [alts.get(p, [key.get(p, ".")]) for p in tok]
        if len(tok) <= 12 and any("".join(c) in v for c in product(*options)):
            n += len(tok)
    return n


def alternative_test(ads: list, key: dict, sym: str) -> list:
    """Rank every second value for a symbol by how many more letters it lets the family read."""
    base = sum(read_alt(a, key, {}) for a in ads)
    gains = []
    for l in A:
        if l != key.get(sym):
            gains.append((sum(read_alt(a, key, {sym: [key.get(sym, "."), l]}) for a in ads) - base, l))
    return sorted(gains, reverse=True)


def family_ads(tid: str) -> list:
    rows = json.loads((ROOT / "data/results/figaro_table_cells.json").read_text())["rows"]
    fam = next(r for r in rows if r["id"] == tid and not r["numeric"])
    hand = json.loads(HAND.read_text())
    otsu, raw = (json.loads((OUT / f).read_text()) for f in ("ocr_otsu.json", "ocr_raw.json"))
    out = []
    for name, _ in fam["family"]:
        if name in hand and "words" in hand[name]:
            out.append((name, [list(w) for w in hand[name]["words"].split()], "hand"))
        else:
            sets = [mixed_tokens(e) for s in (otsu, raw) for e in s.get(name, {}).values() if e]
            out.append((name, max(sets, key=lambda a: sum(map(len, a))), "OCR"))
    return sorted(out)


def run() -> dict:
    db, tables, out = L.connect(), {t["id"]: t for t in digit_tables()}, {"id": "figaro_correspondence", "families": []}
    for tid, extra in FAMILIES.items():
        key = {**tables[tid]["key"], **extra}
        ads = family_ads(tid)
        toks = [a[1] for a in ads]
        test = alternative_test(toks, key, "1") if tid == "2119" else []
        timeline = []
        for name, tok, src in ads:
            lead = list(db.execute("SELECT detail, evidence FROM leads WHERE code=? AND origin='figaro keys' ORDER BY id DESC LIMIT 1", (slug(name),)))
            checked = bool(lead and "checked by eye" in lead[0][1])
            date = f"{name[11:13]}.{name[9:11]}.{name[5:9]}"
            timeline.append({"image": name, "date": date, "signature": name.split("-", 1)[1][:-4] if "-" in name else "", "source": src, "checked": checked, "reading": lead[0][0] if lead else " ".join("".join(key.get(p, ".") for p in t) for t in tok)})
        out["families"].append({"table": tid, "users": tables[tid]["users"], "extra": extra, "ads": len(ads), "checked": sum(t["checked"] for t in timeline), "alternative_for_1": [{"letter": l, "gain": g} for g, l in test[:5]], "timeline": timeline})
    return out


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, ensure_ascii=False, indent=1))
    for f in r["families"]:
        print(f["table"], f["ads"], f["checked"], f["alternative_for_1"])
        for t in f["timeline"]:
            print(" ", t["date"], t["signature"], t["source"], "C" if t["checked"] else "-", t["reading"][:90])
