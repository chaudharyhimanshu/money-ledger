"""
Money as a whole number of minor units, tagged with its currency.

An unrounded amount should be impossible to construct. Storing 415.00 dirhams as
41500 fils means there is no way to express a fraction of a fils, so the daily
interest calculation has to decide what to do about the leftover at the moment it
happens.

The alternative would have been Decimal. Decimal is exact but it is not rounded,
so 415.00 times 0.0004 produces 0.166000 and stays that way until somebody
remembers to quantize it. With Decimal you have to remember. With whole minor
units there is nothing to remember.
"""

from __future__ import annotations

from ledger.base import Record
from ledger.currency import Currency


class CurrencyMismatch(Exception):
    """
    Raised when two amounts in different currencies are combined.

    There is no exchange rate anywhere in this system and no sensible default for
    one, so combining two currencies has to raise. The two accounts hold different
    currencies with different numbers of decimal places, so a silent coercion would
    mix units and move the decimal point by a factor of ten.
    """


class Money(Record):
    minor: int
    currency: Currency

    @classmethod
    def parse(cls, amount: str, currency: Currency) -> "Money":
        """
        Build an amount from a human readable string such as "1200.00".

        The string has to carry exactly the number of decimal places the currency
        uses. "1200.0" is rejected for dirhams and so is "1200.000". The brief says
        amounts are stored and rounded to their own precision, and this is that
        rule applied where a human writes an amount down. It also catches the
        mistake of copying an amount from the dirham account into the dinar
        account, where "25.00" would become twenty five dinars rather than the
        intended twenty five hundredths of a dinar.
        """
        negative = amount.startswith("-")
        body = amount[1:] if negative else amount
        if "." not in body:
            raise ValueError(
                f"{amount!r} has no decimal point, but {currency.code} is written "
                f"with {currency.decimal_places} decimal places"
            )
        whole, fraction = body.split(".")
        if len(fraction) != currency.decimal_places:
            raise ValueError(
                f"{amount!r} has {len(fraction)} decimal places but "
                f"{currency.code} uses exactly {currency.decimal_places}"
            )
        if not whole.isdigit() or not fraction.isdigit():
            raise ValueError(f"{amount!r} is not a plain decimal amount")
        minor = int(whole) * currency.minor_units + int(fraction)
        return cls(minor=-minor if negative else minor, currency=currency)

    @classmethod
    def zero(cls, currency: Currency) -> "Money":
        return cls(minor=0, currency=currency)

    def _same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatch(
                f"cannot combine {self.currency.code} and {other.currency.code}"
            )

    def __add__(self, other: "Money") -> "Money":
        self._same_currency(other)
        return Money(minor=self.minor + other.minor, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._same_currency(other)
        return Money(minor=self.minor - other.minor, currency=self.currency)

    def __neg__(self) -> "Money":
        return Money(minor=-self.minor, currency=self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._same_currency(other)
        return self.minor < other.minor

    def __le__(self, other: "Money") -> bool:
        self._same_currency(other)
        return self.minor <= other.minor

    def __gt__(self, other: "Money") -> bool:
        self._same_currency(other)
        return self.minor > other.minor

    def __ge__(self, other: "Money") -> bool:
        self._same_currency(other)
        return self.minor >= other.minor

    @property
    def is_negative(self) -> bool:
        """
        Strictly below zero. Zero is not negative, so an account sitting at
        exactly zero attracts no overdraft fee.
        """
        return self.minor < 0

    @property
    def is_positive(self) -> bool:
        """
        Strictly above zero. Zero is not positive either, so a zero balance earns
        no interest and is charged no fee.
        """
        return self.minor > 0

    def __str__(self) -> str:
        places = self.currency.decimal_places
        units = self.currency.minor_units
        sign = "-" if self.minor < 0 else ""
        magnitude = abs(self.minor)
        return f"{sign}{magnitude // units}.{magnitude % units:0{places}d}"

    def __repr__(self) -> str:
        return f"{self.currency.code} {self}"
