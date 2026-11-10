"""Round 39: two-letter symbols in the V. T. A. key."""
import json

from codebreaker.mysteries import figaro_vta as V
from codebreaker.mysteries import figaro_vta_pairs as P


def test_neighbours_in_merged_alphabet():
    assert P.neighbours("a") == ["b"] and P.neighbours("i") == ["h", "k"] and P.neighbours("u") == ["t", "w"]


def test_second_value_only_helps_when_it_makes_words():
    saved = V.SCORING
    try:
        V.SCORING = "segmented"
        key = {"a": "w", "b": "e", "c": "l"}
        assert P.best_cover("abcc", key, {}) == 4
        assert P.best_cover("abcc", {"a": "x", "b": "e", "c": "l"}, {"a": "w"}) == 4
        assert P.best_cover("abcc", {"a": "x", "b": "e", "c": "l"}, {}) < 4
    finally:
        V.SCORING = saved


def test_recorded_result_shows_no_neighbour_advantage():
    r = json.loads(P.RESULT.read_text())
    assert r["neighbour_share"] > r["baseline_share"]  # freedom helps...
    assert r["p_value"] > 0.05 and r["neighbour_share"] <= r["random_share_max"]  # ...but neighbours are not special
