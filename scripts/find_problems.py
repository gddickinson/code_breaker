"""Look for new unsolved codes on public lists and add anything new to the leads database."""
import json
import re
import subprocess
import urllib.parse
from pathlib import Path

from codebreaker import leads as L
from codebreaker.mysteries.corpus import _slugify

UA = "codebreaker-research/0.1"
ROOT = Path(__file__).resolve().parent.parent
CATS = {"Category:Undeciphered historical codes and ciphers": "cipher", "Category:Undeciphered writing systems": "script", "Category:Unsolved problems in cryptography": "problem"}
SKIP = re.compile(r"^(Category|File|Template|List of|Undeciphered writing systems)", re.I)
ALREADY = {"bealeciphers", "ddaycarrierpigeoncipher", "henrydebosnys", "kryptos", "olivierlevasseur", "somertonman", "yogtzecase", "isthmianscript", "zapotecscript", "khitanscripts", "iberianscripts", "cyprominoanscript", "beale1", "beale3", "tamanshud", "dorabella",
           # aliases of tracked codes (2026-11-10): McCormick pages, the Zodiac codes, D'Agapeyeff, Tamam Shud, pigeon, Liber Primus
           "rickymccormicksencryptednotes", "zodiackiller", "dagapeyeffcipher", "tamamshudcase", "pigeonnurp40tw194", "cicada3301"}


def wiki_members(cat):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": "500", "format": "json"})
    r = subprocess.run(["curl", "-sS", "-m", "40", "-A", UA, url], capture_output=True, text=True)
    return [m["title"] for m in json.loads(r.stdout)["query"]["categorymembers"]]


def azdecrypt_files():
    r = subprocess.run(["gh", "api", "repos/doranchak/azdecrypt/contents/AZdecrypt/Ciphers/Unsolved", "--jq", ".[].name"], capture_output=True, text=True)
    return [n[:-4] for n in r.stdout.splitlines() if n.endswith(".txt")]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    db = L.connect()
    known = {norm(r[0]) for r in db.execute("SELECT name FROM codes")} | ALREADY
    added = []
    for cat, kind in CATS.items():
        try:
            for t in wiki_members(cat):
                if SKIP.match(t) or norm(t) in known:
                    continue
                L.upsert_code(db, "w-" + _slugify(t), t, kind, "reported unsolved (Wikipedia category)", source="https://en.wikipedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_")))
                L.add_fact(db, "w-" + _slugify(t), f"Found in {cat}. Needs a verified transcription before any attempt.", "problem finder")
                known.add(norm(t)); added.append(t)
        except Exception as exc:
            L.log(db, f"Problem finder failed on {cat}: {exc!r}")
    new_az = [n for n in azdecrypt_files() if norm(n) not in known and not any(norm(n) in k or k in norm(n) for k in known)]
    for n in new_az:
        L.log(db, f"Problem finder: new AZdecrypt unsolved file {n}")
        added.append(n)
    L.log(db, f"Problem finder added {len(added)} entries: {', '.join(added[:12])}")
    db.commit()
    print(len(added), added[:40], L.summary(db))


if __name__ == "__main__":
    main()
