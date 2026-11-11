"""Round 85: language identification over about 50 languages and translation into English."""
import json

import pytest

from codebreaker import langid
from codebreaker.translate import available, cipher_like, translate


def test_identifier_recorded_accuracy():
    r = json.loads(langid.RESULT.read_text())
    assert r["languages"] >= 45 and r["lengths"]["50"]["accuracy"] >= 0.88 and r["lengths"]["200"]["accuracy"] >= 0.95


def test_identifies_common_sentences():
    for text, code in (("Rendez-vous demain à midi près du pont.", "fr"), ("Wir treffen uns morgen am Bahnhof.", "de"),
                       ("We zien elkaar morgen bij het station.", "nl"), ("Spotkajmy się jutro na dworcu kolejowym.", "pl"),
                       ("Καλημέρα κόσμε, αυτό είναι μια δοκιμή.", "el"), ("Bon dia, com estàs avui?", "ca")):
        assert langid.detect(text, 1)[0]["lang"] == code, text


def test_cipher_output_keeps_the_old_path():
    assert cipher_like("SEEYOUTOMORROWATTHESTATION") and not cipher_like("See you tomorrow")
    assert translate("SEEYOUTOMORROWATTHESTATION")["spaced"].startswith("SEE YOU")


def test_translators_checked():
    r = json.loads((langid.ROOT / "data/results/translators_check.json").read_text())
    assert len(r["working"]) >= 45


@pytest.mark.skipif("nl" not in available(), reason="Dutch translator not installed")
def test_translates_dutch():
    assert "station" in (translate("We zien elkaar morgen bij het station.")["translation"] or "").lower()
