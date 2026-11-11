"""Glyph recogniser (Round 78): a small CNN over every drawn sign of the supported scripts, trained on the GPU.

Training: distorted copies of each sign, 30% of them from the 'hard' ranges (after the first model scored 13-27% top-1
on hard copies it never saw; so 'hard' is no longer an independent test). Reported, not tuned on: top-1 and top-5 per
script on held-out normal and hard copies, and on 'unseen' copies (perspective, uneven lighting, motion blur, JPEG)
of a kind never used in training or design; and the model's confidence on pure noise, which sets the
'no confident match' threshold the scanner shows. The model is saved in data/models (rebuilt, not committed)."""
import json
import time

import numpy as np
import torch
from torch import nn

from ..languages import ROOT
from .glyph_render import SIZE, classes, dataset_parallel, prep

PATH = ROOT / "data/models/glyphs.pt"
RESULT = ROOT / "data/results/glyph_model.json"


def device() -> str:
    return "mps" if torch.backends.mps.is_available() else "cpu"


def build(n: int) -> nn.Module:
    def block(i, o):
        return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(), nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(), nn.MaxPool2d(2))
    return nn.Sequential(block(1, 48), block(48, 96), block(96, 192), block(192, 256), nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Dropout(0.3), nn.Linear(256, n))


def _tensor(x: np.ndarray, dev: str) -> torch.Tensor:
    return torch.as_tensor(x, device=dev).float().div(255.0).unsqueeze(1)


def train(per_class: int = 40, epochs: int = 12, batch: int = 256, seed: int = 78) -> dict:
    torch.manual_seed(seed)
    dev, cls = device(), classes()
    t0 = time.time()
    x, y = dataset_parallel(per_class, seed, "train")
    net = build(len(cls)).to(dev)
    opt = torch.optim.AdamW(net.parameters(), 2e-3, weight_decay=1e-4)
    steps = epochs * ((len(x) + batch - 1) // batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-3, total_steps=steps)
    tx, ty = torch.as_tensor(x, device=dev), torch.as_tensor(y, device=dev)
    lossf = nn.CrossEntropyLoss(label_smoothing=0.05)
    for ep in range(epochs):
        net.train()
        order = torch.randperm(len(tx), device=dev)
        total = 0.0
        for i in range(0, len(tx), batch):
            idx = order[i:i + batch]
            loss = lossf(net(tx[idx].float().div(255.0).unsqueeze(1)), ty[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            total += loss.item() * len(idx)
        print(f"epoch {ep + 1}: loss {total / len(tx):.3f} ({time.time() - t0:.0f} s)", flush=True)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state": {k: v.cpu() for k, v in net.state_dict().items()}, "n": len(cls), "signs": ["".join(c["signs"]) for c in cls]}, PATH)
    return {"classes": len(cls), "train_images": len(x), "epochs": epochs, "seconds": round(time.time() - t0)}


_NET = None


def load() -> nn.Module | None:
    global _NET
    if _NET is None and PATH.exists():
        ck = torch.load(PATH, map_location="cpu")
        if ck["signs"] != ["".join(c["signs"]) for c in classes()]:
            return None  # the sign tables or fonts changed since training
        _NET = build(ck["n"])
        _NET.load_state_dict(ck["state"])
        _NET.eval().to(device())
    return _NET


def probabilities(images: np.ndarray, batch: int = 512) -> np.ndarray:
    net, dev, out = load(), device(), []
    with torch.no_grad():
        for i in range(0, len(images), batch):
            out.append(torch.softmax(net(_tensor(images[i:i + batch], dev)), 1).cpu().numpy())
    return np.concatenate(out)


def evaluate(per_class: int = 5) -> dict:
    cls = classes()
    scripts = np.array([c["script"] for c in cls])
    res = {}
    for name, kind, seed in (("held_out", "normal", 9001), ("hard", "hard", 9002), ("unseen", "unseen", 9003)):
        x, y = dataset_parallel(per_class, seed, kind)
        p = probabilities(np.stack([prep(a) for a in x]))
        top5 = np.argsort(-p, 1)[:, :5]
        hit1, hit5 = top5[:, 0] == y, (top5 == y[:, None]).any(1)
        res[name] = {"top1": round(float(hit1.mean()), 3), "top5": round(float(hit5.mean()), 3),
                     "script_from_top1": round(float((scripts[top5[:, 0]] == scripts[y]).mean()), 3),
                     "by_script": {s: {"top1": round(float(hit1[scripts[y] == s].mean()), 3), "top5": round(float(hit5[scripts[y] == s].mean()), 3)}
                                   for s in sorted(set(scripts))}}
        if name == "held_out":
            res[name]["confidence_correct_median"] = round(float(np.median(p.max(1)[hit1])), 3)
    rnd = np.random.default_rng(78)
    noise = np.clip(rnd.normal(30, 40, (500, SIZE, SIZE)), 0, 255).astype(np.uint8)
    blobs = np.stack([np.clip(np.kron(rnd.random((6, 6)) > 0.6, np.ones((8, 8))) * 255 + rnd.normal(0, 20, (SIZE, SIZE)), 0, 255) for _ in range(500)]).astype(np.uint8)
    pn = probabilities(np.stack([prep(a) for a in np.concatenate([noise, blobs])])).max(1)
    res["noise"] = {"max_prob_median": round(float(np.median(pn)), 3), "max_prob_p99": round(float(np.quantile(pn, 0.99)), 3)}
    res["threshold"] = res["noise"]["max_prob_p99"]
    return res


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["evaluate"]:  # re-measure the saved model
        old = json.loads(RESULT.read_text())
        res = {**{k: old[k] for k in ("classes", "train_images", "epochs", "seconds") if k in old}, "id": "glyph_model", **evaluate()}
        RESULT.write_text(json.dumps(res, indent=1))
        print(json.dumps({k: (v if not isinstance(v, dict) else {a: b for a, b in v.items() if a != "by_script"}) for k, v in res.items()}, indent=1))
        raise SystemExit
    info = train()
    res = {"id": "glyph_model", **info, **evaluate()}
    RESULT.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "by_script"}, indent=1))
