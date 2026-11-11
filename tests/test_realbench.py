"""Round 87: the real-material benchmark is built correctly (truths from published keys, documented systems applied
in the right direction, Müller's expansions dropped)."""
import pytest

from codebreaker.mysteries import realbench as R
from codebreaker.text import letters


def test_expansions_initials_and_signature_dropped():
    assert R.enciphered_part("CH - Veux v[ous] voir. Vais parti[r]. (ae)", "CH") == "VEUXVVOIRVAISPARTI"
    assert R.enciphered_part("Je fus empêché jeudi - Ecrivez quand. (dm) Ce n'est ni la façon", "cydalise") == "JEFUSEMPECHEJEUDIECRIVEZQUAND"


def test_vigenere_without_w_round_trips_with_the_documented_decryption():
    from codebreaker.mysteries.figaro_keys import vig

    plain = "VEUXVOUSVOIRBEAUCOUPAVOUSDIRE"
    assert vig(R._vig_enc(plain, "CEAD"), "CEAD", R.NOW) == plain


def test_tier1_truths_from_published_keys():
    t = {x["name"]: x for x in R.tier1()}
    assert t["Kryptos K1"]["truth"].startswith("BETWEENSUBTLESHADING")
    assert t["Kryptos K3"]["truth"].startswith("SLOWLYDESPARATLYSLOWLY")
    if "Beale 2" in t:
        assert t["Beale 2"]["truth"].startswith("IHAREDEPOSCTED")  # the pamphlet's own encoding slips


def test_tier2_ciphers_decrypt_to_their_truths():
    try:
        items = R.tier2()
    except FileNotFoundError:
        pytest.skip("Le Figaro data not fetched")
    from codebreaker.mysteries.figaro_keys import TABLES, vig

    tables = {t["id"]: t["map"] for t in TABLES}
    assert len(items) >= 40
    for x in items:
        if x["system"].startswith("Vigenere"):
            assert vig(x["cipher"], x["system"].split()[1], R.NOW) == x["truth"]
        elif x["system"].startswith("table"):
            m = tables[x["system"].split()[1]]
            assert "".join(m[c] for c in x["cipher"]) == x["truth"]
        else:
            assert x["cipher"][::-1] == x["truth"] == letters(x["truth"])


def test_vigenere_without_w_attack_reads_a_cead_style_message():
    from codebreaker.ciphers.vigenere25 import attack, encrypt

    plain = letters("Veux vous voir beaucoup a vous dire je pars demain ecrivez moi poste restante rue de rivoli")
    r = attack(encrypt(plain, "CEAD"), "fr")
    assert r["plaintext"] == plain.replace("W", "V") and r["key"]["key"] == "CEAD"


def test_adfgx_refuses_text_outside_its_signal_letters():
    from codebreaker.ciphers import REGISTRY

    with pytest.raises(ValueError):
        REGISTRY["adfgx"].attack("TUVEUXQUEMVIENNEDEBONNEHEUREJENETEVERRAIPRESQUE", "fr")


def test_short_texts_keep_a_core_language_slot():
    from codebreaker.langchoice import choose
    from codebreaker.languages import LANGS

    assert any(c in LANGS or c == "frad" for c in choose("QGCITTRSHCBGWZSBSQFWJWHACBGSIZOACI"))
