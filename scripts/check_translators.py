"""Round 85: does every installed translator into English work? For each, a held-out passage of that language
(the test part of data/sources/langid) is translated; recorded: whether it ran, the time, and whether the output is
identified as English (langid, p >= 0.8). Results in data/results/translators_check.json."""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/results/translators_check.json"

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT))
    from codebreaker import langid
    from codebreaker.translate import available, translate

    rows = {}
    for code in available():
        f = langid.SRC / f"{'zh' if code == 'zt' else code}.txt"
        if not f.exists():
            rows[code] = {"tested": False, "why": "no sample text"}
            continue
        _, test = langid.split(f.stem)
        passage = next((a for a in test if 80 <= len(a) <= 400), test[0][:300])
        t = time.time()
        try:
            r = translate(passage, code)
            out = r.get("translation") or ""
            g = langid.detect(out, 1) if out else []
            rows[code] = {"tested": True, "ran": bool(out), "seconds": round(time.time() - t, 1), "english": bool(g and g[0]["lang"] == "en" and g[0]["p"] >= 0.8),
                          "note": r.get("note", "")[:120], "input": passage[:120], "output": out[:160]}
        except Exception as exc:
            rows[code] = {"tested": True, "ran": False, "error": str(exc)[:160]}
        print(code, rows[code].get("ran"), rows[code].get("english"), rows[code].get("output", rows[code].get("error", ""))[:70], flush=True)
    ok = [c for c, r in rows.items() if r.get("english")]
    OUT.write_text(json.dumps({"id": "translators_check", "date": time.strftime("%Y-%m-%d"), "installed": len(rows), "working": ok, "rows": rows},
                              indent=1, ensure_ascii=False))
    print(len(ok), "of", len(rows), "give English")
