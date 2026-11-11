"""Round 85: install every Argos Translate model into English (user request: translate far more languages).

Models come from the Argos package index (MIT-licensed software; models under their own open licences, listed in the
index). Already installed packages are skipped. Writes data/sources/translators.json with what was installed."""
import json
import time
from pathlib import Path

import argostranslate.package as pkg

OUT = Path(__file__).resolve().parents[1] / "data/sources/translators.json"

pkg.update_package_index()
index = pkg.get_available_packages()
have = {(p.from_code, p.to_code) for p in pkg.get_installed_packages()}
todo = sorted((p for p in index if p.to_code == "en" and (p.from_code, p.to_code) not in have), key=lambda p: p.from_code)
print(len(todo), "to install:", [p.from_code for p in todo], flush=True)
done = []
for p in todo:
    t = time.time()
    try:
        pkg.install_from_path(p.download())
        done.append({"from": p.from_code, "name": p.from_name, "to": "en", "version": str(getattr(p, "package_version", "")), "seconds": round(time.time() - t)})
        print("installed", p.from_code, p.from_name, flush=True)
    except Exception as exc:  # keep going; report at the end
        print("failed", p.from_code, exc, flush=True)
installed = sorted({x.from_code for x in pkg.get_installed_packages() if x.to_code == "en"})
OUT.write_text(json.dumps({"source": "Argos Translate package index", "date": time.strftime("%Y-%m-%d"), "installed_into_english": installed,
                           "this_run": done}, indent=1))
print("into English now:", len(installed), installed)
