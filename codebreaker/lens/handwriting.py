"""Handwriting reading with TrOCR (Round 93c), optional: microsoft/trocr-small-handwritten (MIT, about 246 MB, trained
on the IAM handwritten English lines), cached in data/models/trocr (not committed). One line image in, its text out.
Compared with Tesseract and the vision model in handwriting_eval.py: TrOCR decodes with a language model inside, so on
nonsense (cipher-like) letters it tends to write words that are not there."""
from functools import lru_cache

import numpy as np

from ..languages import ROOT

CACHE = ROOT / "data/models/trocr"
NAME = "microsoft/trocr-small-handwritten"


def available() -> bool:
    return any(CACHE.glob("models--microsoft--trocr-small-handwritten/snapshots/*/config.json"))


@lru_cache(maxsize=1)
def _model():
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    p = TrOCRProcessor.from_pretrained(NAME, cache_dir=str(CACHE), local_files_only=True)
    m = VisionEncoderDecoderModel.from_pretrained(NAME, cache_dir=str(CACHE), local_files_only=True).eval()
    return p, m


def read_line(img: np.ndarray) -> str:
    if not available():
        return ""
    import torch
    from PIL import Image

    p, m = _model()
    rgb = Image.fromarray(img).convert("RGB")
    with torch.no_grad():
        ids = m.generate(p(images=rgb, return_tensors="pt").pixel_values, max_new_tokens=64)
    return p.batch_decode(ids, skip_special_tokens=True)[0]
