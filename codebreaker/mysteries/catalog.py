"""Fills the leads database with every known mystery, its facts, leads and avenues."""
import json
import math
import re
from pathlib import Path

from .. import leads as L
from ..languages import LANGS, ROOT
from .corpus import _slugify, load

RES, SRC = ROOT / "data/results", ROOT / "data/sources"
RESEARCH = SRC / "research"
WITH_DATA = [
    ("beale-1", "Beale cipher 1", "cipher", "unsolved", "1885", "data/mysteries/beale_raw.json", "https://en.wikisource.org/wiki/The_Beale_Papers"),
    ("beale-3", "Beale cipher 3", "cipher", "unsolved", "1885", "data/mysteries/beale_raw.json", "https://en.wikisource.org/wiki/The_Beale_Papers"),
    ("dagapeyeff", "D'Agapeyeff cipher", "cipher", "unsolved", "1939", "data/sources/wp_dagapeyeff.txt", "https://en.wikipedia.org/wiki/D%27Agapeyeff_cipher"),
    ("tamam-shud", "Tamam Shud code", "cipher", "unsolved", "1948", "data/sources/wp_tamam.txt", "https://en.wikipedia.org/wiki/Somerton_Man"),
    ("kryptos-k4", "Kryptos K4", "cipher", "solved privately, unpublished", "1990", "data/sources/wp_kryptos.txt", "https://en.wikipedia.org/wiki/Kryptos"),
    ("voynich", "Voynich manuscript", "script", "unsolved", "15th century", "data/sources/vms_ZL3b-n.txt", "https://voynich.nu/extra/legacy.html"),
    ("dorabella", "Dorabella cipher", "cipher", "unsolved", "1897", "data/sources/unsolved/Dorabella.txt", "https://en.wikipedia.org/wiki/Dorabella_Cipher"),
    ("pigeon", "Bletchingley pigeon message", "cipher", "unsolved", "c. 1944", "data/sources/research/wp_nps.txt", "https://en.wikipedia.org/wiki/National_Pigeon_Service"),
    ("zodiac-z13", "Zodiac Z13", "cipher", "unsolved", "1970", "data/sources/zodiac/z13.txt", "https://github.com/doranchak/azdecrypt"),
    ("zodiac-z32", "Zodiac Z32", "cipher", "unsolved", "1970", "data/sources/zodiac/z32.txt", "https://github.com/doranchak/azdecrypt"),
]
AZ = "https://github.com/doranchak/azdecrypt/tree/master/AZdecrypt/Ciphers/Unsolved"
SKIP_AZ = ("Beale", "Dorabella", "Kryptos", "D'Agapeyeff", "Taman Shud")
SEEDED_LEADS = [
    ("beale-1", "Alphabetical run under the Declaration", "Decoding B1 with the Declaration gives DEFGHIIJKLMMNO, a 14-letter run.", "0 of 2,000 number shuffles matched (see Beale case)", "promising"),
    ("dagapeyeff", "Pair grid: first digit 6-9, second 1-5", "Pairs fall in a grid, with pair IC near language. Simple substitution in six languages fails, so a further layer is likely.", "Pair IC 0.0697 vs 0.0594 when shifted", "promising"),
    ("tamam-shud", "English word initials", "Letter distribution fits English initials rather than running text.", "Log-likelihood gap 12.42; simulated running text never reached it", "promising"),
    ("tamam-shud", "Rubaiyat initials TSAMSTG", "Seven letters match 'the Son and Malik Shah the Grandson' in FitzGerald's introduction.", "0.25% under English-initial blocks. Must check whether the Somerton copy had this introduction.", "needs_review"),
    ("voynich", "Conditional entropy far below language", "H2 2.34 bits against 3.31-3.58 for six languages.", "Rules out simple substitution of those languages under EVA", "promising"),
    ("kryptos-k4", "Not a simple periodic cipher", "270 of 288 periodic models conflict with Sanborn's clues.", "Periods 27-29 cannot be tested", "open"),
]
ALIASES = {"the beale cryptograms": "beale-1", "beale ciphers": "beale-1", "the dorabella cryptogram": "dorabella", "dorabella cipher": "dorabella", "the somerton man": "tamam-shud", "kryptos": "kryptos-k4", "voynich manuscript": "voynich",
           "the blitz ciphers": "blitz-cipher-page-7", "ricky mccormick s encrypted notes": "ricky-mccormick-page-1", "the rubin cryptogram": "paul-rubin", "the powers cryptogram": "powers-cryptogram", "the copenhagen cryptogram": "copenhagen-cryptogram", "the fair game code": "fair-game-code", "the moustier altar inscriptions": "moustier-st-martin", "the train station robbery cryptogram": "1916-train-station-robbery-cryptogram", "encrypted messages of a nazi spy": "kohler-1944-nazi-spy-message-137", "the scorpion letters": "scorpio-5", "the shugborough inscription": "shugborough"}


def _ascii_slug(name):
    import unicodedata
    return _slugify(unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode())


def _facts(db, slug, seq):
    n, k = len(seq), len(set(seq))
    db.execute("UPDATE codes SET tokens=?, symbols=? WHERE slug=?", (n, k, slug))
    L.add_fact(db, slug, f"{n} symbols in total, {k} distinct.", "measured")
    mono = 88.4 / 3.2
    if k <= 26:
        L.add_fact(db, slug, f"Unicity distance for simple substitution is about {mono:.0f} letters, so this text is {'long enough' if n > mono else 'too short'} to determine a unique key.", "calculated")
    else:
        need = k * math.log2(26) / 3.2
        L.add_fact(db, slug, f"A homophonic key with {k} symbols needs about {need:.0f} letters to be unique, so this text is {'long enough in principle' if n > need else 'too short'}.", "calculated")


def _avenues(db, slug, n):
    if n < 20:
        return
    for code in LANGS:
        L.add_avenue(db, slug, "substitution", "", code, 3.0)
        L.add_avenue(db, slug, "reverse", "", code, 2.0)
    for k in range(2, min(21, n // 4)):
        for code in ("en", "la", "de", "fr"):
            L.add_avenue(db, slug, "columns", str(k), code, 1.5)
            L.add_avenue(db, slug, "undo_columns", str(k), code, 1.2)
            L.add_avenue(db, slug, "boustrophedon", str(k), code, 1.0)
    for k in range(2, min(13, n // 4)):
        for code in ("en", "fr", "la", "de"):
            L.add_avenue(db, slug, "reverse_columns", str(k), code, 1.6)
            L.add_avenue(db, slug, "reverse_undo", str(k), code, 1.6)
    for r in range(2, int(n ** 0.5) + 1):
        if n % r == 0:
            L.add_avenue(db, slug, "spiral", str(n // r), "en", 1.3)


def _text_lists(db):
    for line in (RESEARCH / "wp_undeciphered.txt").read_text().splitlines():
        m = re.match(r"\*+ \[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]", line)
        if m:
            name = m.group(2) or m.group(1)
            status = "partially deciphered" if "partially" in line[:220].lower() else "undeciphered"
            slug = ALIASES.get(name.lower()) or _ascii_slug(name)
            if not db.execute("SELECT 1 FROM codes WHERE slug=?", (slug,)).fetchone():
                L.upsert_code(db, slug, name, "script", status, source="https://en.wikipedia.org/wiki/Undeciphered_writing_systems")
    raw = (RESEARCH / "wp_list_ciphertexts.txt").read_text()
    for name, status in re.findall(r"\| \[\[(?:[^\]|]*\|)?([^\]]+)\]\][^\n]*\n\| \{\{(?:no|yes|partial) \| align=left \| ([^}|]+)", raw):
        slug = ALIASES.get(name.lower()) or _ascii_slug(name)
        if not db.execute("SELECT 1 FROM codes WHERE slug=?", (slug,)).fetchone():
            L.upsert_code(db, slug, name, "historic cipher", status.strip()[:60], source="https://en.wikipedia.org/wiki/List_of_ciphertexts")
    html = (RESEARCH / "schmeh50.html").read_text(errors="ignore")
    for rank, title in re.findall(r"<h[1-6][^>]*>\s*(\d+)\.\s*([^<]+)</h", html):
        import html as H
        name = H.unescape(title).strip().replace("’", " ")
        slug = ALIASES.get(name.lower()) or _ascii_slug(name)
        if not db.execute("SELECT 1 FROM codes WHERE slug=?", (slug,)).fetchone():
            L.upsert_code(db, slug, name.replace(" s ", "'s "), "cipher", "unsolved", source="https://scienceblogs.de/klausis-krypto-kolumne/the-top-50-unsolved-encrypted-messages/")
        L.add_fact(db, slug, f"Ranked {rank} in Klaus Schmeh's Top 50 unsolved encrypted messages.", "Schmeh")


def seed() -> dict:
    db = L.connect()
    for slug, name, cat, status, origin, path, src in WITH_DATA:
        L.upsert_code(db, slug, name, cat, status, origin, path, source=src)
        seq = load(slug, path)
        _facts(db, slug, seq)
        if cat == "cipher":
            _avenues(db, slug, len(seq))
    for p in sorted((SRC / "unsolved").glob("*.txt")):
        if p.name.startswith(("_",) + SKIP_AZ):
            continue
        slug = _ascii_slug(p.stem)
        rel = str(p.relative_to(ROOT))
        L.upsert_code(db, slug, p.stem, "cipher", "listed unsolved", "", rel, source=AZ)
        seq = load(slug, rel)
        _facts(db, slug, seq)
        _avenues(db, slug, len(seq))
    for slug, name, cat, src in (("phaistos-disc", "Phaistos Disc", "script", "https://en.wikipedia.org/wiki/Phaistos_Disc"), ("linear-a", "Linear A", "script", "https://github.com/mwenge/lineara.xyz"), ("liber-primus", "Liber Primus (Cicada 3301)", "cipher", "https://github.com/henkman/liberprimus"), ("rongorongo", "Rongorongo", "script", "https://github.com/jgregoriods/rongopy")):
        L.upsert_code(db, slug, name, cat, "unsolved", "", "data/results/scriptlab.json", source=src)
    res = json.loads((RES / "scriptlab.json").read_text())["scripts"] if (RES / "scriptlab.json").exists() else {}
    for slug, key in (("phaistos-disc", "Phaistos Disc"), ("linear-a", "Linear A"), ("liber-primus", "Liber Primus"), ("rongorongo", "Rongorongo")):
        if key in res:
            p = res[key]
            db.execute("UPDATE codes SET tokens=?, symbols=? WHERE slug=?", (p["tokens"], p["signs"], slug))
            L.add_fact(db, slug, f"{p['tokens']} signs, {p['signs']} distinct; estimated inventory {p['estimated_inventory']} ({p['class']}).", "script lab")
            L.add_fact(db, slug, f"Conditional entropy {p['h2']} bits; mean word length {p['mean_word_length']}.", "script lab")
    L.add_fact(db, "linear-a", "Most surviving words are short administrative records, and the language is unknown, so codebreaking alone cannot read it.", "Wikipedia")
    _text_lists(db)
    for code, title, detail, ev, st in SEEDED_LEADS:
        L.add_lead(db, code, title, detail, ev, st, "first analysis round")
    sw = RES / "sweep.json"
    if sw.exists():
        for r in json.loads(sw.read_text())["rows"]:
            if r.get("z") and r["z"] >= 5 and r.get("control", 0) >= 0.7:
                L.add_lead(db, _ascii_slug(r["name"]), "Non-random symbol order", f"Best fit {r['language']} ({r['model']}) beats shuffled copies at z={r['z']}, but the output has not been shown to read as text. Suggests structure such as a transposition-free system, a code, or a list.", f"Sweep control accuracy {r['control']}", "open", "sweep")
    db.commit()
    return L.summary(db)
