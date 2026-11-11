"""Round 93c: handwriting readers (TrOCR optional)."""
import random

import numpy as np

from codebreaker.lens import handwriting
from codebreaker.lens.handwriting_eval import draw, invented


def test_draw_gives_a_cropped_line():
    a = draw("meet me at the bridge", "Bradley Hand Bold.ttf", random.Random(1))
    assert a.ndim == 2 and a.shape[0] < 120 and a.shape[1] > 300


def test_invented_counts_dictionary_words_not_in_the_truth():
    assert invented("qzxv plorb", "the qzxv house") == 2 and invented("abc", "abc") == 0


def test_without_trocr_nothing_is_read(monkeypatch):
    monkeypatch.setattr(handwriting, "CACHE", handwriting.CACHE / "none-such")
    assert not handwriting.available() and handwriting.read_line(np.full((40, 200), 255, np.uint8)) == ""
