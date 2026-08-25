"""Money behaves like whole numbers of the smallest unit, and refuses to mix."""

import pytest

from ledger.currency import AED, BHD
from ledger.money import CurrencyMismatch, Money


def test_parse_uses_minor_units():
    assert Money.parse("1200.00", AED).minor == 120_000
    assert Money.parse("10.000", BHD).minor == 10_000


def test_parse_requires_the_currencys_own_precision():
    # The same digits mean different amounts in the two currencies. A string
    # copied from one account to the other has to be rejected, because otherwise
    # it gets read as a different amount.
    with pytest.raises(ValueError):
        Money.parse("1200.0", AED)
    with pytest.raises(ValueError):
        Money.parse("25.00", BHD)


def test_arithmetic_stays_exact():
    total = Money.parse("1200.00", AED) - Money.parse("950.00", AED)
    assert total == Money.parse("250.00", AED)
    assert str(-total) == "-250.00"


def test_currencies_never_mix():
    with pytest.raises(CurrencyMismatch):
        Money.parse("1.00", AED) + Money.parse("1.000", BHD)
    with pytest.raises(CurrencyMismatch):
        Money.parse("1.00", AED) < Money.parse("1.000", BHD)


def test_zero_is_neither_positive_nor_negative():
    # A zero balance earns no interest and pays no overdraft fee, and both of
    # those come from this.
    zero = Money.zero(BHD)
    assert not zero.is_positive
    assert not zero.is_negative


def test_formatting_pads_to_the_currency_precision():
    assert str(Money(minor=-39_500, currency=AED)) == "-395.00"
    assert str(Money(minor=4, currency=BHD)) == "0.004"
