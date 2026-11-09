"""Offline translation via Argos Translate models, plus language detection for solved text."""
from .languages import LANGS, detect
from .segment import segment

ARGOS = {"fr", "de", "it", "es"}
LATIN_MODEL = "Helsinki-NLP/opus-mt-mul-en"
LATIN_NOTE = "Rough machine draft. On Caesar, this model shares about 42% of its words with a published translation. Do not treat it as proof that a decryption is meaningful."
_LATIN = {}


def latin_to_english(text: str) -> str | None:
    """Translate Latin sentence by sentence with a general multi-language model."""
    import re

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        if "m" not in _LATIN:
            _LATIN["t"] = AutoTokenizer.from_pretrained(LATIN_MODEL, local_files_only=True)
            _LATIN["m"] = AutoModelForSeq2SeqLM.from_pretrained(LATIN_MODEL, local_files_only=True).eval()
    except (ImportError, OSError):
        return None
    parts = [x.strip() for x in re.split(r"(?<=[.;:!?])\s+", text.lower()) if x.strip()]
    pieces = [" ".join(p.split()[i:i + 40]) for p in parts for i in range(0, len(p.split()), 40)]
    out = []
    for i in range(0, len(pieces), 8):
        x = _LATIN["t"](pieces[i:i + 8], return_tensors="pt", padding=True, truncation=True, max_length=256)
        out += _LATIN["t"].batch_decode(_LATIN["m"].generate(**x, max_new_tokens=120, num_beams=2), skip_special_tokens=True)
    return " ".join(out)


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
        res["translation"] = latin_to_english(spaced)
        res["note"] = LATIN_NOTE if res["translation"] else "The Latin model is not installed. Run scripts/install_translation_models.py."
        return res
    try:
        import argostranslate.translate as tr
        res["translation"] = tr.translate(spaced.lower(), source, target)
    except Exception as exc:
        res["note"] = f"No installed {source}->{target} model ({exc})."
    return res
