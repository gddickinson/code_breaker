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


def test_missing_symbols_inferred_and_held_out():
    r = json.loads(T.RESULT.read_text())
    m = r["missing"]
    assert m["fitted_all"]["P"] == "U" and m["fitted_all"]["H"] == "W"
    assert m["held_out_gain"] > m["random_gain_max"] and m["p"] <= 0.01


def test_extended_readings_and_timeline():
    r = json.loads(T.RESULT.read_text())
    assert r["readings_extended"]["1884_18840608-N.jpg"].startswith("NO MY DEAR WIFE I DONT FORGET YOU")
    dates = [e["date"] for e in r["timeline"]]
    assert dates == sorted(dates) and len(dates) >= 45 and len(r["checked"]) == 25


def test_fit_missing_picks_the_letter_that_makes_words():
    key = {"A": "L", "B": "O", "C": "E"}
    assert T.fit_missing(key, ["ABVC"], {"V": list("QVXZ")})["V"] == "V"  # only LOVE is a word


def test_symbol_one_is_b():
    assert T.full_key()["1"] == "B"
    st = T.sign_test_b()
    assert st["better"] >= 10 and st["worse"] <= 2 and st["p"] < 0.01


def test_rescreen_spot_checks_read_with_full_key():
    d = json.loads(T.FAMILY.read_text())["checked_rescreen"]
    k = T.full_key()
    assert "DEAR LOVED WIFE MISS YOU SO MUCH" in " ".join(T.decode(d["1882_18820309-7.jpg"], k))
    assert " ".join(T.decode(d["1882_18821209-42.jpg"], k)).startswith("MERCI MADAME")
    assert not set(d) & set(T.texts())  # spot checks are kept out of the fit


def test_full_timeline_and_mentions():
    tl = T.full_timeline()
    assert tl["ads"] >= 75 and len(tl["signatures"]) >= 20
    dates = [e["date"] for e in tl["timeline"]]
    assert dates == sorted(dates)
    assert tl["mentions"]["madame C. L."] == ["1882-12-09"] and "1884-02-27" in tl["mentions"]["bal"]
    assert all(e["transcribed"] for e in tl["timeline"] if e["image"] in json.loads(T.FAMILY.read_text())["checked_rescreen"])


def test_residuals_read_and_tilly_named():
    d = json.loads(T.FAMILY.read_text())["checked_residual"]
    k = T.full_key()
    assert "MA DOUCE TILLY" in " ".join(T.decode(d["1883_18830609-42.jpg"], k))
    round54 = [t for i, t in d.items() if "PAUL" not in i and not (i.endswith("-E.jpg") and i[:4] in ("1884", "1885", "1886") and i not in ("1884_18840323b-E.jpg", "1886_18860202-E.jpg", "1886_18861126-E.jpg"))]
    assert len(round54) == 12 and all(T.share(t, k) > 0.5 for t in round54)


def test_paul_and_e_ads_read():
    d = json.loads(T.FAMILY.read_text())["checked_residual"]
    k = T.full_key()
    assert " ".join(T.decode(d["1882_18820608-PAUL.jpg"], k)).startswith("OUR LITTLE GIRL")
    assert "MUST BE BACK BEFORE END YEAR" in " ".join(T.decode(d["1884_18841220-E.jpg"], k))


def test_t_and_42_ads_and_key_history():
    d = json.loads(T.FAMILY.read_text())["checked_t42"]
    k = T.full_key()
    assert "LOVE YOU ALL MY HEART MY WIFE" in " ".join(T.decode(d["1882_18821012-42.jpg"], k))
    early, late = d["1882_18820204-42.jpg"], d["1882_18821012-42.jpg"]
    assert "09j6 g9i" in early and "orj6 grp" in late  # 9 and i early, r and p later, both 'love you'
    assert T.decode("09j6 g9i", k) == T.decode("orj6 grp", k)


def test_early_leads_transcribed_and_read():
    d = json.loads(T.FAMILY.read_text())["checked_early"]
    k = T.full_key()
    assert len(d) == 12
    for img, t in d.items():
        assert T.share(t, k) >= 0.45, img
    assert "TILLY" in " ".join(T.decode(d["1883_18831226-J.jpg"], k))
