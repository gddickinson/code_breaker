"""Round 69: tier-C documented-system ads retested."""
import json

from codebreaker.mysteries import figaro_tierc as F


def test_dotted_decode_keeps_clear_letters():
    key = {"1": "A", "2": "B"}
    assert F._dotted_decode(["1.2e", "2"], key) == "ABE B"


def test_recorded_result():
    r = {x["image"]: x for x in json.loads(F.RESULT.read_text())["rows"]}
    assert len(r) == 10 and sum(x["passes"] for x in r.values()) == 9
    assert "DINER" in r["1894_18940920-25.jpg"]["reading"] and r["1890_18900203-LILI.jpg"]["reading"].startswith("COMME JE VOUD")
    assert not r["1877_18771006-OPQ.jpg"]["passes"]
