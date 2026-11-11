"""Benchmark on real historical material with known answers (Round 87).

Tier 1, real ciphertext with a published solution: Kryptos K1-K3 (saved Wikipedia page; truth from the published
keys and method, kryptos.py) and Beale 2 (Beale pamphlet numbers; truth decoded with the Declaration of Independence,
beale.py). Tier 2, real plaintext under its documented system: Le Figaro personal-column ads solved in Didier Muller's
database, re-enciphered with the system the database documents for their writer: Vigenere with the keys CEAD, BCD or
CD (alphabet without W), reading backwards, or the writer's substitution table when the signature belongs to exactly
one table. Tier 2 keeps the real language, lengths and abbreviations of 1875-1890 ads, but not the clerks' slips, so
it is an upper bound on what the solvers do on the scans. Müller's bracketed expansions ("v[ous]") were not
enciphered and are dropped; so are the solver's initials and a leading signature.
Scoring: share of letters right against the truth (text.similarity), and whether the crack's verdict called a wrong
answer readable (the error that matters most)."""
import json
import random
import re

from ..languages import ROOT
from ..text import letters
from ..third_party import need

ADS = ROOT / "data/sources/figaro/ads.json"
NOW = "ABCDEFGHIJKLMNOPQRSTUVXYZ"
VIG = {"CEAD": "Vigenère avec la clef CEAD", "BCD": "Vigenère avec la clef BCD", "CD": "Vigenère avec la clef CD"}


def tier1() -> list[dict]:
    from ..ciphers.polyalphabetic import quag_d
    from . import beale
    from .kryptos import rotate_decrypt, sections

    s = sections()
    out = [{"name": "Kryptos K1", "tier": 1, "system": "Quagmire III, KRYPTOS / PALIMPSEST", "cipher": s["K1"], "truth": letters(quag_d(s["K1"], "KRYPTOS", "PALIMPSEST")), "lang": "en"},
           {"name": "Kryptos K2", "tier": 1, "system": "Quagmire III, KRYPTOS / ABSCISSA", "cipher": s["K2"], "truth": letters(quag_d(s["K2"], "KRYPTOS", "ABSCISSA")), "lang": "en"},
           {"name": "Kryptos K3", "tier": 1, "system": "double rotation transposition", "cipher": s["K3"], "truth": letters(rotate_decrypt(s["K3"])[0]), "lang": "en"}]
    nums = beale.ciphers()["B2"] if "B2" in beale.ciphers() else None
    if nums:
        out.append({"name": "Beale 2", "tier": 1, "system": "book cipher, Declaration of Independence", "cipher": " ".join(map(str, nums)),
                    "truth": letters(beale.decode(nums, beale.initials("declaration.txt"))), "lang": "en"})
    return out


def _signature(image: str) -> str:
    return image.rsplit("/", 1)[-1].split("-", 1)[-1].rsplit(".", 1)[0]


def enciphered_part(text: str, sig: str) -> str:
    t = re.sub(r"\[[^\]]*\]", "", text)                  # the solver's expansions were never enciphered
    t = re.sub(r"\((?:[a-z]{1,5})\)\s*$", "", t.strip())  # solver's initials, e.g. (dm)
    t = re.split(r"\(\w{1,5}\)", t)[0]                     # and any comment after them
    head = t.split(" - ", 1)
    if len(head) == 2 and letters(head[0]) and letters(head[0]).startswith(letters(sig)[:2]):
        t = head[1]                                        # leading signature or address left plain
    return letters(t)


def _vig_enc(t: str, key: str) -> str:
    t = t.replace("W", "V")  # the writers' alphabet had no W
    ks = [NOW.index(c) for c in key]
    return "".join(NOW[(NOW.index(c) + ks[i % len(ks)]) % 25] for i, c in enumerate(t))


def tier2(per_system: int = 12, min_letters: int = 30, seed: int = 87) -> list[dict]:
    from .figaro_keys import TABLES

    ads = [a for a in json.loads(need(ADS).read_text()) if a["solved"] and a["text"]]
    by_sig = {}
    for t in TABLES:
        for u in t["users"]:
            by_sig.setdefault(u.lower(), []).append(t)
    groups = {}
    for a in ads:
        sig = _signature(a["image"])
        plain = enciphered_part(a["text"], sig)
        if len(plain) < min_letters:
            continue
        item = {"tier": 2, "name": a["image"], "date": a["date"], "truth": plain, "lang": "fr"}
        key = next((k for k, v in VIG.items() if a["note"].startswith(v)), None)
        if key:
            groups.setdefault(f"Vigenere {key}", []).append({**item, "system": f"Vigenere {key} (no W)", "cipher": _vig_enc(plain, key), "truth": plain.replace("W", "V")})
        elif a["note"].startswith("Lire les lettres"):
            groups.setdefault("reversed", []).append({**item, "system": "letters read backwards", "cipher": plain[::-1]})
        elif a["note"] == "chiffré" and len(by_sig.get(sig.lower(), [])) == 1:
            t = by_sig[sig.lower()][0]
            enc = {}
            for c, p in sorted(t["map"].items()):  # map: cipher letter -> plain letter; invert, first cipher letter wins
                enc.setdefault(p, c)
            if all(c in enc for c in plain):
                groups.setdefault("substitution table", []).append({**item, "system": f"table {t['id']}", "cipher": "".join(enc[c] for c in plain)})
    rnd = random.Random(seed)
    out = []
    for name, items in sorted(groups.items()):
        rnd.shuffle(items)
        out += items[:per_system * (3 if name == "substitution table" else 1)]
    return out


def items(**kw) -> list[dict]:
    return tier1() + tier2(**kw)
