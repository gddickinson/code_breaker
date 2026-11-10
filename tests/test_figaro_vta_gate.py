"""Round 37: segmented word gate and glyph robustness for the V. T. A. key."""
from codebreaker.mysteries import figaro_vta as V
from codebreaker.mysteries import figaro_vta_gate as G


def test_segmented_covers_run_together_words_only_with_long_parts():
    saved = V.SCORING
    try:
        V.SCORING = "segmented"
        assert V.covered("bienaimee") == 9  # the vocabulary writes v as u, like the writer's alphabet
        assert V.covered("loueyou") == 7
        assert V.covered("xqzv") == 0
        V.SCORING = "exact"
        assert V.covered("loueyou") == 0 and V.covered("loue") == 4
    finally:
        V.SCORING = saved


def test_names_are_not_scored():
    ad = V.ads()["1877_18771009-VTA.jpg"]
    assert "v8td427" not in V.scored_words(ad) and "fst28" in V.scored_words(ad)


def test_result_does_not_hang_on_uncertain_glyphs():
    base = G.evaluate(scoring="segmented", trials=50)["pooled_share"]
    flipped = G.evaluate(*G.with_flips(G.FLIPS), scoring="segmented", trials=50)
    assert abs(flipped["pooled_share"] - base) < 0.03
    assert flipped["crib_letters_right"] / flipped["crib_letters"] > 0.95
    for f in G.FLIPS[:3]:
        assert abs(G.evaluate(*G.with_flips([f]), scoring="segmented", trials=20)["pooled_share"] - base) < 0.02


def test_segmented_real_far_above_scrambled_control():
    saved = V.SCORING
    try:
        V.SCORING = "segmented"
        assert V.held_out(trials=100)["pooled_share"] > 2 * V.scrambled_control()["pooled_share"]
    finally:
        V.SCORING = saved
