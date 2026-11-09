"""AIM dictionary code: helpers, recorded references and the control result."""
import json

from codebreaker.languages import ROOT
from codebreaker.mysteries import aim_dictionary as D


def test_plain_strips_accents():
    assert D.plain("Dépêche") == "depeche"


def test_columns_split_by_position_and_skip_header():
    leaf = [[100, 10, "DEM — 163"], [100, 100, "Demi, a."], [900, 100, "Gelee, sf."], [100, 150, "suite minuscule"]]
    c = D.columns(leaf)
    assert c["L"] == ["Demi"] and c["R"] == ["Gelee"]


def test_near_uses_tolerance_and_exact_short_words():
    cols = {"L": ["Bidon", "Bief", "Bien", "Bielle"], "R": []}
    assert D.near(cols, "L", 2, "bien", 1)
    assert not D.near(cols, "L", 1, "bien", 0)
    assert not D.near({"L": ["Jeune"]}, "L", 1, "je", 1)


def test_references_are_recorded_with_a_source():
    d = json.loads(D.CONTROL.read_text())
    assert "solved AIM scans" in d["source"] and len(d["pairs"]) == 27
    assert set(d["unsolved"]) == {"1882_18820120-AIM.jpg", "1882_18820216-AIM.jpg"}


def test_recorded_control_beats_random_locations():
    c = json.loads((ROOT / "data/results/aim_dictionary.json").read_text())["control"]
    assert c["hits"] >= 0.7 * c["pairs"] and c["null_max"] <= 3
