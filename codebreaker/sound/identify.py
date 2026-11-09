"""Who or what made this sound? BirdNET for birds (as in the user's bird_sound_analyzer project) and YAMNet for everything else.

Both models run on ai-edge-litert. Each answer is compared with the same model's best score on noise, because BirdNET
gives about 0.5 to some class even for random noise."""
import csv
import threading
from functools import lru_cache

import numpy as np

from ..languages import ROOT
from .audio import resample

YAMNET = ROOT / "data/models/yamnet"
_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def _birdnet():
    import birdnet

    return birdnet.load("acoustic", "2.4", "tf", library="litert")


def birds(x: np.ndarray, sr: int, top: int = 5) -> dict:
    """Species heard, with the noise baseline to compare against."""
    r = _birds_raw(x, sr, top)
    if r.get("available"):
        r["noise_baseline"] = noise_baseline()["birds"]
    return r


def _birds_raw(x: np.ndarray, sr: int, top: int = 5) -> dict:
    """Species heard in 3-second windows, best confidence per species across the recording."""
    try:
        with _LOCK:
            m = _birdnet()
            y = resample(x, sr, m.get_sample_rate())
            df = m.predict_arrays([(y, m.get_sample_rate())], top_k=3, n_workers=1).to_dataframe()
    except Exception as exc:  # the page still shows the song analysis without a model
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
    col_species = next(c for c in df.columns if "species" in c.lower())
    col_conf = next(c for c in df.columns if "conf" in c.lower())
    best = df.groupby(col_species)[col_conf].agg(["max", "count"]).sort_values("max", ascending=False).head(top)
    rows = []
    for name, r in best.iterrows():
        sci, _, common = str(name).partition("_")
        rows.append({"scientific": sci, "common": common or sci, "confidence": round(float(r["max"]), 3), "windows": int(r["count"])})
    return {"available": True, "species": rows, "windows": int(df[df.columns[0]].count())}


@lru_cache(maxsize=1)
def _yamnet():
    from ai_edge_litert.interpreter import Interpreter

    it = Interpreter(model_path=str(YAMNET / "yamnet.tflite"))
    it.allocate_tensors()
    with open(YAMNET / "yamnet_class_map.csv") as f:
        names = [r["display_name"] for r in csv.DictReader(f)]
    return it, names


def sounds(x: np.ndarray, sr: int, top: int = 8) -> dict:
    """General sound classes, averaged over about one-second frames."""
    try:
        with _LOCK:
            it, names = _yamnet()
            y = resample(x, sr, 16000)
            n, hop = 15600, 7800
            if len(y) < n:
                y = np.pad(y, (0, n - len(y)))
            inp, out = it.get_input_details()[0]["index"], it.get_output_details()[0]["index"]
            scores = []
            for s in range(0, len(y) - n + 1, hop):
                it.set_tensor(inp, y[s:s + n].astype(np.float32))
                it.invoke()
                scores.append(it.get_tensor(out)[0].copy())
    except Exception as exc:  # reported, not fatal
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
    s = np.array(scores)
    mean, peak = s.mean(axis=0), s.max(axis=0)
    order = np.argsort(-mean)[:top]
    return {"available": True, "classes": [{"name": names[i], "mean": round(float(mean[i]), 3), "peak": round(float(peak[i]), 3)} for i in order], "frames": len(s)}


@lru_cache(maxsize=1)
def noise_baseline() -> dict:
    """Each model's best answer on 9 seconds of pink-ish noise: a score below this means nothing."""
    rnd = np.random.default_rng(0)
    w = rnd.normal(size=48000 * 9)
    x = np.cumsum(w) * 0.002 + w * 0.02
    x = (x - x.mean()).astype(np.float32) * 0.1
    b = _birds_raw(x, 48000, top=1)
    return {"birds": b["species"][0]["confidence"] if b.get("available") and b["species"] else None}
