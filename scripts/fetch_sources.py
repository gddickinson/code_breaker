"""Download the third-party data the code reads but the public repository does not redistribute (THIRD_PARTY.md).

  data/sources/figaro/codes.html       Didier Müller's table of cipher systems from the Le Figaro ads database
  data/sources/figaro/ads.json         his database of ads, indexed year by year (scripts/figaro_harvest.py)
  data/sources/research/schmeh50.html  Klaus Schmeh's list of the top 50 unsolved encrypted messages

Requests are spaced out and identify the client generically. Files already present are kept unless --force.
Usage: python scripts/fetch_sources.py [--force]"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "codebreaker-research/0.1"
FIGARO = "https://www.apprendre-en-ligne.net/crypto/Figaro/"
FILES = {ROOT / "data/sources/figaro/codes.html": FIGARO + "codes.php",
         ROOT / "data/sources/research/schmeh50.html": "https://scienceblogs.de/klausis-krypto-kolumne/the-top-50-unsolved-encrypted-messages/"}


def fetch(dest: Path, url: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sS", "-L", "-m", "150", "-A", UA, "-o", str(dest), url], check=True)
    print(f"{dest.relative_to(ROOT)}: {dest.stat().st_size:,} bytes from {url}", flush=True)
    time.sleep(3)


if __name__ == "__main__":
    force = "--force" in sys.argv
    for dest, url in FILES.items():
        if force or not dest.exists():
            fetch(dest, url)
        else:
            print(f"{dest.relative_to(ROOT)}: present", flush=True)
    ads = ROOT / "data/sources/figaro/ads.json"
    if force or not ads.exists():
        sys.path.insert(0, str(ROOT / "scripts"))
        import figaro_harvest

        print(f"indexing the ads database year by year ({FIGARO}annonces.php), about 2 minutes", flush=True)
        print(f"{len(figaro_harvest.index())} ads written to {ads.relative_to(ROOT)}")
    else:
        print(f"{ads.relative_to(ROOT)}: present")
