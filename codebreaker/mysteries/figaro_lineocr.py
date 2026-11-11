"""A line reader for the Le Figaro cipher ads (Round 88b): CNN with 1-D convolutions along the line and CTC, letters and digits only.

Trained first on synthetic lines (figaro_lineocr_data.render), then fine-tuned on real lines from the scans whose
labels come from the by-eye transcriptions: each line's Tesseract reading with the stretch matching the transcription
replaced by the transcription itself (silver labels: the plain words around a cipher are read well by Tesseract, the
cipher is not). Ads are split into training and held-out sets by a hash of the file name; the score is the character
error rate of the transcription as found in each reader's output (figaro_lineocr_data.cer)."""
import random
import subprocess
import zlib

import cv2
import numpy as np
import torch
from torch import nn

from . import figaro_lineocr_data as D
from ..languages import ROOT

MODEL = ROOT / "data/models/figaro_lines.pt"
N_CLASSES = len(D.ALPHABET) + 1  # 0 is the CTC blank


def device():
    return torch.device("mps" if torch.backends.mps.is_available() else "cpu")


class CRNN(nn.Module):
    def __init__(self):
        super().__init__()
        c = lambda i, o: nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU())
        self.cnn = nn.Sequential(c(1, 32), nn.MaxPool2d(2), c(32, 64), nn.MaxPool2d(2), c(64, 128), c(128, 128), nn.MaxPool2d((2, 1)),
                                 c(128, 192), nn.MaxPool2d((2, 1)), c(192, 192), nn.MaxPool2d((2, 1)))  # height 32 -> 1, width /4
        k = lambda i, o: nn.Sequential(nn.Conv1d(i, o, 5, padding=2), nn.BatchNorm1d(o), nn.ReLU())
        self.seq = nn.Sequential(k(192, 256), nn.Dropout(0.15), k(256, 256), k(256, 256))  # context along the line (a GRU was 4x slower on MPS)
        self.out = nn.Conv1d(256, N_CLASSES, 1)

    def forward(self, x):  # x: (B, 1, 32, W) -> (B, W/4, classes)
        return self.out(self.seq(self.cnn(x).squeeze(2))).permute(0, 2, 1)


def held_out(name: str) -> bool:
    return zlib.crc32(name.encode()) % 10 < 3  # 30% of ads, fixed by file name


def batch(images: list[np.ndarray]) -> torch.Tensor:
    xs = [D.to_input(i) for i in images]
    w = max(x.shape[1] for x in xs)
    w += (-w) % 4
    return torch.tensor(np.stack([np.pad(x, ((0, 0), (0, w - x.shape[1]))) for x in xs]))[:, None]


def decode(logits: torch.Tensor) -> list[str]:
    out = []
    for seq in logits.argmax(-1).cpu().numpy():
        s, prev = [], 0
        for k in seq:
            if k != prev and k != 0:
                s.append(D.ALPHABET[k - 1])
            prev = k
        out.append("".join(s))
    return out


def _step(net, opt, ctc, images, labels, dev):
    x = batch(images).to(dev)
    logp = net(x).log_softmax(-1).permute(1, 0, 2)  # (T, B, C)
    targets = torch.tensor([D.ALPHABET.index(c) + 1 for l in labels for c in l], dtype=torch.long)
    loss = ctc(logp.cpu(), targets, torch.full((len(images),), logp.shape[0], dtype=torch.long), torch.tensor([len(l) for l in labels]))
    opt.zero_grad()
    loss.backward()
    nn.utils.clip_grad_norm_(net.parameters(), 5.0)
    opt.step()
    return float(loss.detach())


def train_synthetic(steps: int = 6000, bs: int = 48, seed: int = 88, log=print) -> CRNN:
    rnd, dev = random.Random(seed), device()
    torch.manual_seed(seed)
    words = D.french_words()
    net = CRNN().to(dev)
    opt = torch.optim.AdamW(net.parameters(), 1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 1e-3, total_steps=steps)
    ctc = nn.CTCLoss(blank=0, zero_infinity=True)
    for it in range(steps):
        texts = [D.synthetic_text(rnd, words) for _ in range(bs)]
        imgs = [D.render(t, rnd) for t in texts]
        keep = [(i, D.norm(t)) for i, t in zip(imgs, texts) if D.norm(t)]
        loss = _step(net, opt, ctc, [k[0] for k in keep], [k[1] for k in keep], dev)
        sched.step()
        if it % 500 == 0:
            log(f"synthetic step {it} loss {loss:.3f}")
    return net


def tesseract_line(img: np.ndarray) -> str:
    big = cv2.copyMakeBorder(cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC), 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
    r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "7", "-l", "eng"], input=cv2.imencode(".png", big)[1].tobytes(), capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "ignore").strip()


def silver_labels(name: str, truth: str) -> list[tuple[np.ndarray, str]]:
    """(line image, label) for one ad: Tesseract's reading of each line, with the stretch that matches the transcription
    (located over all lines together) replaced by the transcription itself, cut back at the line boundaries."""
    lines = D.cut_lines(D.gray(D.IMAGES / name))
    reads = [D.norm(tesseract_line(l)) for l in lines]
    joined = "".join(reads)
    if not joined:
        return []
    edits, a, b = D.local_align(truth, joined)
    if edits > 0.6 * len(truth):  # the transcription is not found in this reading: no labels from this ad
        return []
    label = joined[:a] + truth + joined[b:]
    out, pos, shift = [], 0, len(truth) - (b - a)
    for img, r in zip(lines, reads):  # line boundaries in the label: before a they stay, after b they move by shift
        end = pos + len(r)
        e2 = end if end <= a else (end + shift if end >= b else min(len(label), a + int((end - a) * len(truth) / max(b - a, 1))))
        start = pos if pos <= a else (pos + shift if pos >= b else a + int((pos - a) * len(truth) / max(b - a, 1)))
        piece = label[start:e2]
        if len(piece) >= 4:
            out.append((img, piece))
        pos = end
    return out


def finetune(net: CRNN, pairs: list[tuple[np.ndarray, str]], steps: int = 1500, bs: int = 16, seed: int = 88, mix: float = 0.5, log=print) -> CRNN:
    """Real lines mixed with synthetic ones, so the reader does not forget general shapes."""
    rnd, dev = random.Random(seed), device()
    words = D.french_words()
    opt = torch.optim.AdamW(net.parameters(), 3e-4, weight_decay=1e-4)
    ctc = nn.CTCLoss(blank=0, zero_infinity=True)
    net.train()
    for it in range(steps):
        real = rnd.sample(pairs, min(len(pairs), int(bs * mix)))
        syn = [(D.render(t, rnd), D.norm(t)) for t in (D.synthetic_text(rnd, words) for _ in range(bs - len(real)))]
        both = [p for p in real + syn if p[1]]
        loss = _step(net, opt, ctc, [p[0] for p in both], [p[1] for p in both], dev)
        if it % 300 == 0:
            log(f"fine-tune step {it} loss {loss:.3f}")
    return net


@torch.no_grad()
def read_lines(net: CRNN, lines: list[np.ndarray]) -> list[str]:
    net.eval()
    dev = next(net.parameters()).device
    return [decode(net(batch([l]).to(dev)))[0] for l in lines] if lines else []


def load() -> CRNN:
    net = CRNN()
    net.load_state_dict(torch.load(MODEL, map_location="cpu"))
    return net.to(device()).eval()
