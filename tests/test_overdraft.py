"""
A fee is dated to the day it is charged for, so it lands inside that day's own
closing balance. Read literally the rule never finishes: day two closes at minus
370.00, the fee takes it to minus 395.00, which is still negative, which earns
another fee. A day that already carries a fee cannot earn a second one, and days
are swept in ascending order, so a fee charged to an earlier day is already
counted by the time the sweep reaches a later day.
"""

import pytest

from ledger.currency import AED
from ledger.engine import Engine
from ledger.entries import Entry, EntryType
from ledger.money import Money


def aed(amount):
    return Money.parse(amount, AED)


def fees(engine, account_id="ACC-001"):
    return [
        e
        for e in engine.ledger.entries_for(account_id)
        if e.entry_type == EntryType.OVERDRAFT_FEE
    ]


def test_the_backdated_debit_causes_three_fees_not_one(engine):
    """
    Acceptance criterion two says there is exactly one fee, on day two. We
    refuse that.

    The backdated debit makes day two negative and carries forward, so day four
    and day five close negative too, and each earns its own fee.
    """
    assert [f.value_date for f in fees(engine)] == [2, 4, 5]


def test_every_fee_was_assessed_on_day_five(engine):
    # All three were charged in the same sweep, the one that ran once the
    # backdated debit had been heard.
    assert {f.booking_day for f in fees(engine)} == {5}


def test_fee_amount(engine):
    assert all(f.amount == aed("-25.00") for f in fees(engine))


def test_day_three_survives_despite_the_day_two_fee(engine):
    """
    Day three closes at 5.00, not 30.00, because the day two fee carried into it.

    Had the fee been 30.00 the day would have gone negative and earned a fourth
    fee.
    """
    assert engine.ledger.balance("ACC-001", 3, 5) == aed("5.00")


def test_one_fee_per_day_at_most(engine):
    charged = [f.value_date for f in fees(engine)]
    assert len(charged) == len(set(charged))


def test_the_sweep_is_already_a_fixed_point(engine):
    # Running it again has to find nothing. If it found something, one ascending
    # pass would not be enough.
    before = len(engine.ledger.entries)
    for day in range(1, 7):
        assert engine.assess_overdrafts(day) == []
    assert len(engine.ledger.entries) == before


def test_a_fee_can_push_a_later_day_negative():
    """
    This case uses constructed data to show the cascade.

    In the real stream the cascade does not change which days earn a fee. Day
    three lands at 5.00, which is clear of zero, so assessing every day at once
    from a snapshot would give the same three fees. Here day one is only slightly
    overdrawn, day two would be positive on its own, and the day one fee takes it
    under.
    """
    engine = Engine()
    engine.ledger.append(
        Entry(
            entry_id="s1", account_id="ACC-001", booking_day=1, value_date=1,
            amount=aed("-10.00"), entry_type=EntryType.DEBIT,
            caused_by_event_id="synthetic",
        )
    )
    engine.ledger.append(
        Entry(
            entry_id="s2", account_id="ACC-001", booking_day=2, value_date=2,
            amount=aed("20.00"), entry_type=EntryType.CREDIT,
            caused_by_event_id="synthetic",
        )
    )
    # Without the cascade day two reads 10.00 and earns nothing. With it, the
    # day one fee of 25.00 takes day two to minus 15.00.
    engine.assess_overdrafts(1)
    engine.assess_overdrafts(2)
    assert [f.value_date for f in fees(engine)] == [1, 2]
    assert engine.ledger.balance("ACC-001", 2, 2) == aed("-40.00")


def test_the_dinar_account_is_never_charged(engine):
    # The dinar account never goes overdrawn. There is no published dinar
    # overdraft charge, so charging one would raise.
    assert fees(engine, "ACC-002") == []
