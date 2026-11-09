"""Irregular transposition helpers, recorded controls, and hand-read family ads."""
import json

from codebreaker.languages import ROOT
from codebreaker.mysteries import figaro_digit_family as X, figaro_table_cells as C, figaro_transposition as T
from codebreaker.mysteries.figaro_digit_words import HAND

H = json.loads(HAND.read_text())


def test_column_lengths_leave_a_short_last_row():
    assert T.column_lengths(11, 4) == [3, 3, 3, 2]


def test_undo_reverses_columnar_with_an_irregular_grid():
    plain = "RENDEZVOUSAMIDIPRECIS"
    for order in ((2, 0, 1), (3, 1, 0, 2), (4, 2, 0, 1, 3)):
        assert T.undo(T.redo(plain, order), order) == plain


def test_word_anagram_share_counts_scrambled_words():
    assert T.word_anagram_share(["OVUS", "MENIA"]) > 0.4


def test_number_share_excludes_mostly_plain_ads():
    assert C.number_share([["5", "16"], ["A", "B", "C", "D"]]) < 0.6


def test_recorded_columnar_control():
    r = json.loads((ROOT / "data/results/figaro_transposition.json").read_text())
    assert r["columnar_control"]["solved"] >= 0.7 * r["columnar_control"]["n"]


def test_family_hand_readings():
    key = {**next(t for t in X.digit_tables() if t["id"] == "2119")["key"], "R": "O"}
    assert X.apply(H["1884_18841221-S.jpg"]["words"], key)[:2] == ["MA", "CHERIE"]
    assert "RESTER" in X.apply(H["1883_18831226-J.jpg"]["words"], key)


def test_correspondence_slug_and_alternatives():
    from codebreaker.mysteries import figaro_correspondence as F

    assert F.slug("1879_18790309b.jpg") == "figaro-1879-03-09b"
    assert F.slug("1884_18840605-I.jpg") == "figaro-1884-06-05-i"
    assert F.read_alt([list("1ON")], {"O": "O", "N": "N", "1": "X"}, {"1": ["X", "B"]}) == 3


def test_correspondence_section_on_case_page():
    from codebreaker.mysteries.casefiles import case

    heads = [s["heading"] for s in case("figaro_keys")["sections"]]
    assert "Correspondence under table 2119" in heads


def test_quagmire_finds_a_long_alphabet_keyword():
    from codebreaker.ciphers import REGISTRY
    from codebreaker.ciphers.base import DEMO_PLAIN
    from codebreaker.text import letters, similarity

    c = REGISTRY["quagmire"]
    ct = c.encrypt(DEMO_PLAIN, alphabet="ENGAGEMENTS", key="GAINED")
    assert similarity(letters(c.decrypt(ct, alphabet="ENGAGEMENTS", key="GAINED")), letters(c.attack(ct, "en")["plaintext"])) > 0.95
