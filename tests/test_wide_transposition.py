"""Round 34: wide columnar keys by hill-climbing."""
import random

import numpy as np

from codebreaker import kernels_t as T
from codebreaker.kernels import columnar_decrypt
from codebreaker.mysteries import figaro_wide as W
from codebreaker.mysteries.figaro_transposition import redo, undo
from codebreaker.text import to_ints, to_text

PLAIN = ("lesoldatsdupremierregimentarriverontdemainmatinalagaredelestetattendrontlordreducolonel"
         "avantdepartirpourlafrontiereaveclesvivresetlesmunitions")


def test_kernels_are_inverses_and_match_python():
    rnd = random.Random(2)
    for k in (8, 11, 16):
        perm = rnd.sample(range(k), k)
        p = to_ints(PLAIN)
        enc = T.columnar_encrypt(p, np.array(perm, np.int64))
        assert to_text(enc).lower() == redo(PLAIN, tuple(perm))
        assert (columnar_decrypt(enc, np.array(perm, np.int64)) == p).all()
        assert undo(to_text(enc).lower(), tuple(perm)) == PLAIN


def test_climber_finds_width_12_key_both_ways():
    perm = np.array(random.Random(5).sample(range(12), 12), np.int64)
    p = to_ints(PLAIN)
    ct = to_text(T.columnar_encrypt(p, perm)).lower()
    got = W.search(ct, 1, widths=[12])
    assert W.overlap6(got["text"], PLAIN) >= 0.9
    ct2 = to_text(columnar_decrypt(p, perm)).lower()
    got2 = W.search(ct2, 1, widths=[12])
    assert got2["direction"] == "reverse" and W.overlap6(got2["text"], PLAIN) >= 0.7  # may come out rotated or in reordered blocks


def test_shuffle_scores_below_real():
    rnd = random.Random(3)
    perm = np.array(rnd.sample(range(10), 10), np.int64)
    ct = to_text(T.columnar_encrypt(to_ints(PLAIN), perm)).lower()
    s = list(ct)
    rnd.shuffle(s)
    assert W.search(ct, 2, widths=[10])["score"] > W.search("".join(s), 2, widths=[10])["score"] + 0.3


def test_overlap6_counts_rotations():
    assert W.overlap6(PLAIN[40:] + PLAIN[:40], PLAIN) > 0.9 and W.overlap6("x" * 50, PLAIN) == 0


def test_solved_reading_has_word_coverage():
    """Regression: coverage() counts upper-case text only; a solved control must show real words."""
    from codebreaker.validation import coverage

    perm = np.array(random.Random(7).sample(range(9), 9), np.int64)
    got = W.search(to_text(T.columnar_encrypt(to_ints(PLAIN), perm)).lower(), 1, widths=[9])
    assert coverage(got["text"].upper(), "fr") > 0.6
