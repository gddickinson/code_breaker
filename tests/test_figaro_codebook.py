"""Round 52: L. R. G. read as a homophonic substitution; other codebook tests."""
import json

from codebreaker.mysteries import figaro_codebook as C


def test_lrg_key_reads_known_groups():
    key = json.loads(C.RESULT.read_text())["lrg_blind"]["key"]
    dec = lambda t: "".join(key[c] for c in t)
    assert dec("6c72347c4ch85") == "ecrisarcachon"
    assert dec(C.clean(C.DATA["lrg"]["1880_18800705-LRG.jpg"])).startswith("machercherlettreposterestante")


def test_lrg_gates_and_convergence():
    b = json.loads(C.RESULT.read_text())["lrg_blind"]
    assert b["gates"]["passed"] and b["seeds_converged"] >= 2
    assert b["coverage"] > 2 * max(n["coverage"] for n in b["null"])


def test_shared_groups_counts():
    assert C.shared(["abcde"], ["xxbcdyy"], 3) == 1 and C.shared(["abcde"], ["zzz"], 3) == 0


def test_short_ads_are_unreliable():
    rows = json.loads(C.RESULT.read_text())["lc15_per_ad"]
    assert all(r["control_mean_accuracy"] < 0.7 for r in rows)


def test_jane_numbers_and_reading():
    import re

    j = json.loads(C.RESULT.read_text())["jane_blind"]
    nums = [n for t in C.DATA["jane"].values() for n in re.findall(r"\d+", t.replace(" - 1925", ""))]
    assert len(nums) == j["numbers"] and max(map(int, nums)) <= 74
    assert j["gates"]["control"] and j["gates"]["null"]
    assert "les elans de mon co eur" in j["readings"]["1886_18860908-Jane.jpg"]
