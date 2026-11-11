"""Round 77b: Viking-age rune ciphers reproduce the resolved ciphers recorded for the Rök runestone."""
from codebreaker.ciphers import REGISTRY
from codebreaker.ciphers import runic as R
from codebreaker.ciphers.runner import attack_demo


def test_younger_futhark_from_source():
    vals, index, long_row = R.younger()
    assert "".join(vals) == "fuþąrkhniastbmlʀ" and len(long_row) == 16 and len(index) >= 25


def test_rok_branch_pairs():
    rok = R.rok_pairs()
    assert len(rok["pairs"]) == 30
    _, index, _ = R.younger()
    assert all(R.from_aett_pos(a, b, True) == index[r] for a, b, r in rok["pairs"])


def test_rok_shifted_passages():
    rok = R.rok_pairs()
    assert len(rok["shifts"]) == 2
    for cipher, plain in rok["shifts"]:
        assert R.shift_d(cipher, 15) == R.from_index([R.younger()[1][c] for c in plain])
    assert R.shift_d(rok["shifts"][1][0], 15) == "KNUAKNAT"


def test_round_trip_and_attacks():
    assert REGISTRY["branch_runes"].decrypt(REGISTRY["branch_runes"].encrypt("sakum mukmini")) == "SAKUM MUKMINI"
    assert REGISTRY["futhark_shift"].decrypt(REGISTRY["futhark_shift"].encrypt("sakum mukmini", shift=5), shift=5) == "SAKUM MUKMINI"
    for cid in ("branch_runes", "futhark_shift"):
        assert attack_demo(cid, seed=4)["accuracy"] > 0.95
