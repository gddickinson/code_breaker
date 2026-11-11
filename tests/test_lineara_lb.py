"""Round 80: Linear A read with Linear B values against a value-permutation null."""
import json
import random

from codebreaker.mysteries import lineara_lb as M


def test_inputs_and_permutation():
    w, lex = M.la_words(), M.lexicon()
    assert len(w) > 250 and len(lex) > 200
    p = M.permuted(w, random.Random(1))
    assert len(p) == len(w) and sorted(map(len, p)) == sorted(map(len, w))


def test_recorded_result_is_not_significant_and_has_power():
    r = json.loads(M.RESULT.read_text())
    assert r["p"] > 0.05 and ["su-ki-ri-ta", "𐀱𐀑𐀪𐀲"] in [list(x) for x in r["matched"]]
    assert r["power"]["0.02"]["detected_at_p05"] >= 0.9
