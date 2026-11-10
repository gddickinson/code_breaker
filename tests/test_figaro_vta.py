"""Round 36: the abbreviated-plain filter and the V. T. A. correspondence."""
import json
import random
import re
from difflib import SequenceMatcher

from codebreaker.mysteries import figaro_plainness as P
from codebreaker.mysteries import figaro_vta as V


def test_transcription_matches_ocr():
    """The cipher words were transcribed by eye; nearly all must also be found in the OCR of the same scan."""
    ocr = {}
    for f in ("ocr_raw.json", "ocr_otsu.json"):
        for k, v in json.loads((V.OUT / f).read_text()).items():
            if "VTA" in k:
                ocr[k] = ocr.get(k, "") + " " + " ".join(x for e in v.values() if e for x in e)
    hit = tot = 0
    for image, ad in V.ads().items():
        assert (V.OUT / "images" / image).exists()
        assert set("".join(V.words_of(ad["cipher"]))) <= set("abcdefghijklmnopqrstuvwxyz0123456789+'")
        text = re.sub(r"[^a-z0-9+]", "", ocr[image].lower().replace("十", "+"))
        for w in (w.replace("'", "") for w in V.words_of(ad["cipher"]) if len(w) >= 4):
            tot += 1
            hit += max(SequenceMatcher(None, w, text[i:i + len(w)]).ratio() for i in range(max(1, len(text) - len(w) + 1))) >= 0.75
    assert tot > 120 and hit / tot >= 0.95


def test_cribs_fit_one_key():
    assert all(len(c.replace("'", "")) == len(p) for _, c, p in V.CRIBS)
    key = V.full_key()
    wrong = sum(a != b.translate(V.MERGE) for _, c, p in V.CRIBS for a, b in zip(V.decode(c, key), p))
    assert wrong / sum(len(p) for _, c, p in V.CRIBS) < 0.02
    assert V.decode("hxd", key) == "you" and V.decode("y82t17", key) == "petite"


def test_held_out_beats_null_and_scrambled_control():
    h = V.held_out(trials=300)
    assert h["pooled_share"] > 3 * h["null_max"] and h["p_value"] < 0.01
    assert h["crib_letters_right"] / h["crib_letters"] > 0.95
    s = V.scrambled_control()
    assert s["pooled_share"] < h["pooled_share"] / 3 and s["crib_letters_right"] / s["crib_letters"] < 0.4


def test_address_without_cribs_decodes():
    """The 1 Sep ad gave no cribs; with the key it reads as a Paris street name."""
    words = V.words_of(V.ads()["1877_18770901-VTA.jpg"]["cipher"])
    assert [V.decode(w, V.full_key()) for w in words[2:4]] == ["mont", "sainte"]


def test_plainness_separates_controls():
    rnd = random.Random(1)
    t = P.abbreviated("Ch. - 3 sem[aines] s[an]s pouv[oir] v[ous] par[ler] malg[ré] t[ou]s m[es] eff[orts]! V[ous] m'avi[ez] prom[is] (dm)")
    assert t.startswith("semsspouvvparmalgtsmeff")
    plain = "recuavecbonheurlesdepechesmerciimpossiblefaireinsereravisaveclettresconvenues"
    assert P.stem_coverage(plain) > 0.8
    assert P.stem_coverage(P.substitute(plain, rnd)) < 0.3
