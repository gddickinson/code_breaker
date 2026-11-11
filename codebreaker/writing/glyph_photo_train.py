"""Teaching the glyph recogniser real carvings (Round 79): fine-tuning on photographed hieroglyphs, tested on
photographs it never saw.

The font-trained recogniser read 1.6% of Pyramid of Unas photographs correctly (photo_eval.py): carvings are filled,
worn, small and in another hand than the Noto font. Here the photographs (Franken and van Gemert's dataset, Manual/Raw)
are split by source picture: every sign of the TEST_PICTURES is held out. The model is fine-tuned from its font
weights on the other pictures' signs (augmented: rotation, scale, blur, noise, contrast) mixed with font drawings of
every script, so the other scripts are not forgotten. Reported before and after: held-out photographs (top-1, top-5
among Egyptian signs) and the font test (top-1 on held-out drawings). The new weights replace the old only if the
photographs improve and the font test drops by less than one point; the old model is kept as glyphs_font.pt."""
import json
import re
import shutil
import zipfile

import cv2
import numpy as np
import torch
from torch import nn

from ..languages import ROOT
from . import glyph_model as M
from .glyph_render import classes, dataset_parallel, fit, prep
from .photo_eval import ZIP

RESULT = ROOT / "data/results/glyph_photo_train.json"
TEST_PICTURES = ("9", "41")


def photos() -> list[tuple[str, str, np.ndarray]]:
    z = zipfile.ZipFile(ZIP)
    out = []
    for n in sorted(x for x in z.namelist() if x.startswith("Dataset/Manual/Raw/") and x.endswith(".png")):
        pic, code = n.split("/")[3], re.sub(r"\.png$", "", n.rsplit("/", 1)[-1]).split("_")[-1]
        img = cv2.imdecode(np.frombuffer(z.read(n), np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is not None and code != "UNKNOWN":
            out.append((pic, code, img))
    return out


def view(img: np.ndarray) -> np.ndarray:
    return prep(fit(255 - img))  # carvings are darker than the stone; the recogniser wants bright ink


def augment(img: np.ndarray, rnd: np.random.Generator) -> np.ndarray:
    h, w = img.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), float(rnd.uniform(-10, 10)), float(rnd.uniform(0.85, 1.15)))
    a = cv2.warpAffine(img, m, (w, h), borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    a = cv2.GaussianBlur(a, (0, 0), float(rnd.uniform(0.1, 1.2))) * rnd.uniform(0.7, 1.3) + rnd.uniform(-25, 25)
    return view(np.clip(a + rnd.normal(0, 6, a.shape), 0, 255).astype(np.uint8))


def score(net, x, y, mask=None) -> tuple[float, float]:
    M._NET = net
    p = M.probabilities(x)
    if mask is not None:
        p = p * mask
    top = np.argsort(-p, 1)[:, :5]
    return round(float((top[:, 0] == y).mean()), 3), round(float((top == y[:, None]).any(1).mean()), 3)


def run(epochs: int = 5, copies: int = 8, seed: int = 79) -> dict:
    rnd, cls, dev = np.random.default_rng(seed), classes(), M.device()
    index = {c["code"]: k for k, c in enumerate(cls) if c["script"] == "egyptian" and c["code"]}
    egy = np.array([c["script"] == "egyptian" for c in cls])
    data = [(pic, index[c], img) for pic, c, img in photos() if c in index]
    train = [(k, img) for pic, k, img in data if pic not in TEST_PICTURES]
    test = [(k, img) for pic, k, img in data if pic in TEST_PICTURES]
    tx, ty = np.stack([view(img) for _, img in test]), np.array([k for k, _ in test])
    fx, fy = dataset_parallel(3, 9001, "normal")
    base = M.load()
    before = {"photos_top1_top5": score(base, tx, ty, egy), "font_top1": score(base, fx, fy)[0]}
    px = np.stack([augment(img, rnd) for k, img in train for _ in range(copies)])
    py = np.array([k for k, _ in train for _ in range(copies)])
    gx, gy = dataset_parallel(10, seed, "train")
    x, y = np.concatenate([px, gx]), np.concatenate([py, gy])
    net = M.build(len(cls)).to(dev)
    net.load_state_dict({k: v.to(dev) for k, v in base.state_dict().items()})
    opt = torch.optim.AdamW(net.parameters(), 5e-4, weight_decay=1e-4)
    lossf, X, Y = nn.CrossEntropyLoss(label_smoothing=0.05), torch.as_tensor(x, device=dev), torch.as_tensor(y, device=dev)
    for ep in range(epochs):
        net.train()
        order = torch.randperm(len(X), device=dev)
        for i in range(0, len(X), 256):
            idx = order[i:i + 256]
            loss = lossf(net(X[idx].float().div(255.0).unsqueeze(1)), Y[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
        print(f"epoch {ep + 1}: loss {loss.item():.3f}", flush=True)
    net.eval()
    after = {"photos_top1_top5": score(net, tx, ty, egy), "font_top1": score(net, fx, fy)[0]}
    keep = after["photos_top1_top5"][1] > before["photos_top1_top5"][1] and after["font_top1"] >= before["font_top1"] - 0.01
    if keep:
        shutil.copy(M.PATH, M.PATH.with_name("glyphs_font.pt"))
        torch.save({"state": {k: v.cpu() for k, v in net.state_dict().items()}, "n": len(cls), "signs": ["".join(c["signs"]) for c in cls]}, M.PATH)
    M._NET = None
    return {"id": "glyph_photo_train", "test_pictures": TEST_PICTURES, "train_photos": len(train), "test_photos": len(test),
            "test_labels_unseen_in_train": len({k for k, _ in test} - {k for k, _ in train}), "before": before, "after": after, "replaced_model": keep}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))
