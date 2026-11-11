"""Every cipher round-trips, known-answer vectors hold, and attacks recover their messages."""
import pytest

from codebreaker.ciphers import REGISTRY
from codebreaker.ciphers.machines import enigma
from codebreaker.ciphers.polyalphabetic import quag_e
from codebreaker.ciphers.runner import attack_demo
from codebreaker.text import letters, similarity

ONE_WAY = {c.id for c in REGISTRY.values() if c.decrypt is None}


def norm(s):
    return letters(s).replace("J", "I")


@pytest.mark.parametrize("cid", [c for c in REGISTRY if c not in ONE_WAY])
def test_round_trip(cid):
    c = REGISTRY[cid]
    back = c.decrypt(c.encrypt(c.example, **c.key), **c.key)
    if c.modern:
        expected = c.example[:3] if cid == "shamir" else c.example
        assert back == expected
    elif cid == "tap":
        assert norm(back).replace("K", "C") == norm(c.example).replace("K", "C")
    elif cid == "music_french":  # many letters per note: the most likely reading must give the same notes again
        from codebreaker.ciphers.music import french_e
        assert french_e(back) == french_e(c.example)
    elif cid == "book":
        assert similarity(norm(back), norm(c.example)) > 0.8
    else:
        assert similarity(norm(back)[: len(norm(c.example))], norm(c.example)) > 0.85


@pytest.mark.parametrize("cid", [c.id for c in REGISTRY.values() if c.attack or c.demo_attack])
def test_attack(cid):
    r = attack_demo(cid, seed=4)
    if r.get("kind") == "modern":
        assert r["success"], r
    else:
        assert r["accuracy"] > 0.9, r["accuracy"]


def test_enigma_vector():
    assert enigma("AAAAA") == "BDZGO"


def test_vigenere_vector():
    assert REGISTRY["vigenere"].encrypt("ATTACKATDAWN", key="LEMON") == "LXFOPVEFRNHR"


def test_kryptos_k1_start():
    assert quag_e("BETWEENSUBTLESHADING", "KRYPTOS", "PALIMPSEST").startswith("EMUFPHZLRFAXYUSDJKZL")


def test_sha256_vector():
    assert REGISTRY["hash"].encrypt("abc").startswith("ba7816bf")


def test_classifier_encoding_is_fixed_width():
    from codebreaker.classifier import MAX_LEN, encode

    assert len(encode("ABC")) == MAX_LEN and len(encode("A" * 2000)) == MAX_LEN


def test_bombe_recovers_plugboard_enigma():
    from codebreaker.attacks.bombe import demo

    r = demo(2)
    assert r["success"] and r["found_plugboard"] == r["plugboard"] and r["found_rotors"] == r["rotors"]


def test_five_gram_kernel_scores_english_above_noise():
    import numpy as np

    from codebreaker import kernels_n as N
    from codebreaker.text import to_ints
    from codebreaker.validation import sample_plaintext

    p = to_ints(sample_plaintext(300, "en", 8)).astype(np.int64)
    tab = np.asarray(N.table5())
    assert N.score5(p, tab) > N.score5(np.random.default_rng(1).integers(0, 26, 300), tab)


def test_word_trie_prefers_real_words():
    from codebreaker import kernels_word as W
    from codebreaker.text import to_ints

    child, value = W.build_trie()
    assert W.word_dp(to_ints("THEMANWENTHOME"), child, value, -6.5) > W.word_dp(to_ints("QXZJKVBQXZJKVB"), child, value, -6.5)
