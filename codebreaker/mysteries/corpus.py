"""Loads each code's symbol sequence from its source file."""
import json
import re

from ..languages import ROOT
from .sweep import tokens

SRC = ROOT / "data/sources"
LOADERS = {}


def loader(slug):
    def wrap(fn):
        LOADERS[slug] = fn
        return fn
    return wrap


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load(slug: str, data_path: str) -> list[str]:
    if slug in LOADERS:
        return LOADERS[slug]()
    return tokens((ROOT / data_path).read_text(errors="ignore"))


@loader("beale-1")
def _b1():
    return [str(n) for n in next(r for r in json.loads((ROOT / "data/mysteries/beale_raw.json").read_text()) if r[:2] == [71, 194])]


@loader("beale-3")
def _b3():
    return [str(n) for n in next(r for r in json.loads((ROOT / "data/mysteries/beale_raw.json").read_text()) if r[:2] == [317, 8])]


@loader("dagapeyeff")
def _dag():
    from .dagapeyeff import digits, pairs_of
    d = digits()
    return pairs_of(d[:-3] if d.endswith("000") else d)


@loader("tamam-shud")
def _tam():
    from .tamam import CODE
    return list(CODE)


@loader("kryptos-k4")
def _k4():
    from .kryptos import sections
    return list(sections()["K4"])


@loader("voynich")
def _voy():
    from .voynich import glyphs, parse
    return glyphs([w for r in parse()[:260] for w in r["words"]], True)


@loader("pigeon")
def _pigeon():
    from .pigeon import text
    return list(text())
