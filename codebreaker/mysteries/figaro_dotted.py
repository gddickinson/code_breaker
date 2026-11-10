"""Round 67: the dotted number lists once grouped with table 2402 (1875-1889), against fixed numeric systems.

Systems: the 11 documented numeric tables, the alphabet numbered from 1 with every shift (A=1+k), and the reversed
alphabet with every shift. Each list is decoded under every system and scored by French word coverage (the dashes of
the 1877 ad are kept as word breaks); the best system is compared with shuffled copies of the list that also take
their best system (2,000 shuffles), with Bonferroni over the lists. Lists too short for the test are reported as such."""
import json
import random
import re

from ..languages import ROOT
from ..validation import coverage
from .figaro_digit_sweep import numeric_tables

RESULT = ROOT / "data/results/figaro_dotted.json"
A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LISTS = {
    "1877_18770412-OPQ.jpg": "20.7.3.5.2.1 - 15.2.14.20.2 - 3.2.8.6.3.7.1.2.24 - 20.7.14 - 12.7.14.8 - 7.9 - 20.7.3.2",
    "1879_18790222.jpg": "8.11.44.6.9.8.728.432.219.18.19.1.40",
    "1882_18821010-LINETTE.jpg": "19.3.2.16.6.2.23.4.3.14.2.17.2.5.19.18.6.2.7.9.1.10.19.3.16",
    "1883_18830427-pella.jpg": "3.103.20.7.14.14.7.27.28.7.14.20",
    "1889_18890510-AVRIL.jpg": "10.20.19.18.20",
}
MIN_NUMBERS = 10


def systems() -> list[tuple[str, dict]]:
    out = [(f"table {t['id']}", t["key"]) for t in numeric_tables()]
    for k in range(26):
        out.append((f"alphabet shift {k}", {str(i + 1): A[(i + k) % 26] for i in range(26)}))
        out.append((f"reversed alphabet shift {k}", {str(i + 1): A[(25 - i + k) % 26] for i in range(26)}))
    return out


def words(text: str) -> list[list[str]]:
    return [re.findall(r"\d+", w) for w in text.split(" - ")]


def decode(ws: list[list[str]], key: dict) -> str:
    return " ".join("".join(key.get(n, "?") for n in w) for w in ws)


def best(ws, systems_) -> tuple[float, str, str]:
    top = (-1.0, "", "")
    for name, key in systems_:
        d = decode(ws, key)
        if d.count("?") > 0.2 * len(d.replace(" ", "")):
            continue
        c = coverage(d.replace(" ", "").replace("?", ""), "fr")
        if c > top[0]:
            top = (c, name, d)
    return top


def run(trials: int = 2000, seed: int = 67) -> dict:
    sys_, rnd, rows = systems(), random.Random(seed), []
    for img, text in LISTS.items():
        ws = words(text)
        n = sum(map(len, ws))
        if n < MIN_NUMBERS:
            rows.append({"image": img, "numbers": n, "too_short": True})
            continue
        cov, name, reading = best(ws, sys_)
        null = []
        for _ in range(trials):
            flat = [x for w in ws for x in w]
            rnd.shuffle(flat)
            pos, sh = 0, []
            for w in ws:
                sh.append(flat[pos:pos + len(w)])
                pos += len(w)
            null.append(best(sh, sys_)[0])
        rows.append({"image": img, "numbers": n, "too_short": False, "system": name, "coverage": cov, "reading": reading,
                     "null_max": max(null), "p": (sum(x >= cov for x in null) + 1) / (trials + 1)})
    tested = [r for r in rows if not r["too_short"]]
    bar = 0.05 / max(len(tested), 1)
    for r in tested:
        r["passes"] = r["p"] <= bar
    return {"id": "figaro_dotted", "systems": len(sys_), "bar": bar, "rows": rows, "passed": [r["image"] for r in tested if r["passes"]]}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for r in res["rows"]:
        print(r)
