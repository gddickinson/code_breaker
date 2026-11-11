"""Optional models for the Lens and language identification (Rounds 90b and 93), with source, licence and size.
None is redistributed with the app; each is fetched only when this script is run. Usage: python scripts/fetch_tools.py [names]"""
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {
    "fasttext": ("https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz", "data/models/fasttext/lid.176.ftz", "CC BY-SA 3.0", 938013,
                 "8f3472cfe8738a7b6099e8e999c3cbfae0dcd15696aac7d7738a8039db603e83", "fastText language identification, 176 languages (needs pip install fasttext-predict)"),
    "mobilenet": ("https://github.com/onnx/models/raw/main/validated/vision/classification/mobilenet/model/mobilenetv2-12.onnx", "data/models/objects/mobilenetv2-12.onnx",
                  "Apache-2.0", 13964571, "c0c3f76d93fa3fd6580652a45618618a220fced18babf65774ed169de0432ad5", "MobileNetV2 ImageNet classifier, the Lens's classical object fallback"),
    "tessbest": ("https://github.com/tesseract-ocr/tessdata_best/raw/main/script/Latin.traineddata", "data/models/tessdata_best/script/Latin.traineddata", "Apache-2.0",
                 101402885, "cf7216998bf7f363f18e3def04cc6b28ae954d2a5a3bdad09f743c9d3538ef35", "Tesseract 'best' Latin script model, only for repeating the Round 93 comparison (not used by the Lens)"),
    "paddle_arabic": ("https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/rec/arabic_PP-OCRv4_rec_mobile.onnx", "data/models/paddle_rec/arabic_PP-OCRv4_rec_mobile.onnx", "Apache-2.0", 7685206, "4a9011bef71687bb84288dc86ad2471bd5d37b717ddf672dd156f9e7a5601bac", "PaddleOCR arabic recogniser (RapidAI ONNX), for the Lens"),
    "paddle_arabic_dict": ("https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/paddle/PP-OCRv4/rec/arabic_PP-OCRv4_rec_mobile/arabic_dict.txt", "data/models/paddle_rec/arabic_dict.txt", "Apache-2.0", 405, "637c27c88512c22089bef927b34ada08f748dc132ac70facd68d8202384c2726", "PaddleOCR arabic recogniser character list (RapidAI ONNX), for the Lens"),
    "paddle_cyrillic": ("https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/rec/cyrillic_PP-OCRv3_rec_mobile.onnx", "data/models/paddle_rec/cyrillic_PP-OCRv3_rec_mobile.onnx", "Apache-2.0", 8972413, "1efb65bdc460af1c0e8733d005b20952b17ca5aac10ddb56c968333791c5eaa3", "PaddleOCR cyrillic recogniser (RapidAI ONNX), for the Lens"),
    "paddle_cyrillic_dict": ("https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/paddle/PP-OCRv4/rec/cyrillic_PP-OCRv3_rec_mobile/cyrillic_dict.txt", "data/models/paddle_rec/cyrillic_dict.txt", "Apache-2.0", 410, "369a82c6c8c479784a5d726448b83b1eafb5fef0a4129a5eaa3929625ddcd132", "PaddleOCR cyrillic recogniser character list (RapidAI ONNX), for the Lens"),
    "paddle_devanagari": ("https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/rec/devanagari_PP-OCRv4_rec_mobile.onnx", "data/models/paddle_rec/devanagari_PP-OCRv4_rec_mobile.onnx", "Apache-2.0", 7688213, "a62b6148303187907aa0b0d3a0125bdc62557d07966468cab9056949e36035e8", "PaddleOCR devanagari recogniser (RapidAI ONNX), for the Lens"),
    "paddle_devanagari_dict": ("https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/paddle/PP-OCRv4/rec/devanagari_PP-OCRv4_rec_mobile/devanagari_dict.txt", "data/models/paddle_rec/devanagari_dict.txt", "Apache-2.0", 508, "b5f1be6d8bbff1a19fb96c5d4ca96a423380234bb7d2ce0e07b5838adb4d18ea", "PaddleOCR devanagari recogniser character list (RapidAI ONNX), for the Lens"),
    "paddle_japan": ("https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/rec/japan_PP-OCRv4_rec_mobile.onnx", "data/models/paddle_rec/japan_PP-OCRv4_rec_mobile.onnx", "Apache-2.0", 9753335, "e1075a67dba758ecfc7ebc78a10ae61c95ac8fb66a9c86fab5541e33f085cb7a", "PaddleOCR japan recogniser (RapidAI ONNX), for the Lens"),
    "paddle_japan_dict": ("https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/paddle/PP-OCRv4/rec/japan_PP-OCRv4_rec_mobile/japan_dict.txt", "data/models/paddle_rec/japan_dict.txt", "Apache-2.0", 17332, "1dcfcb41eec90576a945b3084f22ade11ced506e24f14879245b071698f308e8", "PaddleOCR japan recogniser character list (RapidAI ONNX), for the Lens"),
    "paddle_korean": ("https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/rec/korean_PP-OCRv4_rec_mobile.onnx", "data/models/paddle_rec/korean_PP-OCRv4_rec_mobile.onnx", "Apache-2.0", 24067780, "ab151ba9065eccd98f884cf4d927db091be86137276392072edd4f9d43ad7426", "PaddleOCR korean recogniser (RapidAI ONNX), for the Lens"),
    "paddle_korean_dict": ("https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/paddle/PP-OCRv4/rec/korean_PP-OCRv4_rec_mobile/korean_dict.txt", "data/models/paddle_rec/korean_dict.txt", "Apache-2.0", 14480, "aa1fdc8ae8f7cd40a0ec4edb472eb0421e11427e6ccfee9915440742c18b0a20", "PaddleOCR korean recogniser character list (RapidAI ONNX), for the Lens"),
    "synset": ("https://raw.githubusercontent.com/onnx/models/main/validated/vision/classification/synset.txt", "data/models/objects/synset.txt", "Apache-2.0", 31675, None,
               "ImageNet class names for MobileNetV2"),
}


def fetch(name: str) -> None:
    url, dest, licence, size, sha, what = TOOLS[name]
    out = ROOT / dest
    if out.exists() and out.stat().st_size == size:
        print(f"{name}: present ({what})")
        return
    print(f"{name}: {what}; {licence}; {size / 1e6:.1f} MB from {url}")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "code-breaker/1.0"}), timeout=300).read()
    if sha and hashlib.sha256(data).hexdigest() != sha:
        raise SystemExit(f"{name}: checksum does not match; not saved")
    out.write_bytes(data)


if __name__ == "__main__":
    for n in sys.argv[1:] or ["fasttext", "mobilenet", "synset"]:  # comparison-only models (tessbest, paddle_*) only when named
        fetch(n)
