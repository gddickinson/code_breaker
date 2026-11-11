"""Round 93: fastText as an optional second language identifier."""
import pytest

from codebreaker import langid_fasttext as F

need = pytest.mark.skipif(not F.MODEL.exists(), reason="fastText model not fetched (scripts/fetch_tools.py)")


@need
def test_fasttext_maps_codes_to_the_apps():
    assert F.detect("Rendez-vous demain à midi près du pont", 1)[0]["lang"] == "fr"
    assert F.detect("Vi ses i morgon vid bron klockan tolv, ta med boken", 1)[0]["lang"] == "sv"
    assert F.detect("Eu vou para casa amanhã de manhã com a minha irmã", 1)[0]["lang"] == "pb"


@need
def test_lens_rule_keeps_the_apps_answer_when_it_is_sure():
    code, how = F.lens_name("The quick brown fox jumps over the lazy dog near the river bank")
    assert code == "en" and how == "character statistics"


def test_without_the_model_nothing_is_named(monkeypatch):
    monkeypatch.setattr(F, "_model", lambda: None)
    assert F.detect("bonjour") == [] and not F.available()
