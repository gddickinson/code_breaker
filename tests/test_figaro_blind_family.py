import json

from codebreaker.mysteries import figaro_blind_family as F


def test_family_sizes_and_documented_keys():
    sizes = {n: len(F.family(n)[0]) for n in ("2119", "2402", "2217")}
    assert sizes == {"2119": 121, "2402": 10, "2217": 5}
    words, key = F.family("2217")
    assert F.agreement(words, key, key) == 1.0 and F.agreement(words, {}, key) == 0.0


def test_blind_results_recorded():
    fam = json.loads(F.RESULT.read_text())["families"]
    assert fam["2402"]["gates"]["passed"] and fam["2217"]["gates"]["passed"]
    assert not fam["2119"]["gates"]["reads"] and fam["2119"]["gates"]["control"] and fam["2119"]["gates"]["null"]
    assert all(f["agreement_with_documented"] > 0.95 for f in fam.values())
