"""Round 38: the blind solve and the audit of unexplained words."""
from codebreaker.mysteries import figaro_vta as V
from codebreaker.mysteries import figaro_vta_blind as B


def test_agreement_counts_symbol_uses():
    truth = {"a": "x", "b": "y"}
    assert B.agreement({"a": "x", "b": "z"}, truth, ["aab"]) == 2 / 3


def test_shuffle_keeps_word_lengths_and_symbols():
    w = B.pooled_words()
    s = B.shuffled(w)
    assert [len(x) for x in s] == [len(x) for x in w] and sorted("".join(s)) == sorted("".join(w))


def test_planted_matches_shape():
    pw, truth = B.planted()
    assert len(pw) > 150 and len(set(truth.values())) >= 20


def test_saved_blind_result_beats_its_controls():
    import json

    r = json.loads(B.RESULT.read_text())
    assert r["best"]["agreement"] >= 0.7 and r["shuffled_null"]["agreement_with_context_key"] < 0.3
    assert r["planted"]["agreement_with_true_key"] >= 0.9
    assert r["best"]["score"] > r["shuffled_null"]["best_score"] + 0.2
    assert r["runs"][0]["seed"] == r["best"]["seed"]  # the best-scoring run, chosen blind


def test_unexplained_audit_lists_names():
    u = V.unexplained()
    assert any(x["name"] for x in u) and all(x["covered"] < len(x["decoded"]) for x in u)
    assert len(u) < 0.4 * sum(len(V.words_of(a["cipher"])) for a in V.ads().values())
