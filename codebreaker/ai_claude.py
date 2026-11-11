"""Claude as an optional reader and advisor (Round 90d), off unless the user turns it on in Settings.

Safety: (1) off by default; turning it on needs a key and an acknowledgement that pictures and text are sent to
Anthropic and cost money; each use is chosen again where it happens. (2) The key never enters the repository or the
browser: it comes from the ANTHROPIC_API_KEY environment variable, or from a settings file outside the repository
(~/.config/code_breaker/claude.json, or $CODEBREAKER_CONFIG_DIR) written with owner-only permissions (0600); status()
reports only whether a key is set and where from. (3) The routes that change settings accept requests from this
machine only (web/routes_settings.py). (4) Nothing here logs the key. Model: claude-opus-5-5, effort low, short
timeouts; the server-side refusal fallback is on (fallbacks "default")."""
import base64
import json
import os
import stat
import time
from pathlib import Path

MODEL = "claude-opus-5-5"
TIMEOUT = 60.0


def config_path() -> Path:
    base = Path(os.environ.get("CODEBREAKER_CONFIG_DIR") or Path.home() / ".config/code_breaker")
    return base / "claude.json"


def _load() -> dict:
    p = config_path()
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(d: dict) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(d, f)
    os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)


def _key() -> tuple[str | None, str | None]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"], "environment variable ANTHROPIC_API_KEY"
    k = _load().get("key")
    return (k, "local settings file") if k else (None, None)


def status() -> dict:
    """What the Settings page may see: never the key itself."""
    d = _load()
    key, source = _key()
    try:
        import anthropic  # noqa: F401

        sdk = True
    except ImportError:
        sdk = False
    return {"enabled": bool(d.get("enabled")) and bool(key) and sdk, "requested": bool(d.get("enabled")), "key_set": bool(key), "key_source": source,
            "sdk_installed": sdk, "model": MODEL, "settings_file": str(config_path()),
            "note": "Pictures and text you send to Claude leave this machine and are processed by Anthropic; calls are billed to the key's account."}


def configure(enabled: bool, acknowledged: bool, key: str | None = None) -> dict:
    d = _load()
    if key is not None:
        key = key.strip()
        if not key.startswith("sk-ant-") or len(key) < 30 or any(c.isspace() for c in key):
            raise ValueError("That does not look like an Anthropic API key (it should start with sk-ant-).")
        d["key"] = key
    if enabled and not acknowledged:
        raise ValueError("Turning Claude on needs the acknowledgement that data leaves this machine.")
    d["enabled"] = bool(enabled)
    d["acknowledged_at"] = time.strftime("%Y-%m-%d %H:%M") if enabled else d.get("acknowledged_at")
    _save(d)
    return status()


def forget_key() -> dict:
    d = _load()
    d.pop("key", None)
    d["enabled"] = False
    _save(d)
    return status()


def _client():
    import anthropic

    key, _ = _key()
    return anthropic.Anthropic(api_key=key, timeout=TIMEOUT, max_retries=1)


def generate(prompt: str, images: list[bytes] | None = None, max_tokens: int = 1024) -> dict | None:
    """{'text', 'seconds', 'model'} or None when Claude is off, unconfigured, refused or unreachable."""
    if not status()["enabled"]:
        return None
    import anthropic

    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.standard_b64encode(b).decode()}} for b in images or []]
    content.append({"type": "text", "text": prompt})
    t = time.time()
    try:
        r = _client().beta.messages.create(model=MODEL, max_tokens=max_tokens, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                                           output_config={"effort": "low"}, messages=[{"role": "user", "content": content}])
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        return None
    if r.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in r.content if b.type == "text")
    return {"text": text, "seconds": round(time.time() - t, 1), "model": r.model}


def test() -> dict:
    """One tiny call, to check the key; reports the error class, never the key."""
    if not status()["key_set"]:
        return {"ok": False, "message": "No key is set."}
    import anthropic

    try:
        r = _client().beta.messages.create(model=MODEL, max_tokens=64, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                                           output_config={"effort": "low"}, messages=[{"role": "user", "content": "Reply with the single word OK."}])
        return {"ok": True, "message": f"Connected: {r.model} answered.", "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}
    except anthropic.AuthenticationError:
        return {"ok": False, "message": "The key was refused (authentication error)."}
    except anthropic.PermissionDeniedError:
        return {"ok": False, "message": "The key lacks permission for this model."}
    except anthropic.RateLimitError:
        return {"ok": False, "message": "Rate limited; try again later."}
    except anthropic.APIStatusError as e:
        return {"ok": False, "message": f"The API answered with status {e.status_code}."}
    except anthropic.APIConnectionError:
        return {"ok": False, "message": "Could not reach the API (network)."}
