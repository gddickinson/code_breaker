"""A small character GRU trained on the GPU, used to re-rank candidate decryptions."""
import numpy as np

from . import accel
from .languages import MODELS, ROOT, corpus_text
from .text import to_ints

PATH = MODELS / "en_gru.pt"
_NET = {}


def _corpus():
    extra = [(ROOT / "data/sources" / f).read_text(errors="ignore") for f in ("key_federalist.txt", "key_common_sense.txt")]
    return to_ints(" ".join([corpus_text("en")] + extra)).astype(np.int64)


def build():
    import torch.nn as nn

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(27, 48)
            self.gru = nn.GRU(48, 256, 2, batch_first=True, dropout=0.1)
            self.out = nn.Linear(256, 26)

        def forward(self, x):
            h, _ = self.gru(self.emb(x))
            return self.out(h)

    return Net()


def train(steps=2400, batch=192, win=120, seed=0):
    import torch

    torch.manual_seed(seed)
    dev = accel.device() or "cpu"
    t = torch.as_tensor(_corpus(), device=dev)
    net = build().to(dev)
    opt = torch.optim.AdamW(net.parameters(), 3e-3)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 4e-3, total_steps=steps)
    for i in range(steps):
        idx = torch.randint(0, len(t) - win - 1, (batch,), device=dev)
        seq = torch.stack([t[j:j + win + 1] for j in idx])
        x = torch.cat([torch.full((batch, 1), 26, device=dev), seq[:, :-1]], 1)[:, :win]
        loss = torch.nn.functional.cross_entropy(net(x).reshape(-1, 26), seq[:, :win].reshape(-1))
        opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step(); sched.step()
        if i % 600 == 0:
            print("step", i, round(loss.item(), 3), flush=True)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save({k: v.cpu() for k, v in net.state_dict().items()}, PATH)
    return loss.item()


def scores(texts: list[np.ndarray]) -> list[float]:
    """Mean log-probability per letter for each text of equal length."""
    import torch

    dev = accel.device() or "cpu"
    if "net" not in _NET:
        net = build()
        net.load_state_dict(torch.load(PATH, map_location="cpu", weights_only=True))
        _NET["net"] = net.to(dev).eval()
    net = _NET["net"]
    with torch.no_grad():
        t = torch.as_tensor(np.array(texts), device=dev)
        x = torch.cat([torch.full((len(t), 1), 26, device=dev), t[:, :-1]], 1)
        lp = torch.log_softmax(net(x), -1).gather(2, t.unsqueeze(2)).squeeze(2).mean(1)
    return lp.cpu().tolist()
