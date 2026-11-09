"""Politely index the Le Figaro ads database by year, then fetch images of the unsolved ads."""
import json
import re
import subprocess
import sys
import time
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/sources/figaro"
IMG = OUT / "images"
BASE = "https://www.apprendre-en-ligne.net/crypto/Figaro/"
UA = "codebreaker-research/0.1"
RE = re.compile(r"<td width=25%><b>([^<]+)</B><BR><a href=([^ >]+) .*?</td><td width=40%>(.*?)</td></td><td width=35%>(.*?)</td>", re.S)


def index():
    ads = []
    for year in range(1875, 1901):
        path = OUT / f"y{year}.html"
        subprocess.run(["curl", "-sS", "-m", "150", "-A", UA, "-o", str(path), "-d", f"jour=0&mois=0&annee={year}&auteur=0&auteur2=0&systeme=0&break=1&unbreak=1&decrypt=1&table=1", BASE + "annonces.php"], check=False)
        t = path.read_text(encoding="latin-1", errors="ignore")
        n = 0
        for date, img, mid, note in RE.findall(t):
            ads.append({"date": date.strip(), "image": img, "solved": "mailto" not in mid, "text": re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", mid))).strip(), "note": re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", note))).strip()})
            n += 1
        print(year, n, flush=True)
        time.sleep(3)
    (OUT / "ads.json").write_text(json.dumps(ads, ensure_ascii=False, indent=0))
    return ads


def images(ads):
    IMG.mkdir(exist_ok=True)
    got = 0
    for a in ads:
        if a["solved"]:
            continue
        dest = IMG / a["image"].replace("/", "_")
        if dest.exists() and dest.stat().st_size > 400:
            continue
        subprocess.run(["curl", "-sS", "-m", "40", "-A", UA, "-o", str(dest), BASE + a["image"]], check=False)
        got += 1
        time.sleep(0.6)
    print("images", got, flush=True)


if __name__ == "__main__":
    ads = index()
    print(len(ads), sum(not a["solved"] for a in ads), flush=True)
    if "--images" in sys.argv:
        images(ads)
