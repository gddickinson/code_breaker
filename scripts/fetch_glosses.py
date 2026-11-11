"""Round 77: fetch Wiktionary lemma pages for the gloss word lists (permission given by the user, 2026-11-10).

For each language, every page in 'Category:<Language> lemmas' is fetched through the MediaWiki API in batches of 50
(one request per second), and only that language's section of the page is kept. Output: data/sources/glosses/<lang>.json
({title: section wikitext}) and sources.json (category, API, licence, date, page count). Licence: CC BY-SA 4.0."""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/sources/glosses"
API = "https://en.wiktionary.org/w/api.php"
UA = {"User-Agent": "code-breaker-research/1.0 (local study tool)"}
LANGS = {"egyptian": "Egyptian", "mycenaean": "Mycenaean Greek", "old_norse": "Old Norse"}


def get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    for attempt in range(8):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception:  # network hiccup: wait and retry
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def section(text: str, language: str) -> str:
    m = re.search(rf"^=={re.escape(language)}==\s*$(.*?)(?=^==[^=]|\Z)", text, flags=re.S | re.M)
    return m.group(1).strip() if m else ""


def fetch(key: str) -> int:
    language, pages, cont = LANGS[key], {}, {}
    while True:
        d = get({"action": "query", "generator": "categorymembers", "gcmtitle": f"Category:{language} lemmas", "gcmlimit": "50",
                 "gcmnamespace": "0", "prop": "revisions", "rvprop": "content", "rvslots": "main", **cont})
        for p in d.get("query", {}).get("pages", []):
            rev = (p.get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("content", "")
            sec = section(rev, language)
            if sec:
                pages[p["title"]] = sec
        print(key, len(pages), flush=True)
        if "continue" not in d:
            break
        cont = {k: v for k, v in d["continue"].items()}
        time.sleep(1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{key}.json").write_text(json.dumps(pages, ensure_ascii=False, indent=0))
    return len(pages)


if __name__ == "__main__":
    keys = sys.argv[1:] or list(LANGS)
    meta_path = OUT / "sources.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    for k in keys:
        n = fetch(k)
        meta[k] = {"category": f"Category:{LANGS[k]} lemmas", "api": API, "site": "https://en.wiktionary.org", "licence": "CC BY-SA 4.0",
                   "fetched": time.strftime("%Y-%m-%d"), "pages": n, "bytes": (OUT / f"{k}.json").stat().st_size}
        meta_path.write_text(json.dumps(meta, indent=1))
