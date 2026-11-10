"""Round 76: ciphers written in other scripts, and the crack's script and symbol layers."""
from codebreaker.ciphers import REGISTRY
from codebreaker.ciphers.base import DEMO_PLAIN
from codebreaker.ciphers.runner import attack_demo
from codebreaker.ciphers.scripts import RUNES
from codebreaker.crack import crack
from codebreaker.crack_steps import script_layer


def test_registered_and_round_trip():
    assert len(set(RUNES)) == 26
    for cid in ("runes", "ogham", "hieroglyph_alphabet", "rune_substitution"):
        d = REGISTRY[cid].detail()
        assert d["family"] == "Scripts" and d["example_back"]
    assert REGISTRY["runes"].decrypt(REGISTRY["runes"].encrypt("Meet at the old bridge")) == "MEETATTHEOLDBRIDGE"
    assert REGISTRY["rune_substitution"].decrypt(REGISTRY["rune_substitution"].encrypt("attack at dawn", keyword="ODIN"), keyword="ODIN") == "ATTACKATDAWN"


def test_rune_substitution_attack_demo():
    assert attack_demo("rune_substitution", seed=3)["accuracy"] > 0.9


def test_script_layer_choices():
    runes = script_layer(REGISTRY["runes"].encrypt(DEMO_PLAIN[:120]))
    assert runes["name"] == "Runes transliterated" and runes["text"].startswith("THE OLD LIGHTHOUSE")
    sub = script_layer(REGISTRY["rune_substitution"].encrypt(DEMO_PLAIN[:120], keyword="VALHALLA"))
    assert "relabelled" in sub["name"] and sub["text"].startswith("ABC DEF")
    assert script_layer("plain English text here") is None


def test_crack_reads_runes():
    end = list(crack(REGISTRY["runes"].encrypt(DEMO_PLAIN), budget=20))[-1]
    assert end["verdict"]["level"] == "readable" and end["best"]["plaintext"].startswith("THE OLD LIGHTHOUSE")
