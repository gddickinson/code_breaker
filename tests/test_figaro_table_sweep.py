"""Round 44: documented tables on every unsolved letter ad."""
import json

import numpy as np

from codebreaker.languages import model
from codebreaker.mysteries import figaro_table_sweep as T
from codebreaker.mysteries import figaro_vta as V
from codebreaker.mysteries.figaro_documented import apply, systems
from codebreaker.mysteries.figaro_keys import OUT


def test_best_score_finds_the_right_table():
    maps, quad = T.table_arrays(), model("fr")["table"]
    ct = np.array([ord(c) - 65 for c in "LQUHUIQSGVHSEHBLQUHHBFHDQCHBLGBBHKLQDHC"], np.int64)
    s, k = T.best_score(ct, maps, quad)
    assert T.TABLES[k]["id"] == "2217"
    null = T.null_scores(ct, maps, quad, 500, 1)
    assert s > null.max()


def test_transcribed_sweep_ads_read():
    tr = json.loads((OUT / "sweep_transcription.json").read_text())["ads"]
    s = {x["id"]: x for x in systems()}
    for image, ad in tr.items():
        assert (OUT / "images" / image).exists()
    read = lambda img: " ".join(apply(s[tr[img]["system"]], w.upper()) for w in tr[img]["cipher"].split())
    assert read("1896_18960909-57E.jpg") == "RUPTURE TT EXPLIC"
    assert read("1881_18810731-LB48.jpg").startswith("VALERY CAUX RUE DU HAVRE MAISON CAPITAINE")
    val = " ".join(V.decode(w, V.full_key()) for w in tr["1878_18781226-Valentin.jpg"]["cipher"].split())
    assert "lettet will write" in val or "letter will write" in val


def test_recorded_sweep_counts():
    r = json.loads(T.RESULT.read_text())
    assert r["bonferroni"] >= 15 and r["fdr"] >= r["bonferroni"]
    assert r["rows"][0]["p"] <= r["bonferroni_bar"]
