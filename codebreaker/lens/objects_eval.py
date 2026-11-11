"""Controls for object understanding and tracking (Round 90b); data/results/lens_objects_eval.json.

Pictures: the macOS account pictures (/Library/User Pictures: animals, flowers, instruments, nature, sports, fun;
Apple's images, converted locally into data/lens_debug/objects and never committed), named by their file names.
Naming: a hit when the name's key word is in the model's label or description, or in the classifier's top-5 ImageNet
names (ImageNet has no class for many of them, e.g. rose or lightning, which caps the fallback). Null 1: the same
pictures with their pixels shuffled (naming the original object is an invention). Null 2: noise pictures (anything
but 'none' is invented). Boxes: each picture pasted at a random place and size on a textured background; overlap
(IoU) of the model's box and of GrabCut's with the pasted rectangle. Tracking: a pasted object moving and growing
over 40 frames (mean IoU, frames lost); null: frames without the object (share reported lost)."""
import json
import random
from pathlib import Path

import cv2
import numpy as np

from . import objects as O
from .objects_track import Tracker
from ..languages import ROOT

PICS = ROOT / "data/lens_debug/objects"
RESULT = ROOT / "data/results/lens_objects_eval.json"
KEYS = {"whiterose": "rose", "red rose": "rose", "sandollar": "sand dollar", "yin-yang": "yin", "gingerbread man": "gingerbread",
        "yellow daisy": "daisy", "fortune cookie": "fortune cookie", "smack": "lips"}


def key(name: str) -> str:
    n = name.lower()
    return KEYS.get(n, n.split()[-1])


def prepare(src: Path = Path("/Library/User Pictures")) -> list[Path]:
    PICS.mkdir(parents=True, exist_ok=True)
    import subprocess

    for f in sorted(src.glob("*/*.heic")):
        out = PICS / f"{f.stem}.jpg"
        if not out.exists():
            subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "512", str(f), "--out", str(out)], capture_output=True)
    return sorted(PICS.glob("*.jpg"))


def iou(a, b) -> float:
    if not a or not b:
        return 0.0
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    return inter / float(aw * ah + bw * bh - inter + 1e-9)


def background(w: int, h: int, rnd: random.Random) -> np.ndarray:
    g = np.random.default_rng(rnd.randint(0, 1 << 30)).integers(90, 200, (h // 8 + 1, w // 8 + 1, 3)).astype(np.uint8)
    return cv2.GaussianBlur(cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC), (0, 0), 3)


def paste(bg: np.ndarray, obj: np.ndarray, x: int, y: int, size: int) -> tuple[np.ndarray, list[int]]:
    o = cv2.resize(obj, (size, size))
    out = bg.copy()
    out[y:y + size, x:x + size] = o
    return out, [x, y, size, size]


def naming(pics: list[Path], rnd: random.Random) -> dict:
    rows = []
    for p in pics:
        img, k = cv2.imread(str(p)), key(p.stem)
        a = O.identify_ai(img) or {}
        c = O.classify(img)
        sh = img.reshape(-1, 3).copy()
        np.random.default_rng(rnd.randint(0, 1 << 30)).shuffle(sh)
        s = O.identify_ai(sh.reshape(img.shape)) or {}
        said = f"{a.get('label', '')} {a.get('description', '')}".lower()
        rows.append({"picture": p.stem, "ai": a.get("label", ""), "ai_hit": k in said, "classical": c[0]["label"] if c else "",
                     "classical_hit": any(k in x["names"].lower() for x in c), "shuffled_said": s.get("label", ""),
                     "shuffled_named_original": k in f"{s.get('label', '')} {s.get('description', '')}".lower(), "ai_seconds": a.get("seconds")})
    n = len(rows)
    return {"pictures": n, "ai_named": sum(r["ai_hit"] for r in rows), "classical_top5": sum(r["classical_hit"] for r in rows),
            "shuffled_named_original": sum(r["shuffled_named_original"] for r in rows),
            "shuffled_said_none": sum(not r["shuffled_said"] for r in rows), "rows": rows}


def run(seed: int = 90) -> dict:
    rnd = random.Random(seed)
    pics = prepare()
    out = {"naming": naming(pics, rnd)}
    noise = [O.identify_ai(np.random.default_rng(i).integers(0, 255, (400, 400, 3)).astype(np.uint8)) or {} for i in range(3)]
    out["noise pictures"] = {"pictures": 3, "said_none": sum(not r.get("label") for r in noise), "labels": [r.get("label", "") for r in noise]}
    ai_iou, gc_iou = [], []
    for p in rnd.sample(pics, 10):
        bg = background(800, 600, rnd)
        size = rnd.randint(150, 300)
        img, box = paste(bg, cv2.imread(str(p)), rnd.randint(0, 800 - size), rnd.randint(0, 600 - size), size)
        a = O.identify_ai(img) or {}
        ai_iou.append(iou(a.get("box"), box))
        gc_iou.append(iou(O.outline(img), box))
    out["boxes"] = {"pictures": 10, "ai_mean_iou": round(float(np.mean(ai_iou)), 3), "grabcut_mean_iou": round(float(np.mean(gc_iou)), 3),
                    "ai_iou_over_0.5": sum(v > 0.5 for v in ai_iou), "grabcut_iou_over_0.5": sum(v > 0.5 for v in gc_iou)}
    tr = []
    for p in rnd.sample(pics, 5):
        obj, bg = cv2.imread(str(p)), background(800, 600, rnd)
        frames = []
        for f in range(40):
            size = int(120 * (1 + 0.15 * f / 39))
            frames.append(paste(bg, obj, 80 + 12 * f, 150 + int(60 * np.sin(f / 6)), size))
        t = Tracker(frames[0][0], frames[0][1])
        res = [t.update(fr) for fr, _ in frames[1:]]
        empty = Tracker(frames[0][0], frames[0][1])
        nul = [empty.update(bg) for _ in range(10)]
        tr.append({"mean_iou": float(np.mean([iou(r["box"], b) for r, (_, b) in zip(res, frames[1:])])), "lost": sum(r["lost"] for r in res),
                   "null_lost_share": sum(r["lost"] for r in nul) / len(nul)})
    out["tracking"] = {"sequences": len(tr), "mean_iou": round(float(np.mean([x["mean_iou"] for x in tr])), 3),
                       "frames_lost": sum(x["lost"] for x in tr), "frames": 39 * len(tr),
                       "null_object_removed_reported_lost": round(float(np.mean([x["null_lost_share"] for x in tr])), 2)}
    return {"id": "lens_objects_eval", "model": O.ai_local.status()["vision"], "results": out}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps({k: {a: b for a, b in v.items() if a != "rows"} for k, v in r["results"].items()}, indent=1))
