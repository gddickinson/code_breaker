"""Case-file text for the Mystery Lab, built from saved results in data/results/."""
import json

from ..languages import ROOT
from .casefile_extra import dorabella_sections, scriptlab_sections, solvability_sections, sweep_sections, zodiac_sections
from .casefile_sections import beale_sections, dagapeyeff_sections, kryptos_sections, tamam_sections, voynich_sections

RESULTS = ROOT / "data/results"

CASES = {
    "beale": {"title": "The Beale Ciphers", "status": "1 of 3 solved", "status_kind": "open", "tagline": "Three number ciphers said to locate buried treasure in Virginia. The second opens with the Declaration of Independence. The others never have.",
              "build": beale_sections, "sources": [("The Beale Papers, 1885 pamphlet (Wikisource)", "https://en.wikisource.org/wiki/The_Beale_Papers"), ("Declaration of Independence (Project Gutenberg)", "https://www.gutenberg.org/ebooks/1"), ("IACR ePrint 2024/695, on whether B1 and B3 are intelligible", "https://eprint.iacr.org/2024/695")]},
    "dagapeyeff": {"title": "D'Agapeyeff Cipher", "status": "Open", "status_kind": "open", "tagline": "A challenge printed in a 1939 textbook. Later editions dropped it, and the author is reported to have forgotten how he made it.",
                   "build": dagapeyeff_sections, "sources": [("D'Agapeyeff cipher (Wikipedia)", "https://en.wikipedia.org/wiki/D%27Agapeyeff_cipher")]},
    "tamam": {"title": "Tamam Shud Code", "status": "Open", "status_kind": "open", "tagline": "Five pencilled lines in a copy of the Rubaiyat, linked to the Somerton Man found on an Adelaide beach in 1948.",
              "build": tamam_sections, "sources": [("Somerton Man (Wikipedia)", "https://en.wikipedia.org/wiki/Somerton_Man"), ("University of Adelaide cipher-cracking project, 2013", "https://www.eleceng.adelaide.edu.au/personal/dabbott/wiki/index.php/Semester_B_Final_Report_2013_-_Cipher_cracking"), ("The Rubaiyat of Omar Khayyam (Project Gutenberg)", "https://www.gutenberg.org/ebooks/246")]},
    "kryptos": {"title": "Kryptos", "status": "K4 solved privately", "status_kind": "private", "tagline": "Jim Sanborn's sculpture at CIA headquarters. Three sections are public. The answer to the fourth was sold at auction.",
                "build": kryptos_sections, "sources": [("Kryptos (Wikipedia)", "https://en.wikipedia.org/wiki/Kryptos"), ("RR Auction on K4", "https://content.rrauction.com/kryptos-k4-discovered-not-solved-heres-what-actually-happened/")]},
    "voynich": {"title": "Voynich Manuscript", "status": "Statistical study", "status_kind": "untestable", "tagline": "A 15th-century illustrated book in an unknown script. It may be a cipher, a lost language, or meaningless. We measure what kind of object it is.",
                "build": voynich_sections, "sources": [("Zandbergen-Landini EVA transliteration ZL3b", "https://voynich.nu/data/ZL3b-n.txt"), ("voynich.nu transliteration archive", "https://voynich.nu/extra/legacy.html")]},
    "dorabella": {"title": "Dorabella Cipher", "status": "Open", "status_kind": "open", "tagline": "Elgar's 1897 note of 87 looping symbols, now attacked across three independent transcriptions.", "build": dorabella_sections,
                  "sources": [("Dorabella cipher (Wikipedia)", "https://en.wikipedia.org/wiki/Dorabella_Cipher"), ("Hauer et al., HistoCrypt", "https://ecp.ep.liu.se/index.php/histocrypt/article/download/159/115"), ("AZdecrypt collection", "https://github.com/doranchak/azdecrypt")]},
    "zodiac": {"title": "Zodiac Ciphers", "status": "Z13, Z32 open", "status_kind": "open", "tagline": "Z408 and Z340 are solved and serve as benchmarks. Z13 and Z32 are too short for any claim to be proved.", "build": zodiac_sections, "sources": [("AZdecrypt Zodiac ciphers, David Oranchak", "https://github.com/doranchak/azdecrypt")]},
    "sweep": {"title": "The Unsolved Sweep", "status": "36 cryptograms", "status_kind": "open", "tagline": "Murder notes, spy messages, challenge ciphers and altar inscriptions, all tested the same way.", "build": sweep_sections, "sources": [("AZdecrypt Unsolved collection", "https://github.com/doranchak/azdecrypt/tree/master/AZdecrypt/Ciphers/Unsolved"), ("Klaus Schmeh's Top 50", "https://scienceblogs.de/klausis-krypto-kolumne/the-top-50-unsolved-encrypted-messages/")]},
    "scriptlab": {"title": "Lost Scripts Lab", "status": "Statistical study", "status_kind": "untestable", "tagline": "Phaistos Disc, Linear A and Liber Primus, measured beside six known languages.", "build": scriptlab_sections, "sources": [("Phaistos Disc (Wikipedia)", "https://en.wikipedia.org/wiki/Phaistos_Disc"), ("Linear A inscriptions, lineara.xyz", "https://github.com/mwenge/lineara.xyz"), ("Liber Primus transcription", "https://github.com/henkman/liberprimus")]},
    "solvability": {"title": "Solvability Map", "status": "Calibration", "status_kind": "solved", "tagline": "How long does a message have to be before a homophonic cipher breaks? Measured, not assumed.", "build": solvability_sections, "sources": [("Project corpora", "https://www.gutenberg.org/")]},
}


def _load(mid: str):
    path = RESULTS / f"{mid}.json"
    return json.loads(path.read_text()) if path.exists() else None


def index() -> list[dict]:
    return [{"id": k, "title": v["title"], "status": v["status"], "status_kind": v["status_kind"], "tagline": v["tagline"]} for k, v in CASES.items()]


def case(mid: str) -> dict | None:
    meta = CASES.get(mid)
    if meta is None:
        return None
    result = _load(mid)
    if meta["build"] is None:
        sections = [{"heading": "Why there is no attempt yet", "paragraphs": ["The symbols are curves in eight orientations, and scholars disagree about several of them. Published statistics exist, but we found no complete transcription we could verify. Typing one from memory or guessing from an image would make every result meaningless.", "To run this case, transcribe the 87 symbols from a scan as orientation numbers. The homophonic and substitution solvers and the control tests already apply. At 87 symbols, expect the answer to be limited by the length of the text."]}]
    elif result is None:
        sections = [{"heading": "Not run yet", "paragraphs": ["Run scripts/run_mysteries.py to generate this case file."]}]
    else:
        sections = meta["build"](result)
    return {"id": mid, "title": meta["title"], "status": meta["status"], "status_kind": meta["status_kind"], "tagline": meta["tagline"], "sections": sections, "sources": [list(s) for s in meta["sources"]]}
