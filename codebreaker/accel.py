"""Optional GPU acceleration (Apple MPS or CUDA) for data-parallel key searches.

Torch is imported lazily and every function has a CPU route, so the app works without it.
`scripts/benchmark_gpu.py` measures which route wins; `best_route` applies those measurements.
"""
import json

import numpy as np

from .languages import ROOT

BENCH = ROOT / "data/results/gpu_benchmark.json"


def device():
    """Best available torch device name, or None if torch is not installed."""
    try:
        import torch
    except ImportError:
        return None
    if torch.backends.mps.is_available():
        return "mps"
    return "cuda" if torch.cuda.is_available() else "cpu"


def best_route(task: str) -> str:
    """'gpu' only when a recorded benchmark showed the GPU to be faster on this machine."""
    if device() not in ("mps", "cuda") or not BENCH.exists():
        return "cpu"
    rec = json.loads(BENCH.read_text()).get(task)
    return "gpu" if rec and rec["gpu_per_s"] > rec["cpu_per_s"] else "cpu"


def _tensor(a, dev, kind=None):
    import torch

    return torch.as_tensor(np.asarray(a), device=dev, dtype=kind or torch.long)


def book_scan(numbers, initials, table, offsets: int, batch: int = 4000) -> np.ndarray:
    """Score a book-cipher decode at every document offset. Same result as kernels.book_offset_scan."""
    import torch

    dev = device()
    nums = _tensor(numbers, dev) - 1
    ini = _tensor(initials, dev)
    tab = _tensor(table, dev, torch.float32)
    n, m, out = len(numbers), len(initials), []
    for start in range(0, offsets, batch):
        off = torch.arange(start, min(start + batch, offsets), device=dev)
        j = nums.unsqueeze(0) + off.unsqueeze(1)
        ok = j < m
        p = ini[j.clamp(max=m - 1)]
        if bool(ok.all()):
            idx = p[:, :-3] * 17576 + p[:, 1:-2] * 676 + p[:, 2:-1] * 26 + p[:, 3:]
            s = tab[idx].sum(1) / max(n - 3, 1)
        else:  # rows with out-of-range numbers: compact them one at a time, as the CPU route does
            vals = []
            for row, mask in zip(p, ok):
                q = row[mask]
                if len(q) < 0.9 * n:
                    vals.append(torch.tensor(-1e18, device=dev, dtype=torch.float32))
                    continue
                ix = q[:-3] * 17576 + q[1:-2] * 676 + q[2:-1] * 26 + q[3:]
                vals.append(tab[ix].sum() / max(len(q) - 3, 1))
            s = torch.stack(vals)
        out.append(s.cpu().numpy())
    return np.concatenate(out)


def enigma_ic_scan(ct, wires, notch, reflector, batch: int = 17576):
    """Index of coincidence for all 17,576 start positions of one rotor order (rings A, no plugs)."""
    import torch

    dev = device()
    grid = np.array(np.meshgrid(np.arange(26), np.arange(26), np.arange(26), indexing="ij")).reshape(3, -1).T
    pos0 = _tensor(grid, dev)
    w = _tensor(wires, dev)
    inv = torch.argsort(w, dim=1)
    refl = _tensor(reflector, dev)
    nt = _tensor(notch, dev)
    t = _tensor(ct, dev)
    counts_all, n = [], len(ct)
    for s in range(0, len(pos0), batch):
        pos = pos0[s:s + batch].clone()
        counts = torch.zeros((len(pos), 26), device=dev, dtype=torch.float32)
        rows = torch.arange(len(pos), device=dev)
        for ch in t:
            mid = pos[:, 1] == nt[1]
            right = (pos[:, 2] == nt[2]) & ~mid
            pos[:, 0] = (pos[:, 0] + mid.long()) % 26
            pos[:, 1] = (pos[:, 1] + (mid | right).long()) % 26
            pos[:, 2] = (pos[:, 2] + 1) % 26
            c = ch.repeat(len(pos))
            for r in (2, 1, 0):
                c = (w[r][(c + pos[:, r]) % 26] - pos[:, r]) % 26
            c = refl[c]
            for r in (0, 1, 2):
                c = (inv[r][(c + pos[:, r]) % 26] - pos[:, r]) % 26
            counts[rows, c] += 1
        counts_all.append(((counts * (counts - 1)).sum(1) / (n * (n - 1))).cpu().numpy())
    ics = np.concatenate(counts_all)
    best = int(np.argmax(ics))
    return grid[best].astype(np.int32), float(ics[best])


def population_anneal(ct, n_sym, table, letter, chains=4096, steps=20000, w=2.0, t0=3.0, seed=0):
    """Thousands of homophonic chains stepping together; each step rescores whole texts.

    Returns (key, objective, proposals). The CPU solver is incremental, so compare with care.
    """
    import torch

    dev = device()
    torch.manual_seed(seed)
    tct = _tensor(ct, dev)
    tab = _tensor(table, dev, torch.float32)
    let = _tensor(letter, dev, torch.float32)
    n = len(ct)
    expected = n * let + 1e-6
    rows = torch.arange(chains, device=dev)

    def objective(k):
        p = k[:, tct]
        q = tab[p[:, :-3] * 17576 + p[:, 1:-2] * 676 + p[:, 2:-1] * 26 + p[:, 3:]].sum(1)
        c = torch.zeros((chains, 26), device=dev, dtype=torch.float32)
        c.scatter_add_(1, p, torch.ones_like(p, dtype=torch.float32))
        return q - w * (((c - expected) ** 2) / expected).sum(1)

    key = torch.multinomial(let, chains * n_sym, replacement=True).reshape(chains, n_sym)
    cur = objective(key)
    best_s, best_k = cur.max().item(), key[cur.argmax()].clone()
    for it in range(steps):
        temp = t0 * (1 - it / steps) + 1e-3
        a = torch.randint(0, n_sym, (chains,), device=dev)
        old = key[rows, a].clone()
        key[rows, a] = torch.randint(0, 26, (chains,), device=dev)
        new = objective(key)
        keep = (new - cur) >= torch.log(torch.rand(chains, device=dev) + 1e-12) * temp
        key[rows[~keep], a[~keep]] = old[~keep]
        cur = torch.where(keep, new, cur)
        top = cur.max().item()
        if top > best_s:
            best_s, best_k = top, key[cur.argmax()].clone()
    return best_k.cpu().numpy().astype(np.int32), best_s, chains * steps
