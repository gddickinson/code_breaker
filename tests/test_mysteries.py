"""Source data integrity: if these fail, a downloaded ciphertext has changed."""
from codebreaker.mysteries import beale, dagapeyeff, kryptos, tamam


def test_beale_counts_match_published():
    c = beale.ciphers()
    assert len(c["B1"]) == 520 and len(c["B3"]) == 618


def test_beale2_decodes_with_declaration():
    b2 = beale.decode(beale.ciphers()["B2"], beale.initials("declaration.txt")).lower()
    assert b2.startswith("iha") and "fourmiles" in b2


def test_kryptos_sections():
    s = kryptos.sections()
    assert {k: len(v) for k, v in s.items()} == {"K1": 63, "K2": 369, "K3": 336, "K4": 97}
    assert s["K4"][21:25] == "FLRV" and s["K4"][63:69] == "NYPVTT" and s["K4"][69:74] == "MZFPK"


def test_dagapeyeff_length():
    assert len(dagapeyeff.digits()) == 395


def test_tamam_length():
    assert len(tamam.CODE) == 44


def test_verdict_rejects_structure_without_text():
    from codebreaker.validation import verdict

    pc = {"mean": 1.0, "solved_score": -4.1, "true_coverage": 0.7}
    assert verdict(pc, 9.0, 1, "QXZJKVBQXZJKVBQXZJ", -5.2).startswith("Structure only")
    assert verdict({**pc, "mean": 0.1}, 9.0, 1, "X", -5.2).startswith("Inconclusive")
    assert verdict(pc, 9.0, 1, "THEQUESTIONWASWHETHERTHEMANWOULDRETURNBEFOREEVENING", -4.0).startswith("Readable")


def test_phaistos_published_counts():
    from codebreaker.mysteries.scriptlab import phaistos

    seq = [s for w in phaistos() for s in w]
    assert len(seq) == 241 and len(set(seq)) == 45


def test_beale_last_letter_control_finds_planted_key():
    from codebreaker.mysteries.beale_forensics import rule_control

    r = rule_control()
    assert r["found"] and r["z"] > 8


def test_dagapeyeff_is_a_square():
    from codebreaker.mysteries.dagapeyeff import digits, pairs_of

    d = digits()
    assert len(pairs_of(d[:-3])) == 196


def test_k4_layered_control_recovers_planted_order():
    from codebreaker.mysteries.kryptos_layers import control

    assert control()["found"]


def test_tamam_mnemonic_control():
    from codebreaker.mysteries.tamam_mnemonic import control

    assert control()["success"]


def test_liber_primus_known_pages_are_recovered():
    from codebreaker.mysteries.liber_primus import best, pages, to_latin

    p = pages()
    assert "PARABLE" in to_latin(best(p[57])[2].tolist())
    assert "DEEPWEB" in to_latin(best(p[56])[2].tolist())


def test_voynich_generators_preserve_substitution_entropy():
    from codebreaker.mysteries.voynich_generators import latin_words, measure, monoalpha

    assert abs(measure(latin_words(4000, 1))["h2"] - measure(monoalpha(4000, 1))["h2"]) < 1e-6


def test_pigeon_message_structure():
    from codebreaker.mysteries.pigeon import groups, text

    g = groups()
    assert len(g) == 27 and g[0] == g[-1] == "AOAKN" and len(text()) == 125


def test_hunter_reverse_transforms_are_permutations():
    from codebreaker.mysteries.hunter import transform

    seq = list(range(37))
    for s in ("reverse_columns", "reverse_undo", "columns", "undo_columns"):
        assert sorted(transform(seq, s, "6")) == seq


def test_narrow_region_encoder_correlates():
    from codebreaker.mysteries.beale_drift import encode, measure
    from codebreaker.text import to_ints
    from codebreaker.validation import sample_plaintext

    doc = to_ints(sample_plaintext(1000, "en", 3))
    plain = to_ints(sample_plaintext(300, "en", 4))
    assert measure(encode(plain, doc, 15, 0.05, 1))["lag1"] > 0.3


def test_liber_running_key_control():
    from codebreaker.mysteries.liber_keys import control
    from codebreaker.mysteries.liber_primus import pages

    p = pages()
    assert control(p, [("page 0", p[min(p)])])["recovered"]


def test_word_score_prefers_english():
    from codebreaker.segment import word_score

    assert word_score("THEMANWENTHOMEBEFOREITWASDARK") > word_score("QJXZVKWQPLMZXJQKVZPWLKXQZJVBM")


def test_high_word_coverage_overrides_a_low_quadgram_score():
    from codebreaker.validation import verdict

    pc = {"mean": 1.0, "solved_score": -3.9, "true_coverage": 0.7}
    assert verdict(pc, 9.0, 1, "THEQUESTIONWASWHETHERTHEMANWOULDRETURNBEFOREEVENING", -4.6).startswith("Readable")


def test_figaro_plain_ads_are_recognised():
    from codebreaker.mysteries.figaro_hunt import already_plain

    assert already_plain("VOUSAVEZELEVE", "VOUSAVEZELEVE") == 1.0
    assert already_plain("QFGTWMAZ", "VOUSAVEZ") < 0.5


def test_figaro_documented_systems_decode_known_samples():
    from codebreaker.mysteries.figaro_keys import A, NOW, shift, vig

    assert shift("SJFORVFUPJ", 25, A) == "RIENQUETOI"
    assert vig("UZIVGRIXCPIHCFSHPYUQOSIV", "CEAD", NOW) == "SUISENITALIEABSENTUNMOIS"


def test_figaro_tables_parse_and_kp_table_reads():
    from codebreaker.mysteries.figaro_keys import TABLES

    t = {x["id"]: x for x in TABLES}
    assert len(TABLES) >= 50 and "KP" in t["1108"]["users"]
    assert "".join(t["1108"]["map"][c] for c in "DVPSH") == "VOILA"


def test_figaro_word_systems():
    from codebreaker.mysteries.figaro_keys import word_systems

    s = dict(word_systems(["ERTTEL", "SIUS"]))
    assert s["mirror words"] == "LETTRESUIS"
    assert dict(word_systems(["BAVONJOUR"]))["remove Javanais AV"] == "BONJOUR"
    assert dict(word_systems(["TAHBEC"]))["every second letter from first"] == "THE"
