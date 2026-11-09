"""Download Argos models between English and the supported languages."""
import argostranslate.package as pkg

pkg.update_package_index()
index = pkg.get_available_packages()
for code in ("fr", "de", "it", "es"):
    for a, b in ((code, "en"), ("en", code)):
        p = next(x for x in index if x.from_code == a and x.to_code == b)
        pkg.install_from_path(p.download())
        print("installed", a, b, flush=True)
