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
