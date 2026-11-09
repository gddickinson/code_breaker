"""Runs attack demonstrations: encrypt a known text with a random key, then break it."""
import random

from ..text import similarity
from .base import DEMO_PLAIN, REGISTRY


def attack_demo(cipher_id: str, seed: int | None = None, lang: str = "en") -> dict:
    c = REGISTRY[cipher_id]
    if c.demo_attack:
        return c.demo_attack(seed if seed is not None else random.randrange(10**6))
    if not c.attack or not c.keygen:
        raise ValueError(f"{c.name} has no attack demonstration")
    rng = random.Random(seed)
    key = c.keygen(rng)
    ct = c.encrypt(DEMO_PLAIN, **key)
    truth = c.decrypt(ct, **key)
    got = c.attack(ct, lang)
    return {"kind": "classical", "secret_key": key, "ciphertext": ct, "truth": truth, **got,
            "accuracy": round(similarity(truth, got["plaintext"]), 3)}
