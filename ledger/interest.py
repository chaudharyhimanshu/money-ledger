"""
Daily interest accrual and the single credit that capitalises it.

Accruing is recognising what is owed. It touches no balance and moves no money.
Capitalising is the one entry that actually pays it. The brief asks for a daily
accrual and a single credit at the end of day six, so the six daily figures are a
breakdown of one payment worked out in a single pass at the end. Nothing is
posted and then corrected.

Day two's closing
balance is not a settled fact on day two. It reads 250.00 at the time, then minus
395.00 once a backdated debit arrives on day five, then 225.00 after that debit is
reversed on day six. There is no moment during day two at which the correct day
two accrual could have been worked out, because the balance it depends on had not
finished happening.

The brief says the rounded daily accruals must sum exactly to the capitalised
total. Two methods satisfy that and they give different answers, so the rule does
not settle it:

  independent   round each day on its own and let the total be their sum
  residual      take the correctly rounded true accrual as the total and let the
                daily figures carry the leftover forward so they add up to it

On this data the true accrual is 0.918. Independent rounding gives six figures
adding to 0.93. Residual carry gives 0.92, moving one fils on day five.

Residual carry is used. The true accrual rounds to 0.92, so independent rounding
pays out more than is owed, and it errs in the same direction every time because
0.166 rounds up every day. On a balance of 415.00 held for a year that overpays by
1.46. The brief also answers this elsewhere: the ten dinar credit has its total
fixed at 10.000 with the parts adjusted to 3.334 and 3.333 and 3.333, and
acceptance criterion seven refuses to let independently rounded parts override a
total that is already known. The same principle applied to interest gives 0.92.

Both are implemented, and the invariant is asserted under each.
"""

from typing import List

from ledger.constants import (
    DAILY_INTEREST_DENOMINATOR,
    DAILY_INTEREST_NUMERATOR,
)
from ledger.currency import Currency
from ledger.money import Money
from ledger.rounding import round_half_up

RESIDUAL = "residual"
INDEPENDENT = "independent"


def accrual_schedule(
    closings: List[Money], currency: Currency, strategy: str = RESIDUAL
) -> List[Money]:
    """
    Work out what each day contributes to the interest credit.

    closings is one balance per day, in day order. Only days that close strictly
    above zero earn anything, so a day at exactly zero contributes nothing and
    neither does an overdrawn one. The brief gives no debit interest, so the days
    this account spends overdrawn cost it a flat fee.
    """
    if strategy == INDEPENDENT:
        return [
            Money(
                minor=round_half_up(
                    balance.minor * DAILY_INTEREST_NUMERATOR,
                    DAILY_INTEREST_DENOMINATOR,
                )
                if balance.is_positive
                else 0,
                currency=currency,
            )
            for balance in closings
        ]

    if strategy != RESIDUAL:
        raise ValueError(f"unknown interest strategy {strategy!r}")

    # This runs the true accrual as an exact whole number and rounds the running
    # total each day. The daily figure posted is whatever moves the rounded
    # running total along, so the leftover fraction is carried until it amounts
    # to a whole fils.
    schedule: List[Money] = []
    exact_so_far = 0
    posted_so_far = 0
    for balance in closings:
        if balance.is_positive:
            exact_so_far += balance.minor * DAILY_INTEREST_NUMERATOR
        target = round_half_up(exact_so_far, DAILY_INTEREST_DENOMINATOR)
        schedule.append(Money(minor=target - posted_so_far, currency=currency))
        posted_so_far = target
    return schedule


def capitalisation(schedule: List[Money], currency: Currency) -> Money:
    """
    The single credit, which is by construction the sum of the daily accruals.

    It adds the daily figures up instead of recomputing from the balances, so a
    later change here cannot break the rule the brief calls non negotiable.
    """
    total = Money.zero(currency)
    for daily in schedule:
        total = total + daily
    return total
