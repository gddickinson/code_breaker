"""Round 45: the V. T. A. key after 1877, and ads grouped by key."""
import json

from codebreaker.mysteries import figaro_families as F
from codebreaker.mysteries import figaro_vta as V
from codebreaker.mysteries import figaro_vta_sweep as S
from codebreaker.mysteries.figaro_documented import apply, systems


def test_tokens_drop_plain_words_and_numbers():
    assert S.tokens("You are such a p8ml y82t17 1877") == ["p8ml", "y82t17"]


def test_valentin_ads_decode_with_the_1877_key():
    tr = json.loads((F.OUT / "sweep_transcription.json").read_text())["ads"]
    k = V.full_key()
    dec = lambda img: " ".join(V.decode(w, k) for w in tr[img]["cipher"].split())
    assert dec("1878_18781226-Valentin.jpg").startswith("deep in snow")
    assert "will send letter" in dec("1879_18790114-Valentin.jpg")


def test_berthe_correspondence_under_table_2217():
    tr = json.loads((F.OUT / "sweep_transcription.json").read_text())["ads"]
    t = {s["id"]: s for s in systems()}["2217"]
    last = " ".join(apply(t, w.upper()) for w in tr["1882_18821224-5.jpg"]["cipher"].split())
    assert "TE BAISE PARTOUT MA BERT" in last
    fam = F.run()["families"]["2217"]
    assert len(fam["ads"]) == 5 and not fam["common_system"] and fam["span"] == ["1881-10-12", "1882-12-24"]


def test_caesar_table_is_flagged_common():
    assert "1001" in F.common_tables()
