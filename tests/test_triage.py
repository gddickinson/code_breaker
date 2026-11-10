"""Round 62: triage of the review queue."""
import json

from codebreaker.mysteries import triage as T


def test_tier_rules():
    assert T.tier("all three gates pass ... Read by eye.", "") == "A"
    assert T.tier("p=5.0e-04 against shuffles (Bonferroni). Read by eye.", "") == "B"
    assert T.tier("p=0.11, does not pass the bar. Read by eye.", "") == "C"
    assert T.tier("machine reading from OCR. NOT yet checked against the scan.", "") == "D"
    assert T.tier("structure only", "") == "D"


def test_every_lead_in_one_tier_and_no_stale_2119():
    r = T.run()
    assert len(r["rows"]) == r["leads"] == sum(r["tiers"].values())
    assert all(x["tier"] in "ABCD" for x in r["rows"])
    assert r["unchecked_2119"] == []


def test_report_written():
    text = T.REPORT.read_text()
    assert text.startswith("# Review queue") and "Tier A" in text


def test_latest_round_weakness_supersedes_but_gates_persist():
    old_weak_new_strong = "Round 30: word gate fails (coverage 59%). Read by eye. Round 40: passes all three gates against printed ads."
    assert T.tier(old_weak_new_strong, "") == "A"
    gates_then_detail = "Round 55: all three gates pass. Read by eye. Round 56: refined readings include 'courage'."
    assert T.tier(gates_then_detail, "") == "A"
    latest_weak = "Round 47: p=5e-4 (Bonferroni). Read by eye. Round 59: does not pass the bar after retranscription."
    assert T.tier(latest_weak, "") == "C"


def test_explicit_stays_in_c_overrides_old_p_value():
    ev = "Round 69: transcribed from the scan; p=0.3007; does not pass. Round 71: stays in tier C: mostly plain text."
    assert T.tier(ev, "") == "C"
