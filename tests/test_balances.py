"""These tests cover the closing balances, both as they stood at the end of day
five and as they read after the whole stream."""

import pytest

from ledger.currency import AED, BHD
from ledger.entries import EntryType
from ledger.money import Money


def aed(amount):
    return Money.parse(amount, AED)


@pytest.mark.parametrize(
    "day, expected",
    [(1, "250.00"), (2, "-395.00"), (3, "5.00"), (4, "-205.00"), (5, "-230.00")],
)
def test_snapshot_as_known_at_the_end_of_day_five(engine, day, expected):
    assert engine.ledger.balance("ACC-001", day, 5) == aed(expected)


@pytest.mark.parametrize(
    "day, expected",
    [
        (1, "250.00"),
        (2, "225.00"),
        (3, "625.00"),
        (4, "415.00"),
        (5, "390.00"),
        (6, "390.92"),
    ],
)
def test_final_restated_closings(engine, day, expected):
    assert engine.ledger.balance("ACC-001", day, 6) == aed(expected)


def test_dinar_account(engine):
    expected = ["0.000", "0.000", "0.000", "0.000", "10.000", "10.008"]
    actual = [str(engine.ledger.balance("ACC-002", d, 6)) for d in range(1, 7)]
    assert actual == expected


def test_acceptance_criterion_one(engine):
    """
    Day two at the end of day five, before any fee, is minus 370.00.

    We accept this criterion. It leaves two things out.

    The qualifier about fees changes the answer, because by the end of day five
    three fees have been charged and the reported day two figure is minus 395.00.
    And this number appears nowhere in the printed report, since the day five
    section shows minus 395.00 and the final section shows 225.00.
    """
    before_fees = Money.zero(AED)
    for entry in engine.ledger.entries_for("ACC-001"):
        if entry.entry_type == EntryType.OVERDRAFT_FEE:
            continue
        if entry.value_date <= 2 and entry.booking_day <= 5:
            before_fees = before_fees + entry.amount
    assert before_fees == aed("-370.00")


def test_holds_are_not_subtracted_from_the_ledger_balance(engine):
    """
    There is a wrong answer sitting right next to criterion one.

    Subtracting the 200.00 authorisation hold gives minus 570.00, which looks
    plausible and is wrong. A hold never touches the ledger balance. It only
    reduces what can be spent.
    """
    assert engine.ledger.balance("ACC-001", 2, 5) != aed("-570.00")
    assert engine.ledger.balance("ACC-001", 2, 5) == aed("-395.00")
