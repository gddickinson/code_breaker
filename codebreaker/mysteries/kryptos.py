"""Kryptos: confirm K1-K3 with our tools, then test periodic models of K4 against its cribs."""
import re

from ..ciphers.polyalphabetic import quag_d
from ..languages import ROOT, score
from ..segment import segment
from ..text import A, keyed_alphabet, letters

CRIBS = {21: "EASTNORTHEAST", 63: "BERLINCLOCK"}  # zero-based starts of Sanborn's published clues


def sections() -> dict:
    raw = (ROOT / "data/sources/wp_kryptos.txt").read_text()
    block = raw[raw.index("<pre>EMUFPHZ") + 5:]
    block = block[: block.index("</pre>")]
    body = re.sub(r"[^A-Z?]", "", block)
    k2, k3, k4 = body.index("VFPJU"), body.index("ENDYAH"), body.index("OBKR")
    return {"K1": body[:k2].replace("?", ""), "K2": body[k2:k3].replace("?", ""), "K3": body[k3:k4].replace("?", ""), "K4": body[k4:].replace("?", "")}


def rotate_decrypt(ct: str) -> str:
    """K3's published method: two grid rotations, undone here by index tracking."""
    n = len(ct)
    best = ("", -99.0, None)
    for a in range(2, 60):
        if n % a:
            continue
        for b in range(2, 60):
            if n % b:
                continue
            for flip in (False, True):
                t = _unrotate(_unrotate(ct, b, flip), a, flip)
                s = score(t)
                if s > best[1]:
                    best = (t, s, (a, b, flip))
    return best


def _unrotate(t: str, w: int, flip: bool) -> str:
    h = len(t) // w
    out = [""] * len(t)
    idx = 0
    for c in range(w):
        for r in range(h):
            target = (h - 1 - r) * w + c if not flip else r * w + (w - 1 - c)
            out[target] = t[idx]
            idx += 1
    return "".join(out)


def crib_conflicts(ct: str, alphabet: str, variant: str, period: int) -> tuple[int, int]:
    """Return (conflicts, comparisons): key positions the cribs constrain more than once."""
    alpha = keyed_alphabet(alphabet) if alphabet else A
    seen, conflicts, comparisons = {}, 0, 0
    for start, crib in CRIBS.items():
        for i, p in enumerate(crib):
            pos = start + i
            ci, pi = alpha.index(ct[pos]), alpha.index(p)
            k = {"vigenere": (ci - pi) % 26, "beaufort": (ci + pi) % 26, "variant": (pi - ci) % 26}[variant]
            if pos % period in seen:
                comparisons += 1
                conflicts += seen[pos % period] != k
            seen.setdefault(pos % period, k)
    return conflicts, comparisons


def k4_elimination(ct: str) -> dict:
    """A model is only eliminated or supported if the cribs actually constrain it."""
    eliminated, untestable, survivors = 0, [], []
    for alphabet in ("", "KRYPTOS"):
        for variant in ("vigenere", "beaufort", "variant"):
            for period in range(1, 49):
                bad, comps = crib_conflicts(ct, alphabet, variant, period)
                row = {"alphabet": alphabet or "standard", "variant": variant, "period": period, "comparisons": comps}
                if comps == 0:
                    untestable.append(row)
                elif bad:
                    eliminated += 1
                else:
                    survivors.append(row)
    return {"models_total": 288, "eliminated": eliminated, "survivors_with_real_constraints": survivors,
            "untestable_periods": sorted({r["period"] for r in untestable}), "known_positions": sum(len(c) for c in CRIBS.values())}


def run() -> dict:
    s = sections()
    k1 = quag_d(s["K1"], "KRYPTOS", "PALIMPSEST")
    k2 = quag_d(s["K2"], "KRYPTOS", "ABSCISSA")
    t3, score3, params = rotate_decrypt(s["K3"])
    return {"id": "kryptos", "lengths": {k: len(v) for k, v in s.items()}, "k1": segment(k1), "k2": segment(k2),
            "k3": segment(t3), "k3_score": round(score3, 3), "k3_params": list(params) if params else None, "k4": s["K4"], "k4_elimination": k4_elimination(s["K4"]),
            "k4_status": "Sanborn's K4 solution sold at auction on 20 November 2025. It has not been published."}
