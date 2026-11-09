"""Regenerate the measurements and pictures shown on the Recovery page."""
import json

from codebreaker.mysteries import recovery as R, recovery_images as I


def main():
    I.STATIC.mkdir(exist_ok=True)
    out = {"gallery": I.gallery(), "ocr": R.ocr_benchmark(), "reconstruction": I.experiment(), "spread": R.error_spread(), "repair_control": R.repair_control(), "repair_real": R.repair_real(), "digits": R.digit_audit()}
    (I.STATIC / "results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "ocr"})[:3500])
    print(out["ocr"]["table"])


if __name__ == "__main__":
    main()
