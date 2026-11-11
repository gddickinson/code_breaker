"""Round 90a: the optional AI layer; these tests do not need Ollama."""
import numpy as np

from codebreaker import ai_local
from codebreaker.lens import ai_check as AC


def test_model_words_confirmed_only_where_ocr_letters_agree():
    c = AC.check(["ALTOIDS", "Wrigley", "Hackettstown", "peppermint"], ["ALT0IDS", "WRIGLEY", "Hackett"], ["Hackettstown NJ"])
    assert c["confirmed"] == ["ALTOIDS", "Wrigley", "Hackettstown"] and c["ai_only"] == ["peppermint"]


def test_short_words_need_a_close_ocr_word():
    assert AC.check(["of"], ["or"], ["profit"])["ai_only"] == []  # one edit
    assert AC.check(["xy"], ["ab"], ["text"])["ai_only"] == ["xy"]


def test_without_a_vision_model_the_lens_says_so(monkeypatch):
    monkeypatch.setattr(ai_local, "status", lambda max_age=60.0: {"vision": None, "note": "No local AI found: the app's own algorithms run."})
    r = AC.second_reader(np.full((40, 40), 255, np.uint8), {"words": []})
    assert r["mode"] == "own algorithms only" and "No local AI" in r["note"]


def test_status_reports_without_failing(monkeypatch):
    monkeypatch.setattr(ai_local, "OLLAMA", "http://127.0.0.1:9")  # nothing listens there
    ai_local._status["value"] = None
    s = ai_local.status()
    assert s["ollama"] is False and s["vision"] is None and s["claude_used"] is False
    ai_local._status["value"] = None
