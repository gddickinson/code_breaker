"""Round 91: agreement marking and its calibration (no vision model needed)."""
from codebreaker.mysteries import figaro_second_reader as R


def test_disputed_characters_are_bracketed():
    assert R.marked("CH - xgrdmkcl", "H. xgrdnkcl") == "[c]hxgrd[m]kcl"
    assert R.agreement("abc", "abc") == [True, True, True]


def test_calibration_counts_inside_the_transcribed_stretch_only():
    c = R.calibrate("xgrdmkcl", "Suis triste. xgrdmkcl", "Suis triste. xgrdnkcl")
    assert c == {"agreed_right": 7, "agreed_wrong": 0, "disputed_right": 1, "disputed_wrong": 0}
    c = R.calibrate("xgrdmkcl", "xgrdmkcz", "xgrdmkcl")
    assert c["disputed_wrong"] == 1 and c["agreed_right"] == 7
