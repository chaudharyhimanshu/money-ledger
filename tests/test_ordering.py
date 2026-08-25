"""
Arrival order is a third date to keep track of, on top of booking day and value
date.

The brief lists the events in an order that is not sorted by booking day. Event
ten books on day five but is listed after event nine, which books on day six. The
published figures must not depend on which of the two orders is used, and the
outcome of the authorisation on day five does depend on order within a single
day.
"""

from ledger.engine import Engine
from ledger.currency import AED
from ledger.money import Money
from ledger.outcomes import Status
from stream import EVENTS


def aed(amount):
    return Money.parse(amount, AED)


def final_position(events):
    engine = Engine()
    engine.replay(events)
    return {
        (account_id, day): engine.ledger.balance(account_id, day, 6)
        for account_id in ("ACC-001", "ACC-002")
        for day in range(1, 7)
    }


def test_arrival_order_and_booking_day_order_agree():
    """
    Sorting by booking day changes nothing here, but only because event ten
    belongs to the other account and that account is never overdrawn.
    """
    by_booking_day = sorted(EVENTS, key=lambda e: e.booking_day)
    assert final_position(EVENTS) == final_position(by_booking_day)


def test_the_last_arriving_event_still_earns_interest():
    """
    Capitalisation waits until the whole stream has been replayed.

    Event ten books on day five and arrives last, after the day six event. An
    engine that capitalised the moment day six closed would not yet have seen
    the dinar credit, so nothing would accrue and the account would finish at
    10.000. It accrues on both day five and day six, which is only possible if
    capitalisation waited.
    """
    engine = Engine()
    engine.replay(EVENTS)
    schedule = engine.interest_schedule["ACC-002"]
    assert [str(x) for x in schedule[4:]] == ["0.004", "0.004"]
    assert str(engine.ledger.balance("ACC-002", 6, 6)) == "10.008"


def test_the_authorisation_outcome_depends_on_order_within_the_day():
    """
    Both the backdated debit and the authorisation book on day five, and the
    order the brief gives puts the debit first. Reverse them and available reads
    465.00 and the authorisation is approved.
    """
    swapped = list(EVENTS)
    debit_at = next(i for i, e in enumerate(swapped) if e.event_id == "E7")
    auth_at = next(i for i, e in enumerate(swapped) if e.event_id == "E8")
    swapped[debit_at], swapped[auth_at] = swapped[auth_at], swapped[debit_at]

    engine = Engine()
    engine.replay(swapped)
    outcome = next(o for o in engine.outcomes if o.event_id == "E8")
    assert outcome.status == Status.APPLIED
    assert engine.holds.is_known("Auth-B")


def test_replaying_the_same_event_twice_is_refused():
    engine = Engine()
    try:
        engine.replay(list(EVENTS) + [EVENTS[0]])
    except ValueError as error:
        assert "duplicate event id" in str(error)
    else:
        raise AssertionError("a repeated event id should have been refused")
