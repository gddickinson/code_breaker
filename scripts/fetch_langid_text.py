"""Round 85: sample text for language identification, from each language's Wikipedia (CC BY-SA 4.0).

For every language with an installed translator (plus English and Latin), intros of random articles are fetched through
the MediaWiki API (20 per request, one request every two seconds) until about 40 kB of text is collected. Train and test
text come from different articles. Output: data/sources/langid/<code>.txt (one article per line) and sources.json."""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data/sources/langid"
UA = {"User-Agent": "code-breaker-research/1.0 (local study tool)"}
WIKI = {"pb": "pt", "zt": "zh", "nb": "no"}  # Argos codes whose Wikipedia has another code
TARGET = 40_000  # enough for character n-gram identification; Wikipedia throttled the larger fetch (Round 85)


def fetch(wiki: str) -> list[str]:
    arts, size, tries = [], 0, 0
    while size < TARGET and tries < 40:
        tries += 1
        url = f"https://{wiki}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "generator": "random", "grnnamespace": 0, "grnlimit": 20,
                                                                                     "prop": "extracts", "exintro": 1, "explaintext": 1, "exlimit": 20, "format": "json"})
        for a in range(6):
            try:
                d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
                break
            except Exception:
                time.sleep(10 * (a + 1))
        else:
            break
        for p in d.get("query", {}).get("pages", {}).values():
            t = re.sub(r"\s+", " ", p.get("extract", "")).strip()
            if len(t) >= 150:
                arts.append(t)
                size += len(t)
        time.sleep(2)
    return arts


if __name__ == "__main__":
    codes = sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    meta_path = OUT / "sources.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    for code in codes:
        if (OUT / f"{code}.txt").exists():
            continue
        wiki = WIKI.get(code, code)
        arts = fetch(wiki)
        (OUT / f"{code}.txt").write_text("\n".join(arts))
        meta[code] = {"wikipedia": f"https://{wiki}.wikipedia.org", "articles": len(arts), "characters": sum(map(len, arts)),
                      "licence": "CC BY-SA 4.0", "fetched": time.strftime("%Y-%m-%d"), "method": "random article intros via the MediaWiki API"}
        meta_path.write_text(json.dumps(meta, indent=1, ensure_ascii=False))
        print(code, len(arts), sum(map(len, arts)), flush=True)
