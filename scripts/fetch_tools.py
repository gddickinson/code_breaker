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
    for n in sys.argv[1:] or [k for k in TOOLS if k != "tessbest"]:  # the 101 MB comparison model only when named
        fetch(n)
