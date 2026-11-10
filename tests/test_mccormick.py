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
