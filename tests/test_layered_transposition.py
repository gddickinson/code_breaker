"""Round 35: routes and columnar keys under a substitution layer."""
from codebreaker.mysteries import figaro_layered as F
from codebreaker.mysteries.figaro_wide import overlap6


def test_every_route_is_a_permutation():
    for name in F.ROUTES:
        for n, w in ((50, 7), (53, 6), (100, 12), (9, 3)):
            assert sorted(F.route(n, w, name)) == list(range(n))
    assert F.route(6, 3, "snake rows") == [0, 1, 2, 5, 4, 3]
    assert F.route(6, 3, "spiral in") == [0, 1, 2, 5, 4, 3]
    assert F.route(9, 3, "spiral in") == [0, 1, 2, 5, 8, 7, 6, 3, 4]


def test_route_with_substitution_control():
    plain, ct = F._plant("routes", 100, 9, 2)
    got = F.search_routes(ct, 2)
    assert overlap6(got["text"], plain) >= 0.7 and "width 9" in got["model"]


def test_joint_anneal_solves_width_6():
    plain, ct = F._plant("columnar", 120, 6, 1)
    got = F.search_joint(ct, 1, widths=[6], iters=300000, restarts=10)
    assert overlap6(got["text"], plain) >= 0.7



def test_routes_skip_the_identity_order():
    """A 2-wide diagonal route keeps the letters in place; it must not pass as a transposition."""
    import numpy as np

    from codebreaker.text import to_ints

    ct = to_ints("lesoldatsdupremierregimentarriverontdemain")
    names = [n for n, t in F.route_texts(ct)]
    assert "diagonals, width 2, undo" not in names
    assert all(not (t == ct).all() for _, t in F.route_texts(ct))
