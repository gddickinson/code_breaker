"""Round 43: transcribed re-ranking and tables across writers."""
import json

from codebreaker.mysteries import figaro_rerank as R
from codebreaker.mysteries.figaro_documented import apply, systems


def test_transcription_lists_cover_all_eighteen():
    d = R.DATA
    names = set(d["letters"]) | set(d["plain_abbreviated"]) | set(d["with_digits"])
    assert len(names) == 18
    for n in names:
        assert (R.OUT / "images" / n).exists()


def test_documented_tables_read_the_two_new_ads():
    s = {x["id"]: x for x in systems()}
    five = " ".join(apply(s["2217"], w.upper()) for w in R.DATA["letters"]["1882_18820701-5.jpg"].split())
    assert five == "AIME MOI UN PEU JE TAIME ET DESIRE TANT TE BAISER"
    assert apply(s["2201"], "ZFKQFKEPKEHG") == "ATOITOUJOURS"


def test_recorded_best_of_all_systems_null():
    rows = {r["image"]: r for r in json.loads(R.RESULT.read_text())["rows"]}
    assert rows["1882_18820701-5.jpg"]["any"]["null_p"] <= 0.007
    assert rows["1883_18830304-X.jpg"]["any"]["null_p"] > 0.05
