"""Round 93b: PaddleOCR recognisers for other scripts (measured, not adopted)."""
import numpy as np

from codebreaker.lens import paddle_ocr
from codebreaker.lens.scripts_ocr_eval import cer


def test_cer_ignores_spaces_and_case():
    assert cer("Привет мир", "привет  мир") == 0.0 and cer("abcd", "abxd") == 0.25 and cer("ab", "") == 1.0


def test_paddle_reports_nothing_when_a_script_is_not_installed(monkeypatch):
    monkeypatch.setattr(paddle_ocr, "DIR", paddle_ocr.DIR / "none-such")
    assert paddle_ocr.read(np.full((40, 200), 255, np.uint8), "Arabic") == "" and paddle_ocr.read_line(np.full((40, 200), 255, np.uint8), "Hangul") == ""
    assert not paddle_ocr.available("Latin")
