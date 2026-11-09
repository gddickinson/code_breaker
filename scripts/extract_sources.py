"""Extract verified mystery ciphertexts from downloaded sources into data/mysteries/."""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "data/sources", ROOT / "data/mysteries"


def beale():
    raw = html.unescape(re.sub(r"<[^>]+>", " ", (SRC / "beale_try8").read_text(errors="ignore")))
    runs = re.findall(r"\d+(?:\s*,\s*\d+){100,}", raw)
    return [[int(n) for n in re.findall(r"\d+", r)] for r in runs]


def declaration_words():
    text = (SRC / "declaration.txt").read_text(errors="ignore")
    start = text.index("When in the Course of human events") if "When in the Course of human events" in text else text.lower().index("when in the course of human events")
    return text[start:], start


if __name__ == "__main__":
    runs = beale()
    for r in runs:
        print(len(r), r[:6], r[-4:], max(r))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "beale_raw.json").write_text(json.dumps(runs))
