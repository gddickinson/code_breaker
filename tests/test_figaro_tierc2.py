import json

from codebreaker.mysteries import figaro_2119 as T
from codebreaker.mysteries import figaro_ch as CH
from codebreaker.mysteries import figaro_tierc2 as R


def test_sources_and_ve3_readings():
    src = R.sources()
    assert len(src["berthe"]) == 3 and len(src["vig"]) == 9 and len(src["short"]) == 4
    want = {"1889_18891101-VE3.jpg": "HUITQUATORZEVINGTDEUXPAS", "1890_18901026-VE3.jpg": "SUISENITALIEABSENTUNMOIS",
            "1891_18910611-VE3.jpg": "LUNDIPASAVANT", "1892_18920721-VE3.jpg": "JUSQUEVINGTHUIT", "1890_18900701-VE3.jpg": "QUATRE"}
    for img, plain in want.items():
        assert CH.decrypt(src["vig"][img][0], 0) == plain
    assert CH.search(src["vig"]["1891_18911226-VE3.jpg"][0])["plain"] == "SEPTSIXHEURES"


def test_ve3_kept_out_of_ch_series():
    d = json.loads((R.SRC / "ch_transcription.json").read_text())
    assert not any("VE3" in k for k in d["ads"]) and len(d["other_writers"]) == 6


def test_abbreviated_statistic_specific_and_control_readable():
    key, src = T.full_key(), R.sources()["short"]
    for t in src.values():
        assert R.abbrev_share(T.decode(t, key)) > 0.65
    plants = R.planted_short(key, n=3)
    assert all(R.abbrev_share(T.decode(p, key)) > 0.8 for p in plants)


def test_result_recorded():
    res = json.loads(R.RESULT.read_text())
    assert len(res["rows"]) == 17 and res["short_control"]["recovered"] == 12
    assert {"1890_18900701-VE3.jpg", "1891_18911226-VE3.jpg"}.isdisjoint(res["passed"]) and "V. E. 3 pooled (6 ads)" in res["passed"]
