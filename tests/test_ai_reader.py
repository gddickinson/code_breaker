"""Round 92: the language model as reader; parts testable without a model."""
import random

from codebreaker import ai_local
from codebreaker import ai_reader as R
from codebreaker.ai_reader_eval import candidates, expanded_words, near_miss


def test_near_misses_have_about_the_share_of_wrong_letters():
    t = "SUISETRETATHOTBLAQUETENVOIEUNPEUARGENTTAIMEATOITOUTE"
    for share in (0.1, 0.3):
        wrong = sum(a != b for a, b in zip(near_miss(t, share, random.Random(1)), t)) / len(t)
        assert share <= wrong <= share + 0.25
    c = candidates(t, random.Random(2))
    assert c["truth"] == t and sorted(c["shuffled"]) == sorted(t) and len(set(c.values())) == 5


def test_expanded_words_come_from_mullers_brackets():
    assert expanded_words("X - Suis Etretat, hôt[el] Bla[n]quet. Envoie un peu [d']argent. (ae) note [x]y") == ["hotel", "blanquet", "dargent"]


def test_rank_rejects_answers_out_of_range(monkeypatch):
    monkeypatch.setattr(ai_local, "status", lambda max_age=60.0: {"text": "m"})
    monkeypatch.setattr(ai_local, "generate", lambda *a, **k: {"text": '{"choice": 9}', "seconds": 0.1})
    assert R.rank(["AB", "CD"]) is None
    monkeypatch.setattr(ai_local, "generate", lambda *a, **k: {"text": "no json", "seconds": 0.1})
    assert R.meaningful("ABC") == {"meaningful": False, "translation": ""}
