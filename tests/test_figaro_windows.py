"""Round 46: date windows for the two correspondences, and the letter-digit family."""
import json
from collections import Counter

from codebreaker.mysteries import figaro_windows as W
from codebreaker.mysteries.figaro_keys import OUT


def test_window_bounds():
    assert W.in_window("1882_18820601-5.jpg", "18810601", "18830630") and not W.in_window("1884_18840101.jpg", "18810601", "18830630")


def test_berthe_window_finds_exactly_the_known_five():
    r = json.loads(W.RESULT.read_text())["berthe"]
    assert set(r["passed"]) == {"1881_18811012.jpg", "1881_18811119-ZZ.jpg", "1882_18820601-5.jpg", "1882_18820701-5.jpg", "1882_18821224-5.jpg"}


def test_letter_digit_family_shares_tokens_across_signatures():
    d = json.loads((OUT / "letter_digit_family.json").read_text())["ads"]
    for image in d:
        assert (OUT / "images" / image).exists()
    sigs = {}
    for image, text in d.items():
        for w in set(text.split()):
            sigs.setdefault(w, set()).add(image.split("-", 1)[1])
    shared = {w for w, s in sigs.items() if len(s) >= 2}
    assert {"fr5", "grp", "26886", "173d"} <= shared
