"""Shared test settings. Tests that need third-party data the repository does not redistribute (Didier Müller's
Le Figaro tables and ads database, Klaus Schmeh's list) are skipped, not failed, until scripts/fetch_sources.py
has downloaded it (see THIRD_PARTY.md)."""
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    outcome = yield
    exc = outcome.excinfo
    if exc and issubclass(exc[0], FileNotFoundError) and "third-party data not kept" in str(exc[1]):
        outcome.force_exception(pytest.skip.Exception(f"needs third-party data: {exc[1]}", _use_item_location=True))


NEEDS_KEY_TABLES = ("test_figaro_families.py::test_caesar_table_is_flagged_common", "test_figaro_fusion.py::test_new_candidate_transcriptions_decrypt",
                    "test_figaro_fusion.py::test_digit_solver_recovers_planted_text", "test_figaro_table_sweep.py::test_best_score_finds_the_right_table",
                    "test_mysteries.py::test_figaro_tables_parse_and_kp_table_reads")


def pytest_collection_modifyitems(config, items):
    """Tests that read Müller's key tables through figaro_keys.TABLES (empty when codes.html is absent)."""
    from codebreaker.mysteries.figaro_keys import OUT

    if (OUT / "codes.html").exists():
        return
    skip = pytest.mark.skip(reason="needs data/sources/figaro/codes.html: run python scripts/fetch_sources.py")
    for item in items:
        if any(item.nodeid.endswith(n) for n in NEEDS_KEY_TABLES):
            item.add_marker(skip)
