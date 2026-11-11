"""Round 86: Wikipedia article text as corpora for languages Project Gutenberg barely has (Ukrainian, Arabic, Persian,
Urdu; Hebrew if its Gutenberg books are too few).

Random main-namespace articles are fetched through the MediaWiki API as plain-text extracts (up to 1,200 characters
each, 20 articles a request, one second apart) until about TARGET characters are collected. Licence: CC BY-SA 4.0
(Wikipedia); the text is used to build letter statistics and is not redistributed: files go to data/corpora/extra
(not committed, as <code>_wiki.txt) and the fetch is recorded in data/sources/corpora_extra.json.
Usage: python scripts/fetch_wiki_corpora.py [codes...]"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT, REC = ROOT / "data/corpora/extra", ROOT / "data/sources/corpora_extra.json"
UA = {"User-Agent": "code-breaker-research/1.0 (local study tool)"}
LANGS = ["ru", "bg", "uk", "ar", "fa", "ur"]  # ru and bg add to their few Gutenberg books
TARGET = 1_500_000


def batch(code: str) -> list[str]:
    q = {"action": "query", "format": "json", "generator": "random", "grnnamespace": 0, "grnlimit": 20, "prop": "extracts",
         "explaintext": 1, "exchars": 1200, "exlimit": 20}
    url = f"https://{code}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(q)
    data = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
    return [p.get("extract", "") for p in data.get("query", {}).get("pages", {}).values()]


if __name__ == "__main__":
    rec = json.loads(REC.read_text()) if REC.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    for code in sys.argv[1:] or LANGS:
        dest, key = OUT / f"{code}_wiki.txt", f"{code}_wiki"
        if dest.exists() and key in rec:
            print(code, "present")
            continue
        parts, size, requests, wait, refused = [], 0, 0, 1.0, 0
        while size < TARGET and requests < 400:
            requests += 1
            try:
                got = [t for t in batch(code) if len(t) > 200]
                wait, refused = max(1.0, wait / 2), 0
            except Exception as exc:  # 429 and other refusals: back off, and give up after three in a row
                refused += 1
                wait = min(wait * 4, 300)
                print(code, "request refused:", exc, f"- waiting {wait:.0f} s", flush=True)
                if refused >= 3:
                    print(code, "stopped: the server keeps refusing; keeping what was collected")
                    break
                got = []
            parts += got
            size += sum(map(len, got))
            time.sleep(wait)
        dest.write_text("\n\n".join(parts))
        rec[key] = {"articles": len(parts), "characters": size, "requests": requests, "source": f"https://{code}.wikipedia.org (random articles, plain-text extracts)",
                     "licence": "CC BY-SA 4.0; not redistributed", "fetched": time.strftime("%Y-%m-%d")}
        REC.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        print(code, len(parts), "articles", size, "characters", flush=True)
