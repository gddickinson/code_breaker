"""Round 41: the documented C. H. key on the writer's unsolved ads."""
import json

from codebreaker.mysteries import figaro_ch as C


def test_key_round_trip_and_no_w():
    assert "W" not in C.A and len(C.A) == 25
    p = "TACHEZEVITERSANSREFUSER"
    assert C.decrypt(C.encrypt(p)) == p


def test_block_readings_under_restarting_key():
    assert C.decrypt("LIPDTX") == "JEPARS" and C.decrypt("NIHYKY") == "LEHUIT"
    assert C.decrypt("VECKGDEZKYEUUENVTIFYUIZ").startswith("TACHEZEVITERSANSREFUSE")


def test_slip_recovers_a_dropped_letter():
    p = "CEQUEJAIFAITANOTREENFANT"
    ct = C.encrypt(p)
    ct = ct[:10] + ct[11:]
    got = C.search(ct, phases=(0,))
    expect = p[:10] + p[11:]
    assert got["plain"].endswith("NOTREENFANT")  # the slip's exact place can be off by a letter or two
    assert sum(a == b for a, b in zip(got["plain"], expect)) / len(expect) >= 0.8


def test_transcription_blocks_use_the_alphabet():
    for ad in C.DATA["ads"].values():
        for b in ad["blocks"]:
            assert set(b) <= set(C.A)


def test_recorded_strict_result():
    r = json.loads(C.RESULT.read_text())["strict"]
    assert r["control"]["recovered"] / r["control"]["trials"] >= 0.9
    passed = {x["image"] for x in r["rows"] if x["gates"]["passed"]}
    assert "1886_18860629-CH.jpg" in passed and "1882_18821111-CH.jpg" not in passed
