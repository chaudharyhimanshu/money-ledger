"""
Day two has more than one closing balance and each of them is correct.

It reads 250.00 while day two is the present, minus 395.00 once a debit dated back
to it arrives on day five, and 225.00 after that debit is reversed on day six.
Each of them is what was true given what had been heard by that day, and none of
them corrects the others.

A balance query that took only one day could produce the last of these and nothing
else. The earlier figures would only exist if something printed them while the
replay was in the right place, and the report would then depend on how the code
happens to run.
"""

import pytest

from ledger.money import Money
from ledger.currency import AED


def aed(amount):
    return Money.parse(amount, AED)


@pytest.mark.parametrize(
    "known_as_of, expected",
    [
        (2, "250.00"),   # day two, while day two is still the present
        (3, "250.00"),
        (4, "250.00"),   # the backdated debit has not arrived yet
        (5, "-395.00"),  # E7 lands, dated back to day two, and the fee follows
        (6, "225.00"),   # E9 reverses it, but the fee stays
    ],
)
def test_day_two_seen_from_each_later_day(engine, known_as_of, expected):
    assert engine.ledger.balance("ACC-001", 2, known_as_of) == aed(expected)


def test_the_backdated_debit_is_invisible_before_it_arrives(engine):
    # E7 books on day five. Nothing asked from day four can see it, no matter
    # which day is being asked about.
    for value_date in range(1, 5):
        as_known_then = engine.ledger.balance("ACC-001", value_date, 4)
        assert as_known_then.is_positive


def test_fee_entries_record_both_days(engine):
    # This fee is dated to day two and booked on day five, which is why entries
    # carry two dates. Keeping only the value date would make it impossible to say
    # what the account looked like before the assessment ran.
    fees = [e for e in engine.ledger.entries if e.entry_type == "overdraft_fee"]
    assert {(f.value_date, f.booking_day) for f in fees} == {(2, 5), (4, 5), (5, 5)}
