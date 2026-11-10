"""Round 66: the table 2402 family."""
import json

from codebreaker.mysteries import figaro_2119 as T
from codebreaker.mysteries import figaro_2402 as F


def test_ads_transcribed_and_key():
    a = F.ads()
    assert len(a) == 10 and all((T.OUT / "images" / i).exists() for i in a)
    assert F.key2402()["M"] == "E"


def test_readings_and_recorded_result():
    k = F.key2402()
    assert " ".join(T.decode(F.ads()["1889_18890109-2F.jpg"], k)).startswith("TIMBRE MAL MIS PAR")
    r = json.loads(F.RESULT.read_text())
    assert len(r["passed"]) == 10 and all(x["rank"] == 1 for x in r["rows"])
