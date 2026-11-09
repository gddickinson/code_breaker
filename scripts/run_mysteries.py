"""Run mystery analyses in parallel and save JSON to data/results/."""
import importlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data/results"


def job(name):
    t = time.time()
    res = importlib.import_module(f"codebreaker.mysteries.{name}").run()
    res["runtime_s"] = round(time.time() - t, 1)
    (OUT / f"{name}.json").write_text(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    return name, res["runtime_s"]


if __name__ == "__main__":
    names = sys.argv[1:] or ["kryptos", "voynich", "tamam", "dagapeyeff", "beale", "solvability", "zodiac", "dorabella", "sweep", "scriptlab", "beale_forensics", "dagapeyeff_models", "kryptos_layers", "tamam_mnemonic", "voynich_generators", "liber_primus", "pigeon", "beale_drift", "rongo_align", "liber_keys", "polyalpha_sweep"]
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(4) as ex:
        for f in as_completed([ex.submit(job, n) for n in names]):
            try:
                print("done", f.result(), flush=True)
            except Exception as e:
                import traceback; traceback.print_exc(); print("FAILED", e, flush=True)
