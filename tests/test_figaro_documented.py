"""Round 42: documented systems on their writers' unsolved ads."""
import json

from codebreaker.mysteries import figaro_documented as D
from codebreaker.mysteries.figaro_keys import OUT


def test_three_vigenere_keys_parsed():
    keys = {v["key"]: v for v in D.vigenere_systems()}
    assert set(keys) == {"BCD", "CEAD", "CD"} and "CH" in keys["CEAD"]["users"] and "VE" in keys["CEAD"]["users"]


def test_vigenere_restarts_per_block():
    s = {"kind": "vigenere", "key": "CEAD"}
    assert D.apply(s, "LIPDTX") == "JEPARS" and D.apply(s, "NIHYKY") == "LEHUIT"


def test_transcribed_ads_read_under_their_tables():
    data = json.loads((OUT / "documented_transcription.json").read_text())["ads"]
    sysmap = {s["id"]: s for s in D.systems()}
    for image, ad in data.items():
        assert (OUT / "images" / image).exists()
        plain = " ".join(D.apply(sysmap[ad["table"]], w.upper()) for w in ad["cipher"].split())
        assert sum(c != "?" for c in plain) / len(plain) > 0.9
    geo = data["1890_18900619-GEO.jpg"]
    assert " ".join(D.apply(sysmap["1110"], w.upper()) for w in geo["cipher"].split()) == "IYAUNAN FOLLEMENT JETATTEDS TOUTATOI"


def test_own_system_ranks_first_far_above_chance():
    r = json.loads(D.RESULT.read_text())
    assert r["own_first"] >= 3 * r["expected_first"] and r["p_value"] < 1e-3
