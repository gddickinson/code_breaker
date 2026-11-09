"""Offline translation via Argos Translate models, plus language detection for solved text."""
from .languages import LANGS, detect
from .segment import segment

ARGOS = {"fr", "de", "it", "es"}


def available() -> list[str]:
    try:
        import argostranslate.package as pkg
        return sorted({p.from_code for p in pkg.get_installed_packages() if p.to_code == "en"})
    except Exception:
        return []


def translate(text: str, source: str | None = None, target: str = "en") -> dict:
    """Detect, add word breaks to unspaced cipher output, then translate if a model exists."""
    guesses = detect(text)
    source = source or guesses[0]["lang"]
    spaced = segment(text.upper(), source) if " " not in text.strip() and text.strip() else text
    res = {"source": source, "source_name": LANGS.get(source, source), "detected": guesses, "spaced": spaced, "translation": None, "note": ""}
    if source == target:
        res["note"] = "Text is already in the target language."
        return res
    if source == "la":
        res["note"] = "No offline Latin model exists in Argos Translate. Detection and word breaks still work."
        return res
    try:
        import argostranslate.translate as tr
        res["translation"] = tr.translate(spaced.lower(), source, target)
    except Exception as exc:
        res["note"] = f"No installed {source}->{target} model ({exc})."
    return res
