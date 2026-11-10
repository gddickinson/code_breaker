"""Round 40: pooled blind solves by writer."""
from codebreaker.mysteries import figaro_pooled as P


def test_plain_stretches_are_cut_and_cipher_kept():
    t = "pourraiocnitgvqwvgycpvrtgxgpwogtepltgnkdtg"
    out = P.cipher_part(t)
    assert not out.startswith("pourrai") and "ocnitgvqwvgycpv" in out


def test_mask_needs_runs_of_six():
    m = P.plain_mask("xqzjelaimexqzj")
    assert not any(m[:4]) and not any(m[-4:])


def test_signature_parsing():
    assert P.signature("1893_18930704-TR.jpg") == "TR" and P.signature("1896_18960715.jpg") == ""


def test_planted_control_is_a_substitution_of_real_printed_text():
    plain, ct = P.planted(200, 1)
    assert len(plain) == len(ct) == 200
    pairs = {}
    for a, b in zip(plain, ct):
        assert pairs.setdefault(a, b) == b
