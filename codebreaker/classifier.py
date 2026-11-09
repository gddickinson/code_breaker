"""Neural cipher-type classifier: a small CNN over ciphertext characters, trained on synthetic data."""
import json
import random
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import accel
from .ciphers import REGISTRY
from .languages import MODELS, corpus_text
from .text import letters

EXCLUDE = {"running", "book"}  # need a whole key book per message, and are numeric lists anyway
CLASSES = sorted(k for k, c in REGISTRY.items() if not c.modern and c.keygen and k not in EXCLUDE) + ["plaintext"]
VOCAB = {c: i + 1 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .-+/")}
MAX_LEN = 480
PATH = MODELS / "classifier.pt"
_TEXT = {}


def encode(text: str) -> np.ndarray:
    ids = [VOCAB.get(c.upper(), 0) for c in text[:MAX_LEN]]
    return np.array(ids + [0] * (MAX_LEN - len(ids)), dtype=np.int64)


def sample_text(r) -> str:
    if "en" not in _TEXT:
        _TEXT["en"] = letters(corpus_text("en"))
    return _TEXT["en"][(s := r.randrange(5000, len(_TEXT["en"]) - 1000)): s + r.randint(90, 420)]


def make_one(cls: str, r) -> str:
    plain = sample_text(r)
    if cls == "plaintext":
        return plain
    c = REGISTRY[cls]
    return c.encrypt(plain, **c.keygen(r))


def _batch(a):
    cls, n, seed = a
    r, out = random.Random(seed), []
    for _ in range(n):
        try:
            out.append(encode(make_one(cls, r)))
        except (ValueError, KeyError, IndexError):
            continue
    return CLASSES.index(cls), out


def dataset(per_class: int, seed: int, workers: int = 6):
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_batch, [(c, per_class, seed + i) for i, c in enumerate(CLASSES)]))
    x = np.array([s for _, b in res for s in b])
    y = np.array([i for i, b in res for _ in b], dtype=np.int64)
    return x, y


def build_model(n_classes: int):
    import torch.nn as nn

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(len(VOCAB) + 1, 32, padding_idx=0)
            self.conv = nn.Sequential(nn.Conv1d(32, 128, 5, padding=2), nn.BatchNorm1d(128), nn.ReLU(), nn.MaxPool1d(2),
                                      nn.Conv1d(128, 192, 5, padding=2), nn.BatchNorm1d(192), nn.ReLU(), nn.MaxPool1d(2),
                                      nn.Conv1d(192, 256, 3, padding=1), nn.BatchNorm1d(256), nn.ReLU())
            self.out = nn.Sequential(nn.Dropout(0.25), nn.Linear(512, n_classes))

        def forward(self, x):
            h = self.conv(self.emb(x).transpose(1, 2))
            return self.out(__import__("torch").cat([h.mean(2), h.max(2)[0]], 1))

    return Net()


def train(x, y, device: str, epochs: int = 14, batch: int = 128, seed: int = 0):
    import torch

    torch.manual_seed(seed)
    net = build_model(len(CLASSES)).to(device)
    opt = torch.optim.AdamW(net.parameters(), 2e-3, weight_decay=1e-4)
    steps = max(len(x) // batch, 1)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-3, total_steps=epochs * steps)
    tx, ty = torch.as_tensor(x, device=device), torch.as_tensor(y, device=device)
    net.train()
    t0 = time.perf_counter()
    for _ in range(epochs):
        order = torch.randperm(len(tx), device=device)
        for i in range(steps):
            idx = order[i * batch:(i + 1) * batch]
            loss = torch.nn.functional.cross_entropy(net(tx[idx]), ty[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
    return net, time.perf_counter() - t0


def predict_logits(net, x, device, batch=256):
    import torch

    net.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(x), batch):
            out.append(net(torch.as_tensor(x[i:i + batch], device=device)).cpu())
    return torch.cat(out).numpy()


def evaluate(net, x, y, device) -> dict:
    logits = predict_logits(net, x, device)
    order = np.argsort(-logits, axis=1)
    fam = np.array([REGISTRY[c].family if c in REGISTRY else "plaintext" for c in CLASSES])
    per = {CLASSES[c]: round(float((order[y == c, 0] == c).mean()), 3) for c in range(len(CLASSES)) if (y == c).any()}
    return {"top1": round(float((order[:, 0] == y).mean()), 4), "top3": round(float((order[:, :3] == y[:, None]).any(1).mean()), 4), "family": round(float((fam[order[:, 0]] == fam[y]).mean()), 4), "per_class": per}


def save(net):
    import torch

    PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state": {k: v.cpu() for k, v in net.state_dict().items()}, "classes": CLASSES}, PATH)


_CACHE = {}


def load():
    import torch

    if "net" not in _CACHE:
        if not PATH.exists():
            return None
        ck = torch.load(PATH, map_location="cpu", weights_only=True)
        if ck["classes"] != CLASSES:
            return None  # the roster changed, so the saved model no longer applies
        net = build_model(len(CLASSES))
        net.load_state_dict(ck["state"])
        net.eval()
        _CACHE["net"] = net
    return _CACHE["net"]


def classify(text: str, top: int = 5) -> list[dict] | None:
    """Ranked cipher guesses with probabilities, or None when no trained model is available."""
    net = load()
    if net is None:
        return None
    import torch

    with torch.no_grad():
        p = torch.softmax(net(torch.as_tensor(encode(text)[None])), 1)[0].numpy()
    return [{"id": CLASSES[i], "name": REGISTRY[CLASSES[i]].name if CLASSES[i] in REGISTRY else "Plain text", "probability": round(float(p[i]), 3)} for i in np.argsort(-p)[:top]]
