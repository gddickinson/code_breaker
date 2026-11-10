"""Round 47: the letter-digit family is the table 2119 correspondence."""
import json

from codebreaker.mysteries import figaro_2119 as T


def test_key_includes_inferred_r():
    k = T.key2119()
    assert k["R"] == "O" and len(k) >= 20


def test_transcribed_ads_read_bilingually():
    d = json.loads(T.FAMILY.read_text())
    k = T.key2119()
    assert " ".join(T.decode(d["checked_screen"]["1884_18840608-N.jpg"], k)).startswith("NO MY DEAR")
    assert "MA FEMME ADOREE" in " ".join(T.decode(d["ads"]["1882_18820311-7.jpg"], k))


def test_shuffled_copy_reads_much_less():
    import random

    t = json.loads(T.FAMILY.read_text())["ads"]["1885_18850216-R.jpg"]
    k = T.key2119()
    rnd = random.Random(1)
    assert T.share(t, k) > 2 * max(T.share(T.shuffled(t.upper(), rnd), k) for _ in range(50))


def test_recorded_result():
    r = json.loads(T.RESULT.read_text())
    assert len(r["new_members"]) >= 4 and all(x["rank"] == 1 for x in r["rows"] if x["passes"])
    assert len(r["screen_passed"]) >= 20 and r["screen_bar"] < 2e-4
