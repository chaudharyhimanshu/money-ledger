"""
The printed report is pinned against a stored copy. Regenerate the stored copy
with:

    ./.venv/bin/python run.py > tests/expected_report.txt

and read the diff before committing it. A change here is either a formatting
change or a change to the numbers. Work out which one it is before you commit.
"""

import pathlib

from ledger.engine import Engine
from ledger.report import render
from stream import EVENTS

EXPECTED = pathlib.Path(__file__).parent / "expected_report.txt"


def test_report_matches_the_stored_copy():
    engine = Engine()
    engine.replay(EVENTS)
    # Both sides are stripped of trailing blank lines, since the report ends on
    # one and print adds another.
    assert render(engine, EVENTS).rstrip("\n") == EXPECTED.read_text().rstrip("\n")


def test_every_day_and_both_accounts_appear(engine):
    report = render(engine, EVENTS)
    for day in range(1, 7):
        assert f"DAY {day}" in report
    # The dinar account has nothing at all until day five and still has to be
    # reported on each of the first four days.
    assert report.count("ACC-002") >= 7


def test_the_refused_settlement_is_reported_as_an_error_on_day_four(engine):
    report = render(engine, EVENTS)
    day_four = report.split("DAY 4")[1].split("DAY 5")[0]
    assert "Auth-Z" in day_four
    assert "does not leave the account" in day_four


def test_the_decline_is_reported_under_authorisations_not_errors(engine):
    """
    A refused settlement is the system finding something wrong. A refused
    authorisation is the system working. Reporting both as errors would be
    misleading, so the decline appears alongside the other authorisation states.
    """
    report = render(engine, EVENTS)
    day_five = report.split("DAY 5")[1].split("DAY 6")[0]
    acc_one = day_five.split("ACC-002")[0]
    authorisations = acc_one.split("authorisations")[1].split("errors")[0]
    assert "Auth-B   declined" in authorisations
    assert "errors" in acc_one and "none" in acc_one.split("errors")[1]


def test_restatements_are_shown_on_the_day_they_become_known(engine):
    report = render(engine, EVENTS)
    day_five = report.split("DAY 5")[1].split("DAY 6")[0]
    assert "restated by events that arrived today" in day_five
    assert "Day 2   250.00  becomes  -395.00" in day_five
