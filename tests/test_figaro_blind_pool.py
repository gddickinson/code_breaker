"""Round 53: the blind pooled screen over letter-digit signatures."""
from codebreaker.mysteries import figaro_blind_pool as B


def test_pools_leave_out_known_families():
    p = B.pools()
    known = B.family_members()
    for sig, ads in p.items():
        assert not any(x in sig for x in B.EXCLUDE)
        assert all(img not in known for img, _ in ads)
        assert sum(len(s) for _, s in ads) >= B.MIN_SYMBOLS


def test_pooled_text_is_digit_tokens_only():
    p = B.pools()
    for ads in p.values():
        for _, s in ads:
            assert s.isalnum() and any(c.isdigit() for c in s)


def test_recorded_screen_controls_work_and_nothing_passes_from_ocr():
    import json

    r = json.loads(B.RESULT.read_text())
    assert r["signatures"] >= 10 and all(x["planted_accuracy"] > 0.9 for x in r["rows"])
    assert r["passed"] == [] and all(x["coverage"] < 0.3 for x in r["rows"])
