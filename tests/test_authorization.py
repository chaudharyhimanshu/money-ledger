"""These tests cover authorisations, settlements, and what a hold does to the balance."""

import pytest

from ledger.currency import AED
from ledger.engine import Engine
from ledger.entries import EntryType
from ledger.events import Authorization, Credit, Debit, Settlement
from ledger.holds import HoldReleased
from ledger.money import Money
from ledger.outcomes import Status


def aed(amount):
    return Money.parse(amount, AED)


def outcome_for(engine, event_id):
    return next(o for o in engine.outcomes if o.event_id == event_id)


def test_auth_a_was_approved(engine):
    assert outcome_for(engine, "E3").status == Status.APPLIED


@pytest.mark.parametrize(
    "day, ledger_balance, available",
    [(2, "250.00", "50.00"), (3, "650.00", "450.00")],
)
def test_a_hold_reduces_what_can_be_spent_but_not_what_is_owned(
    engine, day, ledger_balance, available
):
    """
    This is acceptance criterion five, with the numbers filled in.

    The criterion is written as a claim about Auth-B, and Auth-B is declined, so
    strictly it never comes into effect. The property it describes is real
    though, and Auth-A shows it twice while its hold is live.
    """
    assert engine.ledger.balance("ACC-001", day, day) == aed(ledger_balance)
    assert engine.available("ACC-001", day) == aed(available)


def test_auth_b_is_declined(engine):
    outcome = outcome_for(engine, "E8")
    assert outcome.status == Status.DECLINED


def test_auth_b_is_judged_against_the_balance_at_the_time(engine):
    """
    The balance at the time was minus 155.00, not minus 230.00.

    Minus 230.00 is day five's closing balance once the fee sweep has run, and
    the sweep runs at the end of the day, after this decision has been taken. The
    decline holds either way, but only one of those two numbers existed when the
    question was actually asked, and the reason recorded on the outcome has to be
    the one that did.

    Asking the finished engine what day five's available balance is gives the
    later figure, which is correct and is not the same question.
    """
    reason = outcome_for(engine, "E8").reason
    assert "-155.00" in reason
    assert "-245.00" in reason

    # Ask the same question again after the fees exist and you get a different
    # answer that is also correct.
    assert engine.available("ACC-001", 5) == aed("-230.00")


def test_a_declined_authorisation_places_no_hold(engine):
    assert not engine.holds.is_known("Auth-B")


def test_settlement_against_an_unknown_authorisation_is_refused(engine):
    outcome = outcome_for(engine, "E6")
    assert outcome.status == Status.REJECTED
    assert outcome.is_error


def test_the_refused_settlement_moved_no_money(engine):
    assert engine.ledger.entries_by_event("E6") == []
    # Day four reads 465.00. It would read 285.00 if the 180.00 had gone out.
    assert engine.ledger.balance("ACC-001", 4, 4) == aed("465.00")


def test_clearing_for_less_than_authorised_releases_the_rest(engine):
    # The hold was 200.00 and the clearing was 185.00. The authorisation is
    # finished and the remaining 15.00 goes back, rather than staying open for a
    # second clearing.
    released = [
        r for r in engine.holds.records if isinstance(r, HoldReleased)
    ]
    assert [r.amount for r in released] == [aed("15.00")]
    assert engine.holds.outstanding("Auth-A", AED) == Money.zero(AED)
    assert engine.holds.state("Auth-A", AED) == "settled"


def test_a_settlement_posts_even_with_no_money_behind_it():
    """
    Settlements never consult the available balance.

    A hold does not move money and does not give its authorisation any claim ahead
    of anything else, so there is no coverage that could have been lost. The commitment was made when the authorisation was approved, and a
    clearing reports that money has moved rather than asking whether it may.
    """
    events = [
        Credit(
            event_id="C1", arrival_index=0, booking_day=1, value_date=1,
            account_id="ACC-001", amount=aed("100.00"),
        ),
        Authorization(
            event_id="C2", arrival_index=1, booking_day=1, value_date=1,
            account_id="ACC-001", amount=aed("100.00"), auth_id="Auth-X",
        ),
        Debit(
            event_id="C3", arrival_index=2, booking_day=2, value_date=2,
            account_id="ACC-001", amount=aed("90.00"),
        ),
        Settlement(
            event_id="C4", arrival_index=3, booking_day=3, value_date=3,
            account_id="ACC-001", amount=aed("100.00"), auth_id="Auth-X",
        ),
    ]
    engine = Engine()
    engine.replay(events)

    assert outcome_for(engine, "C2").status == Status.APPLIED
    # By the time the clearing arrives there is nothing like enough to cover it.
    assert outcome_for(engine, "C4").status == Status.APPLIED
    settlement = engine.ledger.entries_by_event("C4")[0]
    assert settlement.entry_type == EntryType.SETTLEMENT
    assert settlement.amount == aed("-100.00")


def test_debits_are_not_checked_against_available_funds(engine):
    """
    Only authorisations are refused for lack of funds.

    Apply the same test to debits and the backdated debit on day five is refused,
    and nothing else in this replay happens.
    """
    assert outcome_for(engine, "E7").status == Status.APPLIED
    assert engine.ledger.balance("ACC-001", 2, 5).is_negative
