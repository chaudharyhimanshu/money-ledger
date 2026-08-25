"""
Charges, held as a schedule keyed by currency.

The brief gives one overdraft fee, twenty five dirhams, and then says fees are
assessed per account. One of the two accounts is held in dinars.

The fee is a schedule keyed by currency, with one entry in it, and the absence of
a dinar entry is what raises. What is missing is a published charge for dinar
accounts, and the fix is to publish one. Retail charges are set per currency at
round advertised numbers, and the amount charged has to match the published
schedule, so a converted figure like 2.559 dinars would not be chargeable even
though the arithmetic works.

The dinar account never goes overdrawn in this replay, so the event stream never
reaches this guard. There is a test that calls it directly.
"""
from typing import Dict

from ledger.currency import AED, Currency
from ledger.money import Money


class MissingTariff(Exception):
    pass


OVERDRAFT_FEE: Dict[Currency, Money] = {
    AED: Money.parse("25.00", AED),
}


def overdraft_fee(currency: Currency) -> Money:
    if currency not in OVERDRAFT_FEE:
        raise MissingTariff(
            f"no overdraft fee is published for {currency.code}. The brief "
            f"supplies an amount for AED only, and a retail charge cannot be "
            f"derived by converting another currency's published figure."
        )
    return OVERDRAFT_FEE[currency]
