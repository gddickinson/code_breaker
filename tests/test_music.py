"""Round 81: music ciphers, checked against the recorded examples of the 'Musical cryptogram' page."""
from codebreaker.ciphers import REGISTRY
from codebreaker.ciphers.base import DEMO_PLAIN
from codebreaker.ciphers.music import french_a, french_e, german_d, german_e
from codebreaker.ciphers.runner import attack_demo
from codebreaker.text import letters, similarity


def test_recorded_examples():
    assert german_e("Bach") == "B♭ A C B♮" and german_d("B♭ A C B♮") == "BACH"
    assert german_e("Asch") == "A E♭ C B♮"  # Schumann's Carnaval
    assert german_e("DSCH") == "D E♭ C B♮"  # Shostakovich
    assert french_e("HAYDN") == "B♮ A D D G"  # Ravel 1909: H kept as B-natural


def test_french_rows_and_attack():
    assert french_e("AOV") == "A A A" and french_e("BIPW") == "B♮ B♮ B♮ B♮"
    r = french_a(french_e(DEMO_PLAIN))
    assert similarity(letters(DEMO_PLAIN), letters(r["plaintext"])) > 0.6


def test_note_substitution_round_trip_and_attack():
    c = REGISTRY["music_notes"]
    assert c.decrypt(c.encrypt("attack at dawn", keyword="BACH"), keyword="BACH") == "ATTACKATDAWN"
    assert attack_demo("music_notes", seed=3)["accuracy"] > 0.95
