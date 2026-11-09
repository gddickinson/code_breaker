"""Recovery page: measured results exist, the hand readings decrypt, and repair works."""
import json

from codebreaker.languages import ROOT
from codebreaker.mysteries import figaro_keys as F
from codebreaker.mysteries import recovery as R, recovery_images as I
from codebreaker.text import A, letters

import numpy as np

HAND = R.hand_truth()


def test_hand_transcriptions_decrypt_to_recorded_readings():
    t25 = letters(HAND["1894_18940920-25.jpg"]["ciphertext"])
    assert F.vig(t25, "CD", F.NOW) == letters("Espere diner avec toi ou serai tres peinee")
    t78 = letters(HAND["1884_18841113-78.jpg"]["ciphertext"])
    assert F.shift(t78, 2, A) == letters("Je t'adore. Te voir est mon seul bonheur")
    table = next(x for x in F.load_tables() if x["id"] == "2217")["map"]
    t5 = letters(HAND["1882_18820701-5.jpg"]["ciphertext"])
    assert "".join(table[c] for c in t5) == letters("aime moi un peu je t aime et desire tant te baiser")


def test_recovered_measures_characters():
    assert R.recovered("abcd", "ab cd") == 1
    assert R.recovered("abcd", "ab") == 0.5


def test_key_aware_repair_fixes_the_1894_ad():
    r = R.repair_real()
    assert r["plain"] == letters("Espere diner avec toi ou serai tres peinee")
    assert len(r["edits"]) == 2


def test_dropped_letters_hurt_a_repeating_key_most():
    s = R.error_spread(n=10, length=200)["series"]
    assert s["Vigenere, deletion"][3] < s["Vigenere, misread"][3]
    assert s["Vigenere, deletion"][3] < s["Caesar, deletion"][3]


def test_skew_angle_found():
    img = I.render("abcdefg hijkl mnopqr stuvw")
    rng = np.random.default_rng(1)
    assert abs(I.skew_angle(I.degrade(img, rng, 3.0)) + 3.0) <= 0.75


def test_page_results_are_complete():
    d = json.loads((I.STATIC / "results.json").read_text())
    assert d["ocr"]["ads"] == len(HAND) and len(d["ocr"]["table"]) == 15
    assert len(d["reconstruction"]["stages"]) == len(I.STAGES)
    for f in ("ad25_scan.png", "adn_otsu.png", "stage0.png", "stage6.png"):
        assert (I.STATIC / f).exists()
    assert "recovery.js" in (ROOT / "codebreaker/web/static/index.html").read_text()
