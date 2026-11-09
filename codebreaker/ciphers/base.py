"""Cipher description object and the global registry."""
from dataclasses import dataclass, field
from typing import Callable, Optional

REGISTRY: dict[str, "Cipher"] = {}

DEMO_PLAIN = (
    "The old lighthouse keeper wrote every evening in a small green notebook. Nobody in the village "
    "knew what he recorded there, and when the winter storms came he would climb the stairs alone and "
    "watch the ships go past the rocks. After he died the children found the book hidden behind a loose "
    "stone, but the pages were filled with strange letters that none of them could read. They carried it "
    "to the schoolmaster, who studied the patterns for many weeks before the first words began to appear."
)


@dataclass
class Param:
    name: str
    label: str
    kind: str = "text"  # text | int | choice
    choices: Optional[list] = None
    help: str = ""


@dataclass
class Cipher:
    id: str
    name: str
    family: str
    era: str
    summary: str
    how: str
    weakness: str
    encrypt: Callable
    decrypt: Optional[Callable]
    key: dict  # worked-example key
    example: str
    params: list = field(default_factory=list)
    attack: Optional[Callable] = None  # (ciphertext, lang) -> dict
    attack_name: str = ""
    keygen: Optional[Callable] = None  # (random.Random) -> key dict for attack demos
    demo_attack: Optional[Callable] = None  # (seed) -> dict, for modern misuse attacks
    modern: bool = False

    def card(self) -> dict:
        return {"id": self.id, "name": self.name, "family": self.family, "era": self.era, "summary": self.summary,
                "can_attack": bool(self.attack or self.demo_attack)}

    def detail(self) -> dict:
        ct = self.encrypt(self.example, **self.key)
        return {**self.card(), "how": self.how, "weakness": self.weakness, "attack_name": self.attack_name,
                "key": self.key, "example": self.example, "example_cipher": ct,
                "example_back": self.decrypt(ct, **self.key) if self.decrypt else None,
                "params": [vars(p) for p in self.params], "paste_attack": bool(self.attack), "modern": self.modern}


def add(**kw) -> Cipher:
    c = Cipher(**kw)
    if c.id in REGISTRY:
        raise ValueError(f"duplicate cipher id {c.id}")
    REGISTRY[c.id] = c
    return c


def dict_word(r) -> str:
    """A random keyword guaranteed to be inside the attack dictionary."""
    from ..languages import keywords

    return r.choice(keywords("en", 2000, 4))
