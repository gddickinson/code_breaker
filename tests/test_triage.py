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
