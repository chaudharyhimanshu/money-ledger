"""
These tests check that pydantic strict mode is switched on.

Storing amounts as whole numbers of the smallest unit means a fractional amount
cannot exist. That only holds if the models refuse the values that would let one
in.

Pydantic's default is the opposite. In lax mode an integer field accepts 25.0 and
the string "25" and True, converting the last of those to 1. Under that
configuration the models would look validated while admitting what the design
forbids. Turn strict off in the base config and the six coercion checks below
fail. The other three cover frozen and extra="forbid".
"""
import pytest
from pydantic import ValidationError

from ledger.currency import AED
from ledger.events import Credit
from ledger.money import Money


@pytest.mark.parametrize("smuggled", [25.0, "25", True])
def test_money_refuses_anything_that_is_not_a_whole_number(smuggled):
    with pytest.raises(ValidationError):
        Money(minor=smuggled, currency=AED)


@pytest.mark.parametrize("smuggled", [1.0, "1", True])
def test_event_days_refuse_anything_that_is_not_a_whole_number(smuggled):
    with pytest.raises(ValidationError):
        Credit(
            event_id="X", arrival_index=0, booking_day=smuggled, value_date=1,
            account_id="ACC-001", amount=Money.parse("1.00", AED),
        )


def test_records_are_frozen():
    amount = Money.parse("1.00", AED)
    with pytest.raises(ValidationError):
        amount.minor = 999


def test_unknown_field_is_an_error_rather_than_ignored():
    with pytest.raises(ValidationError):
        Money(minor=1, currency=AED, typo=True)


def test_gross_amounts_must_be_positive():
    # Direction belongs to the event type. A debit of minus fifty would be a
    # credit in disguise and would pass every check downstream.
    with pytest.raises(ValidationError):
        Credit(
            event_id="X", arrival_index=0, booking_day=1, value_date=1,
            account_id="ACC-001", amount=Money.parse("-5.00", AED),
        )
