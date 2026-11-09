"""OCR fusion and the letter-digit solver: unit checks, integrity and recorded controls."""
import json
from collections import Counter

from codebreaker.languages import ROOT
from codebreaker.mysteries import figaro_digits as D, figaro_fusion as U, figaro_keys as F
from codebreaker.mysteries.recovery import hand_truth
from codebreaker.text import A, letters

HAND = hand_truth()


def test_slots_collect_votes_from_aligned_readings():
    s = U.slots(["BONJOUR", "BONIOUR", "BONJOUR"])
    assert s[3] == Counter({"J": 2, "I": 1})


def test_viterbi_uses_french_to_settle_a_tie():
    sl = [Counter({c: 1}) for c in "BONJOU"] + [Counter({"R": 1, "X": 1})]
    assert U.viterbi(sl, lambda i, c: c, U.bigrams())[1] == "BONJOUR"


def test_viterbi_keeps_key_position():
    plain = "CHERAMIE"
    keyed = [Counter({A[(A.index(c) + [1, 2][i % 2]) % 26]: 1}) for i, c in enumerate(plain)]
    assert U.viterbi(keyed, lambda i, c: A[(A.index(c) - [1, 2][i % 2]) % 26], U.bigrams())[1] == plain


def test_new_candidate_transcriptions_decrypt():
    t = letters(HAND["1894_18940911-25.jpg"]["ciphertext"])
    assert F.vig(t, "CD", F.NOW).startswith("TOUSBIEN")
    tab = next(x for x in F.TABLES if x["id"] == "2210")["map"]
    r = "".join(tab[c] for c in letters(HAND["1881_18811007.jpg"]["ciphertext"])[::-1])
    assert r.endswith("TAIMEMALADEDEPUISRIEN")


def test_digit_tokens_keep_cipher_and_skip_french():
    got = D.tokens("merci Rcog dc6h maison")
    assert "DC6H" in got and "MERCI" not in got


def test_digit_solver_recovers_planted_text():
    words = "J5 T41M3 D3 T0UT M0N C03UR J5 T3 D1S QU3 J3 P3NS3 4 T01 T0UJ0URS"
    p = D.solve(words)[3]
    assert sum(a == b for a, b in zip(p, letters("JETAIMEDETOUTMONCOEURJETEDISQUEJEPENSEATOITOUJOURS"))) >= 25


def test_recorded_controls():
    f = json.loads((ROOT / "data/results/figaro_fusion.json").read_text())
    assert f["control"]["hmm"] >= f["baseline_recovered"]
    d = json.loads((ROOT / "data/results/figaro_digits.json").read_text())
    assert d["control_solved"] >= 0.7 * d["control_n"]
