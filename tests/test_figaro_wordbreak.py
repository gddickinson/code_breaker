"""Round 57: word-break series from OCR through the matched refinement."""
import json

from codebreaker.mysteries import figaro_wordbreak as W


def test_candidates_exclude_known_families_and_led_ads():
    c = W.candidates()
    led = W.led_dates()
    for sig, ads in c.items():
        assert sig in W.SIGNATURES
        assert all(f"{i[5:9]}-{i[9:11]}-{i[11:13]}" not in led for i in ads)


def test_recorded_screen_has_working_controls_and_no_reading():
    r = json.loads(W.RESULT.read_text())
    assert r["series"] >= 10 and r["passed"] == []
    assert all(x["gates"]["control"] for x in r["rows"])
    assert all(x["coverage"] < 0.8 * x["planted_refined_coverage"] for x in r["rows"])
