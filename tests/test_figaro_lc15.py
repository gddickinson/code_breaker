"""Round 51: the L. C. 15 and L. R. G. series."""
import json
import random
import re
from difflib import SequenceMatcher

from codebreaker.mysteries import figaro_lc15 as F


def test_transcriptions_exist_and_match_ocr():
    raw = json.loads((F.OUT / "ocr_raw.json").read_text())
    ok = tot = 0
    for group in ("lc15_digits", "lc15_letters", "lrg"):
        for image, text in F.DATA[group].items():
            assert (F.OUT / "images" / image).exists()
            ocr = re.sub(r"[^a-z0-9;?]", "", " ".join(raw.get(image, {}).get("tesseract") or []).lower())
            tot += 1
            ok += SequenceMatcher(None, text, ocr).find_longest_match(0, len(text), 0, len(ocr)).size >= 6
    assert ok / tot >= 0.8


def test_repeat_share_counts_shared_kgrams():
    assert F.repeat_share(["abcdefxyz", "zzabcdeqq"]) == 10 / 18
    rnd = random.Random(1)
    assert F.repeat_share(F.shuffled_texts(["abcdefxyz", "zzabcdeqq"], rnd)) <= 1


def test_ic():
    assert abs(F.index_of_coincidence("aaaa") - 1) < 1e-9 and F.index_of_coincidence("abcd") == 0


def test_recorded_result_has_working_controls():
    r = json.loads(F.RESULT.read_text())
    assert r["repeats"]["lrg"]["share"] > 3 * r["repeats"]["lrg"]["null_max"]
    assert r["blind_lc15"]["planted_accuracy"] > 0.9 and not r["blind_lc15"]["reads"]
    assert r["blind_lc15_letters"]["planted_accuracy"] > 0.9 and r["blind_lc15_letters"]["coverage"] < 0.3
