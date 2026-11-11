"""A local language model as reader of solver output (Round 92): ranking candidates, judging meaning, expanding
abbreviations. Its answers are leads only: a reading counts only under the three gates (validation.py) and a by-eye
check, because a language model can find meaning in noise (measured in ai_reader_eval.py). Local model only."""
import json
import re

from . import ai_local
from .segment import segment

LANG = {"fr": "French", "frad": "French (abbreviated, as in 19th-century newspaper personal ads)", "en": "English", "la": "Latin", "de": "German"}


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


def _ask(prompt: str, n: int = 200) -> dict | None:
    model = ai_local.status()["text"]
    if not model:
        return None
    r = ai_local.generate(model, prompt, timeout=90.0, num_predict=n)
    if r is None:
        return None
    return {**_json(r["text"]), "_raw": r["text"][:300], "_seconds": r["seconds"]}


def shown(text: str, lang: str) -> str:
    """Candidates come without word breaks; every reader sees the same segmentation."""
    return segment(text.upper(), lang if lang != "frad" else "frad")


def rank(candidates: list[str], lang: str = "frad") -> int | None:
    """Index of the candidate the model judges the real message, or None."""
    listing = "\n".join(f"{i + 1}. {shown(c, lang)}" for i, c in enumerate(candidates))
    d = _ask(f"These are candidate decryptions of one short {LANG.get(lang, lang)} message; word breaks were added by a program and may be wrong. "
             f"Which one is the real message? Answer only with JSON: {{\"choice\": <number>, \"reason\": \"...\"}}.\n{listing}", 120)
    try:
        k = int((d or {}).get("choice")) - 1
    except (TypeError, ValueError):
        return None
    return k if 0 <= k < len(candidates) else None


def meaningful(text: str, lang: str = "frad") -> dict | None:
    d = _ask(f"Is the following a meaningful {LANG.get(lang, lang)} message (abbreviations allowed), or meaningless letters? Word breaks were added by a "
             f"program. Answer only with JSON: {{\"meaningful\": true or false, \"translation\": \"English, or empty\"}}.\nText: {shown(text, lang)}", 160)
    return None if d is None else {"meaningful": bool(d.get("meaningful")), "translation": str(d.get("translation", ""))[:200]}


def expand(text: str, lang: str = "frad") -> dict | None:
    d = _ask(f"This is an abbreviated {LANG.get(lang, lang)} message from a 19th-century personal ad (letters were dropped from many words). Write it out "
             f"in full {LANG.get('fr' if lang == 'frad' else lang, lang)}, changing as little as possible. If it is not that language, answer \"NONE\". "
             f"Answer only with JSON: {{\"expanded\": \"...\"}}.\nText: {text}", 250)
    return None if d is None else {"expanded": str(d.get("expanded", "")).strip()}
