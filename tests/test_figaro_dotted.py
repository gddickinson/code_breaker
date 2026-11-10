"""Round 67: dotted number lists against fixed numeric systems."""
import json

from codebreaker.mysteries import figaro_dotted as D


def test_systems_and_decode():
    s = dict(D.systems())
    assert s["alphabet shift 0"]["1"] == "A" and s["reversed alphabet shift 0"]["1"] == "Z" and len(s) >= 60
    assert D.words("1.2 - 3") == [["1", "2"], ["3"]]


def test_opq_reads_under_table_2308():
    r = {x["image"]: x for x in json.loads(D.RESULT.read_text())["rows"]}
    opq = r["1877_18770412-OPQ.jpg"]
    assert opq["system"] == "table 2308" and opq["reading"].startswith("DEMAIN") and opq["passes"]
    assert not r["1882_18821010-LINETTE.jpg"]["passes"]
