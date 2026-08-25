"""
An account is an identifier, a currency, and an opening balance.

The opening balance is the starting value of the balance fold rather than an entry
dated before the window. Both accounts open at zero, so the choice makes no
numerical difference. I picked this one because a ledger listing should only
contain things that happened, and an opening entry of zero dirhams is not one.
AMBIGUITIES.md records the alternative.
"""

from ledger.base import Record
from ledger.currency import AED, BHD, Currency
from ledger.money import Money


class Account(Record):
    account_id: str
    currency: Currency
    opening_balance: Money

    @property
    def zero(self) -> Money:
        return Money.zero(self.currency)


ACC_001 = Account(
    account_id="ACC-001", currency=AED, opening_balance=Money.parse("0.00", AED)
)
ACC_002 = Account(
    account_id="ACC-002", currency=BHD, opening_balance=Money.parse("0.000", BHD)
)

ACCOUNTS = {a.account_id: a for a in (ACC_001, ACC_002)}


def account(account_id: str) -> Account:
    if account_id not in ACCOUNTS:
        raise KeyError(f"unknown account {account_id!r}")
    return ACCOUNTS[account_id]
