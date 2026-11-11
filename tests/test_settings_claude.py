"""Round 90d: the optional Claude connection is off by default, keeps the key out of the repository and the page,
and accepts setting changes from this computer only. No call to Anthropic is made here."""
import os
import stat

import pytest
from fastapi.testclient import TestClient

from codebreaker import ai_claude
from codebreaker.web.app import app

KEY = "sk-ant-api03-" + "x" * 40


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEBREAKER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_off_by_default_and_generate_sends_nothing():
    s = ai_claude.status()
    assert not s["enabled"] and not s["key_set"] and ai_claude.generate("hello") is None


def test_turning_on_needs_the_acknowledgement_and_a_real_looking_key():
    with pytest.raises(ValueError):
        ai_claude.configure(True, False, KEY)
    with pytest.raises(ValueError):
        ai_claude.configure(True, True, "not-a-key")
    s = ai_claude.configure(True, True, KEY)
    assert s["enabled"] == s["sdk_installed"] and s["key_set"] and s["key_source"] == "local settings file"


def test_key_file_is_private_and_outside_the_repository():
    ai_claude.configure(False, False, KEY)
    p = ai_claude.config_path()
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
    assert not str(p.resolve()).startswith(str(ai_claude.Path(__file__).resolve().parents[1]))


def test_routes_never_return_the_key_and_refuse_other_computers():
    local = TestClient(app, client=("127.0.0.1", 50000))
    r = local.post("/api/settings/claude", json={"enabled": True, "acknowledged": True, "key": KEY})
    assert r.status_code == 200 and KEY not in r.text
    assert KEY not in local.get("/api/settings/claude").text
    far = TestClient(app, client=("10.0.0.5", 50000))
    assert far.post("/api/settings/claude", json={"enabled": False}).status_code == 403
    assert far.post("/api/settings/claude/test").status_code == 403
    assert local.post("/api/settings/claude/forget").json()["key_set"] is False


def test_environment_key_wins_and_is_not_written(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    s = ai_claude.status()
    assert s["key_set"] and s["key_source"].startswith("environment") and not ai_claude.config_path().exists()
