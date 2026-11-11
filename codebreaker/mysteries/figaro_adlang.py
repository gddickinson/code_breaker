"""French as the Le Figaro personal-column writers wrote it (Round 87), as a cipher language ("frad").

The Round 87 benchmark showed that the solved ads' plaintexts score 2 to 16 standard deviations below French novels:
they are telegraphic ("t aime", "pr", "qd"), so a model trained on novels does not recognise them. This builds a
corpus from Didier Muller's solved ads instead: the text that was actually enciphered (his bracketed expansions,
initials and comments removed, word breaks kept), one ad a line, written to data/corpora/extra/frad.txt (not
committed: the ads database is third-party data, fetched by scripts/fetch_sources.py). The 70 benchmark ads are left
out, so the benchmark measures the model on ads it has not seen.
Usage: PYTHONPATH=. python -m codebreaker.mysteries.figaro_adlang"""
import json
import re

from ..languages import CORPORA
from ..third_party import need
from .realbench import ADS, _signature

OUT = CORPORA / "extra/frad.txt"


def enciphered_words(text: str, sig: str) -> str:
    t = re.sub(r"\[[^\]]*\]", "", text)
    t = re.split(r"\(\w{1,5}\)", t)[0]
    head = t.split(" - ", 1)
    if len(head) == 2 and len(head[0]) < 30 and head[0].strip().lower().startswith(sig.lower()[:2]):
        t = head[1]
    return " ".join(re.findall(r"[^\W\d_]+", t))


def build(exclude: set[str]) -> dict:
    ads = [a for a in json.loads(need(ADS).read_text()) if a["solved"] and a["text"] and a["image"] not in exclude]
    lines = [w for w in (enciphered_words(a["text"], _signature(a["image"])) for a in ads) if len(w) >= 10]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ads": len(lines), "characters": sum(map(len, lines)), "excluded": len(exclude)}


if __name__ == "__main__":
    from .realbench import tier2

    print(build({x["name"] for x in tier2()}))
