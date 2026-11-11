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
    parts = [x.strip() for x in re.split(r"(?<=[.;:!?])\s+", text) if x.strip()]
    parts = [x.capitalize() if x.isupper() else x for x in parts]
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


def cipher_like(text: str) -> bool:
    """Unspaced capital letters, as decrypted cipher output comes: word breaks must be restored first."""
    t = text.strip()
    return bool(t) and " " not in t and t.upper() == t and t.isalpha()


def translate(text: str, source: str | None = None, target: str = "en") -> dict:
    """Ordinary text: identify among about 50 languages (langid), translate with any installed model. Unspaced cipher
    output: the cipher-tuned models of the six classical languages, word breaks restored, then translate."""
    from . import langid

    if cipher_like(text):
        guesses = [{"lang": d["lang"], "name": d["name"], "p": None, "score": d["score"]} for d in detect(text)]
        source = source or guesses[0]["lang"]
        spaced = segment(text.upper(), source)
        lower = True
    else:
        guesses = langid.detect(text)
        source = source or (guesses[0]["lang"] if guesses else "en")
        spaced, lower = text, False
    name = langid.NAMES.get(source, LANGS.get(source, source))
    res = {"source": source, "source_name": name, "detected": guesses, "spaced": spaced, "translation": None, "note": ""}
    if source == target:
        res["note"] = "Text is already in the target language."
        return res
    if source == "la":
        res["translation"] = latin_to_english(spaced)
        res["note"] = LATIN_NOTE if res["translation"] else "The Latin model is not installed. Run scripts/install_translation_models.py."
        return res
    if source not in available():
        res["note"] = f"No {name} to English translator is installed (scripts/install_more_translators.py)."
        return res
    try:
        import argostranslate.translate as tr
        res["translation"] = tr.translate(spaced.lower() if lower else spaced, source, target)
    except Exception as exc:
        res["note"] = f"No installed {source}->{target} model ({exc})."
    return res
