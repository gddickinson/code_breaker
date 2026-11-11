"""PaddleOCR PP-OCRv4 recognisers for other scripts through RapidOCR (Round 93b).

Models: RapidAI's ONNX conversions of PaddleOCR's mobile recognisers (Apache-2.0), from modelscope.cn/models/RapidAI/
RapidOCR, in data/models/paddle_rec (not committed; scripts/fetch_tools.py): Arabic, Cyrillic (PP-OCRv3), Devanagari,
Japanese, Korean, each with its character list. RapidOCR's own detector finds the lines; the script's recogniser reads
them. Compared with Tesseract and the vision model in scripts_ocr_eval.py."""
from functools import lru_cache

import cv2
import numpy as np

from ..languages import ROOT

DIR = ROOT / "data/models/paddle_rec"
MODELS = {"Arabic": ("arabic_PP-OCRv4_rec_mobile.onnx", "arabic_dict.txt"), "Cyrillic": ("cyrillic_PP-OCRv3_rec_mobile.onnx", "cyrillic_dict.txt"),
          "Devanagari": ("devanagari_PP-OCRv4_rec_mobile.onnx", "devanagari_dict.txt"), "Japanese": ("japan_PP-OCRv4_rec_mobile.onnx", "japan_dict.txt"),
          "Hangul": ("korean_PP-OCRv4_rec_mobile.onnx", "korean_dict.txt")}


def available(script: str) -> bool:
    return script in MODELS and (DIR / MODELS[script][0]).exists()


@lru_cache(maxsize=None)
def _engine(script: str):
    from rapidocr_onnxruntime import RapidOCR

    model, keys = MODELS[script]
    return RapidOCR(rec_model_path=str(DIR / model), rec_keys_path=str(DIR / keys))


def lines(img: np.ndarray, script: str) -> list[tuple]:
    """[(box points, text, confidence)] read with the script's recogniser; [] if it is not installed."""
    if not available(script):
        return []
    rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img
    res, _ = _engine(script)(rgb)
    return [(r[0], r[1], float(r[2])) for r in res] if res else []


def read_line(img: np.ndarray, script: str) -> str:
    """One line already cut out (a live line, a Tesseract line box): the recogniser alone. RapidOCR's detector, trained
    on Chinese, breaks Devanagari lines apart at the headline, so for line images it is skipped."""
    if not available(script):
        return ""
    rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img
    res, _ = _engine(script)(rgb, use_det=False, use_cls=False)
    return res[0][0] if res else ""


def read(img: np.ndarray, script: str) -> str:
    ls = lines(img, script)
    rtl = script == "Arabic"
    ls = sorted(ls, key=lambda r: min(p[0] for p in r[0]), reverse=rtl)
    return " ".join(r[1] for r in ls)
