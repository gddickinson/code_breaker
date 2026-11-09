"""Train the cipher-type classifier; compare GPU with CPU; evaluate on unseen keys and texts."""
import json
import random
import time

from codebreaker import accel, classifier as C
from codebreaker.autobreak import autobreak
from codebreaker.ciphers import REGISTRY
from codebreaker.languages import ROOT
from codebreaker.text import letters, similarity

if __name__ == "__main__":
    t = time.time()
    x, y = C.dataset(320, 11)
    tx, ty = C.dataset(50, 900011)
    print("classes", len(C.CLASSES), "train", len(x), "test", len(tx), round(time.time() - t), "s", flush=True)
    dev = accel.device()
    _, gpu_t = C.train(x[:2000], y[:2000], dev, epochs=2)
    _, cpu_t = C.train(x[:2000], y[:2000], "cpu", epochs=2)
    print("speed gpu", round(gpu_t, 1), "cpu", round(cpu_t, 1), flush=True)
    net, dt = C.train(x, y, dev, epochs=16)
    ev = C.evaluate(net, tx, ty, dev)
    print({k: ev[k] for k in ("top1", "top3", "family")}, "train s", round(dt), flush=True)
    C.save(net)
    C._CACHE.clear()
    r, names, trials = random.Random(77), [c for c in C.CLASSES if c in REGISTRY and c not in ("chaocipher", "twosquare", "foursquare", "double")], []
    for i in range(24):
        cid = names[i % len(names)]
        c = REGISTRY[cid]
        plain = C.sample_text(r)
        ct = c.encrypt(plain, **c.keygen(r))
        res = autobreak(ct, top=4)
        best = res["best"]
        got = letters(best["plaintext"]) if best else ""
        trials.append({"cipher": cid, "identified": res["guesses"][0]["id"], "recovered": round(similarity(letters(plain), got[: len(letters(plain))]), 3), "top_system": best["cipher"] if best else None})
        print(trials[-1], flush=True)
    out = {"id": "classifier", "classes": len(C.CLASSES), "train": len(x), "test": len(tx), "gpu_seconds_2_epochs": round(gpu_t, 1), "cpu_seconds_2_epochs": round(cpu_t, 1), **ev, "autobreak_trials": trials, "autobreak_solved": sum(t["recovered"] > 0.8 for t in trials)}
    (ROOT / "data/results/classifier.json").write_text(json.dumps(out, indent=1))
    print("autobreak solved", out["autobreak_solved"], "of", len(trials))
