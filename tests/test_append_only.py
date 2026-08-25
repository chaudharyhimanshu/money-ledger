"""
Nothing is ever changed or removed, only added.

The rule forbids editing or deleting a record. It says nothing about whether an
offsetting record may be written, and writing one is the only way to correct
anything. So the overdraft fees do not survive the reversal because the ledger is
append only. They survive because the rules contain no provision for refunding a
fee.
"""

import pytest
from pydantic import ValidationError

from ledger.currency import AED
from ledger.engine import Engine
from ledger.entries import EntryType
from ledger.events import Reversal
from ledger.ledger import Ledger
from ledger.money import Money
from ledger.outcomes import Status
from stream import EVENTS


def aed(amount):
    return Money.parse(amount, AED)


def test_an_entry_cannot_be_changed(engine):
    entry = engine.ledger.entries[0]
    with pytest.raises(ValidationError):
        entry.amount = aed("1.00")


def test_the_store_offers_no_way_to_remove_anything():
    forbidden = {"update", "delete", "remove", "pop", "clear", "edit"}
    assert forbidden.isdisjoint(dir(Ledger))


def test_the_entries_view_cannot_be_used_to_reach_in(engine):
    entries = engine.ledger.entries
    assert isinstance(entries, tuple)


def test_the_reversal_leaves_the_original_in_place(engine):
    original = engine.ledger.entries_by_event("E7")
    assert len(original) == 1
    assert original[0].amount == aed("-620.00")

    compensating = engine.ledger.entries_by_event("E9")
    assert len(compensating) == 1
    assert compensating[0].amount == aed("620.00")
    assert compensating[0].reverses_entry_id == original[0].entry_id
    # The compensating entry is written on day six and dated back to the day the
    # original landed on.
    assert compensating[0].booking_day == 6
    assert compensating[0].value_date == 2


def test_the_same_event_cannot_be_reversed_twice(engine):
    """
    There is no flag on the original saying it has been undone, because setting
    one would be a change. The guard has to be worked out by reading the log.
    """
    again = Reversal(
        event_id="E9-again", arrival_index=99, booking_day=6, value_date=2,
        account_id="ACC-001", reverses_event_id="E7",
    )
    engine._apply(again)
    assert engine.outcomes[-1].status == Status.REJECTED
    assert "already been reversed" in engine.outcomes[-1].reason


def test_reversing_something_that_produced_no_entries_is_refused(engine):
    # E6 was refused, so there is nothing to take back.
    nothing_there = Reversal(
        event_id="E6-rev", arrival_index=98, booking_day=6, value_date=4,
        account_id="ACC-001", reverses_event_id="E6",
    )
    engine._apply(nothing_there)
    assert engine.outcomes[-1].status == Status.REJECTED
    assert "nothing to reverse" in engine.outcomes[-1].reason


def test_a_reversal_reverses_every_entry_the_event_produced():
    """
    One event produced three entries, so the reversal produces three compensating
    entries.

    The ten dinar credit is paid in three instalments, so one event can produce
    more than one entry and a reversal cannot assume it will find a single one.
    """
    engine = Engine()
    engine.replay(EVENTS)
    assert len(engine.ledger.entries_by_event("E10")) == 3

    undo = Reversal(
        event_id="E10-rev", arrival_index=97, booking_day=6, value_date=5,
        account_id="ACC-002", reverses_event_id="E10",
    )
    engine._apply(undo)
    compensating = engine.ledger.entries_by_event("E10-rev")
    assert len(compensating) == 3
    assert [c.amount.minor for c in compensating] == [-3_334, -3_333, -3_333]
    assert sum(c.amount.minor for c in compensating) == -10_000


def test_the_fees_survive_the_reversal(engine):
    """
    Acceptance criterion six says balances and fees return to their earlier
    values. They do not.

    Strip the three fees out and the restated balances are the figures from before
    the backdated debit arrived, so the principal comes back. The criterion fails
    only because of the 75.00 of fees.
    """
    fees = [
        e for e in engine.ledger.entries_for("ACC-001")
        if e.entry_type == EntryType.OVERDRAFT_FEE
    ]
    assert len(fees) == 3

    without_fees = Money.zero(AED)
    for entry in engine.ledger.entries_for("ACC-001"):
        if entry.entry_type in (EntryType.OVERDRAFT_FEE, EntryType.INTEREST):
            continue
        if entry.value_date <= 4:
            without_fees = without_fees + entry.amount
    assert without_fees == aed("465.00")
    assert engine.ledger.balance("ACC-001", 4, 6) == aed("415.00")
