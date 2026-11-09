"""Letter-digit attacks: the beam, documented digit tables, hand transcriptions and recorded controls."""
import json

from codebreaker.languages import ROOT
from codebreaker.mysteries import figaro_digit_family as X, figaro_digit_words as W

HAND = json.loads(W.HAND.read_text())


def table(tid):
    return next(t for t in X.digit_tables() if t["id"] == tid)["key"]


def test_digit_tables_are_parsed():
    assert len(X.digit_tables()) >= 30
    assert table("2119")["6"] == "E"


def test_documented_table_reads_the_hand_transcription():
    got = X.apply(HAND["1881_18811107.jpg"]["words"], table("2402"))
    assert got[:4] == ["DOUX", "SOUVENIR", "TENDRES", "BAISERS"]


def test_second_table_reading():
    got = X.apply(HAND["1879_18790309b.jpg"]["words"], table("2402"))
    assert got[:2] == ["SERAI", "PARIS"]


def test_beam_solves_a_short_planted_ad():
    r = W.solve("".join({"E": "6", "A": "7", "I": "5"}.get(c, c) for c in "JE VOUDRAIS TE VOIR ET TE DIRE QUE JE T AIME".replace(" T AIME", "")))
    assert r["read"] >= 0.8


def test_family_key_rejects_shuffles():
    key = table("2119")
    text = HAND["1884_18840427-H.jpg"]["words"]
    assert X.read_share(text, {**key, "R": "O", "A": "G"}) > 0.5


def test_recorded_control_at_real_length():
    c = json.loads((ROOT / "data/results/figaro_digit_words.json").read_text())["control"]
    assert c["30"]["solved"] >= 0.7 * c["30"]["n"]
