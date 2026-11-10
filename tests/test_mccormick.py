"""Round 64: letter-frequency models for Ricky McCormick's notes."""
import json

from codebreaker.mysteries import mccormick as M


def test_model_streams():
    w = ["hello", "world", "apple"]
    assert M.model_stream("vowel_dropped", w) == "hllwrldappl"
    assert M.model_stream("initials", w) == "hwa"


def test_kl_zero_for_same_distribution():
    p = M.freqs("abcabc")
    assert abs(M.kl(p, p)) < 1e-12 and M.kl(M.freqs("aaaa"), M.freqs("abcd")) > 0


def test_recorded_result():
    r = json.loads(M.RESULT.read_text())
    assert r["letters"] > 700 and r["not_rejected"] == []
    assert r["endings"]["se_share"] > 10 * r["endings"]["se_share_english"]


def test_stripped_markers_and_stems():
    full, stripped = M.mccormick_letters(), M.mccormick_letters(strip_markers=True)
    assert len(stripped) < len(full) and stripped.count("e") < full.count("e")
    r = json.loads(M.RESULT.read_text())
    assert r["stripped"]["not_rejected"] == []
    from codebreaker.mysteries import wordbreak_en as W

    s = json.loads(W.RESULT.read_text())["mccormick_stems"]
    assert s["gates"]["control"] and not s["gates"]["passed"]
