"""Optional AI layer (Round 90a): what is available, and calls to local models through Ollama.

Every feature of the app works without it. Only local models are used here: pictures and text stay on this machine.
A Claude API key, if one is set in the environment, is reported but never used without the user's explicit opt-in
(not implemented: Round 90b and later). Calls have time limits; failures return None so callers fall back to the
app's own algorithms and say which mode ran."""
import base64
import json
import os
import time
import urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
VISION = ("qwen2.5vl:7b", "moondream:latest")
TEXT = ("qwen2.5:14b",)
_status = {"checked": 0.0, "value": None}


def _get(path: str, timeout: float = 2.0):
    with urllib.request.urlopen(OLLAMA + path, timeout=timeout) as r:
        return json.loads(r.read())


def status(max_age: float = 60.0) -> dict:
    """{'ollama': bool, 'models': [...], 'vision': name or None, 'text': name or None, 'claude_key_set': bool}."""
    if _status["value"] is not None and time.time() - _status["checked"] < max_age:
        return _status["value"]
    try:
        models = [m["name"] for m in _get("/api/tags")["models"]]
        up = True
    except Exception:  # not installed or not running
        models, up = [], False
    v = {"ollama": up, "models": models, "vision": next((m for m in VISION if m in models), None),
         "text": next((m for m in TEXT if m in models), None), "claude_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
         "claude_used": False, "note": "Local models only; nothing leaves this machine." if up else "No local AI found: the app's own algorithms run."}
    _status.update(checked=time.time(), value=v)
    return v


def generate(model: str, prompt: str, images: list[bytes] | None = None, timeout: float = 120.0, num_predict: int = 400) -> dict | None:
    """{'text', 'seconds'} or None when the model is not available or the call fails."""
    body = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0, "num_predict": num_predict}}
    if images:
        body["images"] = [base64.b64encode(b).decode() for b in images]
    req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read())
    except Exception:
        return None
    return {"text": out.get("response", ""), "seconds": round(time.time() - t, 1), "model": model}
