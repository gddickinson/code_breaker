"""Synthetic birdsong: syllable types drawn from a small grammar, so the true sequence is known."""
import numpy as np

SR = 22050


def _syllable(kind: str, dur: float, rnd: np.random.Generator) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    if kind == "A":  # rising whistle
        f = 2500 + 2500 * t / dur
    elif kind == "B":  # falling whistle
        f = 5500 - 2500 * t / dur
    elif kind == "C":  # trill: fast frequency wobble
        f = 4000 + 600 * np.sin(2 * np.pi * 60 * t)
    elif kind == "D":  # low flat note
        f = np.full_like(t, 1800.0)
    else:  # E: high buzz
        f = 7000 + 300 * np.sin(2 * np.pi * 180 * t)
    phase = 2 * np.pi * np.cumsum(f) / SR
    env = np.sin(np.pi * t / dur) ** 0.6
    return (env * np.sin(phase) * rnd.uniform(0.5, 0.9)).astype(np.float32)


DUR = {"A": 0.12, "B": 0.12, "C": 0.2, "D": 0.15, "E": 0.08}
GRAMMAR = {"A": "AB", "B": "CA", "C": "DC", "D": "AE", "E": "BA"}


def song(n: int = 40, seed: int = 1, noise: float = 0.02) -> tuple[np.ndarray, int, str]:
    """A song of n syllables from a Markov grammar, with gaps and background noise."""
    rnd = np.random.default_rng(seed)
    seq, cur, parts = [], "A", []
    for _ in range(n):
        seq.append(cur)
        parts.append(_syllable(cur, DUR[cur] * rnd.uniform(0.9, 1.1), rnd))
        parts.append(np.zeros(int(SR * rnd.uniform(0.06, 0.12)), np.float32))
        cur = GRAMMAR[cur][rnd.integers(2)]
    x = np.concatenate([np.zeros(int(0.3 * SR), np.float32)] + parts)
    x += rnd.normal(0, noise, len(x)).astype(np.float32)
    return x, SR, "".join(seq)
