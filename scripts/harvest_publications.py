"""Build a publications table from Crossref metadata, so each entry has a checkable DOI."""
import json
import re
import subprocess
import time
import urllib.parse

from codebreaker import leads as L

UA = "codebreaker-research/0.1 (academic bibliography tool)"
QUERIES = {
 "Historical cryptology": ["historical ciphers cryptanalysis", "nomenclator cipher decipherment", "Copiale cipher", "Mary Queen of Scots cipher letters", "encrypted historical manuscripts", "homophonic cipher historical"],
 "Classical cryptanalysis": ["simulated annealing cryptanalysis classical cipher", "hill climbing cipher solving", "Vigenere cipher cryptanalysis", "transposition cipher cryptanalysis", "Playfair cryptanalysis", "homophonic substitution solver", "Enigma cryptanalysis ciphertext only"],
 "Unsolved ciphers and lost scripts": ["Voynich manuscript statistical analysis", "Beale cipher", "Zodiac 340 cipher", "Kryptos sculpture cipher", "Linear A decipherment", "Rongorongo script", "Indus script statistical", "Phaistos disc", "lost language decipherment machine learning"],
 "Machines and wartime codebreaking": ["Enigma Bletchley bombe history", "Lorenz cipher Colossus", "Purple cipher machine", "M-209 cryptanalysis", "Venona project"],
 "Modern cryptography": ["communication theory of secrecy systems", "new directions in cryptography", "padding oracle attack CBC", "differential cryptanalysis", "post-quantum cryptography lattice"],
 "Puzzles and recreational maths": ["Rubik's cube diameter group God's number", "two-phase Rubik cube solving", "sudoku mathematics solver", "permutation puzzles group theory", "recreational mathematics puzzles algorithm"],
}
CORE = ["10.1002/j.1538-7305.1949.tb00928.x", "10.1109/TIT.1976.1055638", "10.1145/359340.359342"]


def get(url):
    r = subprocess.run(["curl", "-sS", "-m", "60", "-A", UA, url], capture_output=True, text=True)
    return json.loads(r.stdout)


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def store(db, it, topic):
    doi = it.get("DOI", "").lower()
    title = clean((it.get("title") or [""])[0])
    if not doi or len(title) < 12:
        return 0
    year = None
    for k in ("published-print", "published-online", "published", "issued"):
        parts = (it.get(k) or {}).get("date-parts") or [[None]]
        if parts[0][0]:
            year = parts[0][0]
            break
    authors = "; ".join(f"{a.get('given', '')} {a.get('family', '')}".strip() for a in it.get("author", [])[:8])
    venue = clean((it.get("container-title") or [""])[0])
    before = db.execute("SELECT count(*) FROM publications").fetchone()[0]
    db.execute("INSERT OR IGNORE INTO publications(doi,title,authors,year,venue,type,topic,url,citations,added) VALUES(?,?,?,?,?,?,?,?,?,?)", (doi, title, authors, year, venue, it.get("type", ""), topic, f"https://doi.org/{doi}", it.get("is-referenced-by-count", 0), L.now()))
    return db.execute("SELECT count(*) FROM publications").fetchone()[0] - before


def main():
    db = L.connect()
    db.executescript("CREATE TABLE IF NOT EXISTS publications(doi TEXT PRIMARY KEY, title TEXT, authors TEXT, year INTEGER, venue TEXT, type TEXT, topic TEXT, url TEXT, citations INTEGER, added TEXT);")
    total = 0
    for doi in CORE:
        total += store(db, get("https://api.crossref.org/works/" + doi)["message"], "Foundational")
        time.sleep(1)
    cry = get("https://api.crossref.org/journals/0161-1194/works?" + urllib.parse.urlencode({"rows": 400, "sort": "is-referenced-by-count", "order": "desc"}))["message"]["items"]
    for it in cry:
        total += store(db, it, "Journal: Cryptologia")
    time.sleep(1)
    for topic, qs in QUERIES.items():
        for q in qs:
            items = get("https://api.crossref.org/works?" + urllib.parse.urlencode({"query.bibliographic": q, "rows": 40, "select": "DOI,title,author,published-print,published-online,published,issued,container-title,type,is-referenced-by-count"}))["message"]["items"]
            for it in items:
                total += store(db, it, topic)
            print(topic[:20], q[:32], total, flush=True)
            time.sleep(1.2)
    print("publications", db.execute("SELECT count(*) FROM publications").fetchone()[0])


if __name__ == "__main__":
    main()
