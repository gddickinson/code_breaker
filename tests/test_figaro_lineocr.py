"""Round 88b: data, alignment and model shapes for the Le Figaro line reader (no training here)."""
import random

import pytest
import torch

from codebreaker.mysteries import figaro_lineocr as M
from codebreaker.mysteries import figaro_lineocr_data as D

scans = pytest.mark.skipif(not D.IMAGES.exists(), reason="Le Figaro scans not fetched")


def test_cer_finds_the_transcription_inside_a_reading():
    assert D.cer("96709mo3go5", "L. C. 15.— 96709mo3go5.") == 0.0
    assert abs(D.cer("96709mo3go5iogiui6082", "LC15 96709mo3go5iogiui6O82") - 1 / 21) < 1e-9
    assert D.cer("abc", "") == 1.0


def test_decode_collapses_repeats_and_blanks():
    seq = [1, 1, 0, 1, 2, 2, 0, 0, 27]  # a a _ a b b _ _ 0
    logits = torch.nn.functional.one_hot(torch.tensor([seq]), M.N_CLASSES).float()
    assert M.decode(logits) == ["aab0"]


def test_model_maps_a_line_to_a_quarter_width_sequence():
    net = M.CRNN().eval()
    x = M.batch([D.render("abc 123", random.Random(1))])
    assert net(x).shape[0] == 1 and net(x).shape[1] == x.shape[-1] // 4 and net(x).shape[2] == M.N_CLASSES


def test_held_out_split_is_fixed_by_name():
    assert M.held_out("1879_18790809-LC15.jpg") == M.held_out("1879_18790809-LC15.jpg")


@scans
def test_truth_and_line_cutting():
    t = D.truth()
    assert len(t) >= 100 and t["1879_18790809-LC15.jpg"] == "96709mo3go5iogiui6082do37ymmy72s370"
    assert len(D.cut_lines(D.gray(D.IMAGES / "1886_18860906-Jane.jpg"))) >= 7
    assert len(D.cut_lines(D.gray(D.IMAGES / "1879_18790809-LC15.jpg"))) == 1
