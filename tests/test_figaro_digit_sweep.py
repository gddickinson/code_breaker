"""Documented numeric tables and the hand-read numeric ads."""
import re
import json

from codebreaker.mysteries import figaro_digit_sweep as S
from codebreaker.mysteries.figaro_digit_words import HAND

H = json.loads(HAND.read_text())


def table(tid):
    return next(t for t in S.numeric_tables() if t["id"] == tid)["key"]


def decode(text, key):
    """Numbers through the table; letters printed in clear are kept."""
    return "".join(key.get(p, "?") if p.isdigit() else p.upper() for p in re.findall(r"\d+|[A-Za-z]", text))


def test_numeric_tables_are_found():
    assert len(S.numeric_tables()) >= 10


def test_chery_ad_reads_under_table_2310():
    got = decode(H["1889_18891019-CHERY.jpg"]["numbers"], table("2310"))
    assert got.startswith("SUISROME") and "NOUVELLES" in got and "ADOREE" in got.replace("EE", "EE")


def test_miromesnil_ad_reads_under_table_2308():
    got = decode(H["1877_18770412-OPQ.jpg"]["numbers"], table("2308"))
    assert got.startswith("DEMAIN") and "MIROMENIL" in got


def test_vendredi_ad_reads_under_table_2305():
    assert "VENDREDI" in decode(H["1875_18750923-5.jpg"]["numbers"], table("2305"))


def test_numbers_require_a_mostly_numeric_line():
    assert S.numbers(["Bonjour mon ami, viens vite 12"]) == []
    assert len(S.numbers([".".join(str(i) for i in range(1, 15))])) == 14
