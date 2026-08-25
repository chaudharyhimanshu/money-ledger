"""
Currencies, described by how many of their smallest unit make up one whole unit.

Every amount in this system is stored as a whole number of those smallest units.
AED is divided into 100 fils and BHD into 1000 fils, which is why the two accounts
in this exercise round to two and three decimal places respectively. BHD is one of
the small group of currencies that use three decimal places rather than two, and
which is why the ten dinar credit splits into 3.334 and 3.333 and 3.333.
"""

from ledger.base import Record


class Currency(Record):
    code: str
    minor_units: int

    @property
    def decimal_places(self) -> int:
        """
        How many digits appear after the decimal point when this currency is
        printed. One hundred minor units gives two places, one thousand gives
        three. It is derived from minor_units so the two cannot disagree.
        """
        return len(str(self.minor_units)) - 1

    def __str__(self) -> str:
        return self.code


AED = Currency(code="AED", minor_units=100)
BHD = Currency(code="BHD", minor_units=1000)
