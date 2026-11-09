"""Numbers mixed with clear letters: parsing, null design, controls and hand-read ads."""
import json
import random

from codebreaker.languages import ROOT
from codebreaker.mysteries import figaro_digit_family as X, figaro_numeric_mixed as M
from codebreaker.mysteries.figaro_digit_sweep import numeric_tables
from codebreaker.mysteries.figaro_digit_words import HAND

H = json.loads(HAND.read_text())


def table(tid):
    return next(t for t in numeric_tables() if t["id"] == tid)["key"]


def test_decode_keeps_clear_letters_between_numbers():
    assert M.decode(M.pieces(["5.16m16", "a12"]), {"5": "S", "16": "E", "12": "B"}) == "SEMEAB"


def test_shuffle_moves_numbers_and_leaves_letters():
    ps = M.pieces(["1a2b3c4d"])
    out = M.shuffle_numbers(ps, random.Random(1))
    assert [p for p in out if p.isalpha()] == ["a", "b", "c", "d"]
    assert sorted(p for p in out if p.isdigit()) == ["1", "2", "3", "4"]


def test_second_chery_ad_reads_under_its_table():
    got = M.decode(M.pieces([H["1889_18891108-CHERY.jpg"]["numbers"]]), table("2310"))
    assert got.startswith("ADORENEDOUTEPASDEMOI") and "DAVANTAGE" in got and "RETROVERAS" in got


def test_letter_digit_transcriptions():
    key = next(t for t in X.digit_tables() if t["id"] == "2402")["key"]
    assert X.apply(H["1886_18860307-2F.jpg"]["words"], key)[:5] == ["MMARDON", "DE", "TOUT", "MON", "COEUR"]
    assert X.apply(H["1879_18790410.jpg"]["words"], key)[2:4] == ["MON", "COEUR"]


def test_recorded_control():
    c = json.loads((ROOT / "data/results/figaro_numeric_mixed.json").read_text())["control"]
    assert c["detected"] >= 0.7 * c["planted"] and c["false_on_junk"] <= 2
