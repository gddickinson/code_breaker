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


def test_verdict_rejects_structure_without_text():
    from codebreaker.validation import verdict

    pc = {"mean": 1.0, "solved_score": -4.1, "true_coverage": 0.7}
    assert verdict(pc, 9.0, 1, "QXZJKVBQXZJKVBQXZJ", -5.2).startswith("Structure only")
    assert verdict({**pc, "mean": 0.1}, 9.0, 1, "X", -5.2).startswith("Inconclusive")
    assert verdict(pc, 9.0, 1, "THEQUESTIONWASWHETHERTHEMANWOULDRETURNBEFOREEVENING", -4.0).startswith("Readable")


def test_phaistos_published_counts():
    from codebreaker.mysteries.scriptlab import phaistos

    seq = [s for w in phaistos() for s in w]
    assert len(seq) == 241 and len(set(seq)) == 45


def test_beale_last_letter_control_finds_planted_key():
    from codebreaker.mysteries.beale_forensics import rule_control

    r = rule_control()
    assert r["found"] and r["z"] > 8


def test_dagapeyeff_is_a_square():
    from codebreaker.mysteries.dagapeyeff import digits, pairs_of

    d = digits()
    assert len(pairs_of(d[:-3])) == 196
