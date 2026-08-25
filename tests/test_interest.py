"""
The brief calls one rule non negotiable: the rounded daily accruals must sum
exactly to the capitalised total. Two methods satisfy that and they disagree by a
fils, so the rule does not decide between them. Both are implemented and the
invariant is asserted under each.
"""

import pytest

from ledger.currency import AED, BHD
from ledger.engine import Engine
from ledger.interest import (
    INDEPENDENT,
    RESIDUAL,
    accrual_schedule,
    capitalisation,
)
from ledger.money import Money
from ledger.rounding import round_half_up
from stream import EVENTS

CLOSINGS = [25_000, 22_500, 62_500, 41_500, 39_000, 39_000]


def closings(currency=AED):
    return [Money(minor=m, currency=currency) for m in CLOSINGS]


def test_the_daily_schedule(engine):
    schedule = [str(x) for x in engine.interest_schedule["ACC-001"]]
    assert schedule == ["0.10", "0.09", "0.25", "0.17", "0.15", "0.16"]


def test_capitalised_total(engine):
    total = capitalisation(engine.interest_schedule["ACC-001"], AED)
    assert str(total) == "0.92"


@pytest.mark.parametrize("strategy", [RESIDUAL, INDEPENDENT])
def test_dailies_sum_exactly_to_the_total_under_either_method(strategy):
    schedule = accrual_schedule(closings(), AED, strategy)
    assert capitalisation(schedule, AED) == sum(
        schedule[1:], schedule[0]
    )


def test_the_two_methods_disagree_by_one_fils():
    """
    Residual carry gives 0.92 and independent rounding gives 0.93.

    The true accrual is 0.918, so 0.92 is the correctly rounded figure and 0.93
    pays out more than is owed. Independent rounding errs the same way every
    time, because 0.166 rounds up on every day it appears.
    """
    residual = capitalisation(accrual_schedule(closings(), AED, RESIDUAL), AED)
    independent = capitalisation(
        accrual_schedule(closings(), AED, INDEPENDENT), AED
    )
    assert str(residual) == "0.92"
    assert str(independent) == "0.93"


def test_the_whole_replay_under_independent_rounding():
    # The only figure that moves is the interest.
    engine = Engine(interest_strategy=INDEPENDENT)
    engine.replay(EVENTS)
    assert str(engine.ledger.balance("ACC-001", 6, 6)) == "390.93"
    assert str(engine.ledger.balance("ACC-001", 5, 6)) == "390.00"


def test_only_days_that_close_above_zero_earn_anything():
    balances = [
        Money.parse("100.00", AED),
        Money.zero(AED),
        Money.parse("-100.00", AED),
    ]
    schedule = accrual_schedule(balances, AED, INDEPENDENT)
    assert [x.minor for x in schedule] == [4, 0, 0]


def test_an_exact_half_rounds_up():
    """
    The real stream never produces a tie.

    Every accrual in it lands on 0.100, 0.090, 0.250, 0.166 or
    0.156, so half up and half to even would give identical answers throughout
    and the choice is never exercised. A balance of 12.50 accrues exactly 0.005
    and does exercise it.
    """
    assert round_half_up(5_000, 10_000) == 1
    twelve_fifty = [Money.parse("12.50", AED)]
    assert accrual_schedule(twelve_fifty, AED, INDEPENDENT)[0].minor == 1


def test_interest_does_not_earn_interest_on_the_day_it_is_paid(engine):
    """
    Day six accrues on 390.00, not on 390.92.

    The schedule is worked out from the balances first and the credit is written
    afterwards, so the credit cannot be inside its own accrual base.
    """
    day_six_accrual = engine.interest_schedule["ACC-001"][5]
    assert day_six_accrual == Money(minor=round_half_up(39_000 * 4, 10_000), currency=AED)


def test_the_dinar_account(engine):
    schedule = engine.interest_schedule["ACC-002"]
    assert [str(x) for x in schedule] == [
        "0.000", "0.000", "0.000", "0.000", "0.004", "0.004",
    ]
    assert str(capitalisation(schedule, BHD)) == "0.008"
