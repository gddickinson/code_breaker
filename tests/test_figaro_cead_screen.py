import json
import random

from codebreaker.mysteries import figaro_cead_screen as S


def test_read_finds_running_key_and_planted_text():
    s, mode, plain = S.read(["NZNGK", "TAV", "CAAQV"])
    assert plain == "LUNDIPASAVANT" and mode == "running, phase 0"
    blocks = S.planted([[12, 14]], seed=5, noise=0.0)[0]
    s, mode, plain = S.read(blocks)
    assert s > S.read(S.shuffled(blocks, random.Random(1)))[0]


def test_stage_two_can_reach_the_bar():
    res = json.loads(S.RESULT.read_text())
    for part in (res, res["all_keys"]):
        assert 1 / (max(S.STAGE2, int(2 / part["bar"])) + 1) < part["bar"]


def test_screen_finds_only_documented_writers():
    res = json.loads(S.RESULT.read_text())
    assert res["ads"] == 284 and res["control"]["recovered"] >= 18
    assert all(("VE3" in r["image"] or "CH" in r["image"]) for r in res["passed"])
    x = res["all_keys"]
    assert x["ads"] == 643 and {(r["key"], r["image"][-6:-4]) for r in x["passed"]} <= {("CD", "25"), ("CEAD", "E3"), ("CEAD", "CH")}
