"""Round 85b: public-domain books from Project Gutenberg as corpora for the extra cipher languages.

For each language, single-language text books from the Gutenberg catalogue (data/models/gutenberg/pg_catalog.csv,
downloaded from gutenberg.org) are fetched in catalogue order, two seconds apart, until about TARGET characters of text
(Gutenberg header and licence removed later by languages.corpus_text) are collected. Files go to data/corpora/extra
(not committed); the book numbers used are recorded in data/sources/corpora_extra.json so the corpora can be rebuilt.
Usage: python scripts/fetch_corpora.py [codes...]"""
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT, CAT, REC = ROOT / "data/corpora/extra", ROOT / "data/models/gutenberg/pg_catalog.csv", ROOT / "data/sources/corpora_extra.json"
UA = {"User-Agent": "code-breaker-research/1.0 (local study tool)"}
LANGS = ["nl", "pt", "sv", "da", "no", "fi", "hu", "pl", "cs", "eo", "ca", "tl"]
TARGET = 1_500_000

if __name__ == "__main__":
    codes = sys.argv[1:] or LANGS
    books = [r for r in csv.DictReader(open(CAT, encoding="utf-8")) if r["Type"] == "Text"]
    rec = json.loads(REC.read_text()) if REC.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    for code in codes:
        dest = OUT / f"{code}.txt"
        if dest.exists() and code in rec:
            print(code, "present")
            continue
        parts, ids, size = [], [], 0
        for b in (r for r in books if r["Language"] == code):
            url = f"https://www.gutenberg.org/cache/epub/{b['Text#']}/pg{b['Text#']}.txt"
            try:
                t = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "ignore")
            except Exception as exc:
                print(code, b["Text#"], "skipped:", exc)
                time.sleep(2)
                continue
            parts.append(t)
            ids.append({"id": b["Text#"], "title": b["Title"][:80]})
            size += len(t)
            time.sleep(2)
            if size >= TARGET or len(ids) >= 12:
                break
        dest.write_text("\n".join(parts))
        rec[code] = {"books": ids, "characters": size, "source": "https://www.gutenberg.org", "licence": "public domain in the USA (Project Gutenberg licence for the files)",
                     "fetched": time.strftime("%Y-%m-%d")}
        REC.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        print(code, len(ids), "books", size, "characters", flush=True)
