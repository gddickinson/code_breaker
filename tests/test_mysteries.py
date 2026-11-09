"""Source data integrity: if these fail, a downloaded ciphertext has changed."""
from codebreaker.mysteries import beale, dagapeyeff, kryptos, tamam


def test_beale_counts_match_published():
    c = beale.ciphers()
    assert len(c["B1"]) == 520 and len(c["B3"]) == 618


def test_beale2_decodes_with_declaration():
    b2 = beale.decode(beale.ciphers()["B2"], beale.initials("declaration.txt")).lower()
    assert b2.startswith("iha") and "fourmiles" in b2


def test_kryptos_sections():
    s = kryptos.sections()
    assert {k: len(v) for k, v in s.items()} == {"K1": 63, "K2": 369, "K3": 336, "K4": 97}
    assert s["K4"][21:25] == "FLRV" and s["K4"][63:69] == "NYPVTT" and s["K4"][69:74] == "MZFPK"


def test_dagapeyeff_length():
    assert len(dagapeyeff.digits()) == 395


def test_tamam_length():
    assert len(tamam.CODE) == 44
