"""The font-trained glyph recogniser on real photographs (Round 79): Egyptian hieroglyphs from the Pyramid of Unas.

Data: Franken and van Gemert's hieroglyph dataset (GlyphDataset.zip from the authors' site, the accompanying code under
the MIT licence; downloaded with the user's permission into data/models/glyph_photos, not committed). The 'Manual/Raw'
part holds 4,210 photographed signs labelled with Gardiner codes. Signs are read straight from the zip. Carved signs
may be darker or lighter than the stone, so three inputs are compared: the crop as is, inverted, and the average of the
two views' probabilities. Reported: top-1 and top-5 among Egyptian signs, for labels the recogniser knows."""
import json
import re
import zipfile
from collections import Counter

import cv2
import numpy as np

from ..languages import ROOT
from .glyph_model import probabilities
from .glyph_render import classes, fit, prep

ZIP = ROOT / "data/models/glyph_photos/GlyphDataset.zip"
RESULT = ROOT / "data/results/glyph_photo_eval.json"


def samples(part: str = "Manual/Raw", limit: int | None = None) -> list[tuple[str, np.ndarray]]:
    z = zipfile.ZipFile(ZIP)
    out = []
    for n in sorted(x for x in z.namelist() if x.startswith(f"Dataset/{part}/") and x.endswith(".png")):
        code = re.sub(r"\.png$", "", n.rsplit("/", 1)[-1]).split("_")[-1]
        img = cv2.imdecode(np.frombuffer(z.read(n), np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is not None and code != "UNKNOWN":
            out.append((code, img))
        if limit and len(out) >= limit:
            break
    return out


def evaluate(limit: int | None = None) -> dict:
    cls = classes()
    code_index = {c["code"]: k for k, c in enumerate(cls) if c["script"] == "egyptian" and c["code"]}
    egy = np.array([c["script"] == "egyptian" for c in cls])
    data = [(code_index[c], img) for c, img in samples(limit=limit) if c in code_index]
    unknown_labels = Counter(c for c, _ in samples(limit=limit) if c not in code_index)
    y = np.array([k for k, _ in data])
    views = {"as is": np.stack([prep(fit(img)) for _, img in data]), "inverted": np.stack([prep(fit(255 - img)) for _, img in data])}
    probs = {k: probabilities(v) * egy for k, v in views.items()}
    probs["both views averaged"] = (probs["as is"] + probs["inverted"]) / 2
    res = {}
    for k, p in probs.items():
        top = np.argsort(-p, 1)[:, :5]
        res[k] = {"top1": round(float((top[:, 0] == y).mean()), 3), "top5": round(float((top == y[:, None]).any(1).mean()), 3)}
    freq = Counter(y.tolist()).most_common(1)[0][1] / len(y)
    return {"id": "glyph_photo_eval", "photos": len(data), "labels_known": len(set(y.tolist())), "labels_not_in_recogniser": dict(unknown_labels.most_common(10)),
            "chance_top1_most_common_sign": round(freq, 3), "results": res,
            "note": "Font-trained recogniser, no photographs in training; Pyramid of Unas photographs (Franken and van Gemert)."}


if __name__ == "__main__":
    r = evaluate()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))
