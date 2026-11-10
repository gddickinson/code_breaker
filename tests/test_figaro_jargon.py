"""Round 60: the '38' codebook and the 1896 'V' jargon."""
import json

from codebreaker.mysteries import figaro_jargon as J


def test_pattern_matches_stem_consonant_vowel():
    assert J.PATTERN.match("larzo") and J.PATTERN.match("frata") and J.PATTERN.match("milo")
    assert not J.PATTERN.match("lazro") and not J.PATTERN.match("bonjour")


def test_recorded_results():
    r = json.loads(J.RESULT.read_text())
    assert r["codebook_38"]["max"] == 36427 and r["codebook_38"]["p"] > 0.05
    v = r["v_1896"]
    assert v["pattern_share"] > 3 * v["null_max"] and len(v["by_stem"]["dri"]) >= 10


def test_mutual_information_and_date_tests():
    assert J.mutual_information([("a", 1), ("b", 2)] * 5) > J.mutual_information([("a", 1), ("a", 2), ("b", 1), ("b", 2)] * 3)
    r = json.loads(J.RESULT.read_text())["v_dates"]
    assert r["tests"] and r["passed"] == [] and r["bar"] < 0.01
