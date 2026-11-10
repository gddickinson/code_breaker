from codebreaker.mysteries import figaro_style_gate as G


def test_style_measured_and_control_matches_size():
    words, key = G.family("2119")
    st = G.style(words, key)
    assert st["words"] == 1719 and 0.2 < st["p_en"] < 0.3 and 0.1 < st["p_abbrev"] < 0.2
    flat = [w for ws in words.values() for w in ws]
    pw, pt = G.planted_style(st)(flat)
    assert [len(w) for w in pw] == [len(w) for w in pt.split()] and len(pw) == len(flat)
    assert len({c for w in pw for c in w}) <= len({c for w in flat for c in w}) + 2
