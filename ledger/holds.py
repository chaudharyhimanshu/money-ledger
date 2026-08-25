"""
Authorisation holds, kept as an append only log of their own.

A hold could have been a small object with a status field reassigned from active
to settled, but holds are what decide whether an authorisation is approved, so a
mutable status sitting next to an append only ledger would mean the system as a
whole is not append only.

Three kinds of record are written and never changed, and the outstanding amount on
any authorisation is worked out by adding them up.

A hold reserves nothing. It posts no entry and moves no money, and it gives its
authorisation no claim on the funds ahead of anything else. It only reduces the
number the approval decision looks at. Other debits can and do spend the same
money first, which is how an account ends up overdrawn by a transaction that was
approved when the money was there.
"""

from typing import List, Literal

from ledger.base import Record
from ledger.constants import LAST_DAY
from ledger.currency import Currency
from ledger.money import Money


class HoldPlaced(Record):
    kind: Literal["placed"] = "placed"
    auth_id: str
    account_id: str
    booking_day: int
    amount: Money


class HoldConsumed(Record):
    kind: Literal["consumed"] = "consumed"
    auth_id: str
    account_id: str
    booking_day: int
    amount: Money
    settlement_entry_id: str


class HoldReleased(Record):
    kind: Literal["released"] = "released"
    auth_id: str
    account_id: str
    booking_day: int
    amount: Money
    reason: str


class HoldLog:
    def __init__(self) -> None:
        self._records: List[Record] = []

    def append(self, record: Record) -> None:
        self._records.append(record)

    @property
    def records(self) -> tuple:
        return tuple(self._records)

    def is_known(self, auth_id: str, known_as_of: int = LAST_DAY) -> bool:
        """
        Whether we ever granted this authorisation.

        This is the check that refuses the Auth-Z settlement. It asks the hold
        log, not the ledger. Holds never produce ledger entries, so an
        authorisation identifier is never present in the ledger, not even for one
        that was approved and settled normally.
        """
        return any(
            isinstance(r, HoldPlaced)
            and r.auth_id == auth_id
            and r.booking_day <= known_as_of
            for r in self._records
        )

    def auth_ids_known_by(self, known_as_of: int) -> List[str]:
        """Every authorisation granted on or before the given day, in order."""
        return [
            r.auth_id
            for r in self._records
            if isinstance(r, HoldPlaced) and r.booking_day <= known_as_of
        ]

    def outstanding(
        self, auth_id: str, currency: Currency, known_as_of: int = LAST_DAY
    ) -> Money:
        """
        How much of this authorisation is still encumbering the account.

        Placed, less anything consumed by a settlement, less anything released.
        """
        total = Money.zero(currency)
        for record in self._records:
            if record.auth_id != auth_id or record.booking_day > known_as_of:
                continue
            if isinstance(record, HoldPlaced):
                total = total + record.amount
            else:
                total = total - record.amount
        return total

    def outstanding_total(
        self, account_id: str, currency: Currency, known_as_of: int
    ) -> Money:
        """
        Everything still held against one account, as known on a given day.
        """
        total = Money.zero(currency)
        for record in self._records:
            if record.account_id != account_id or record.booking_day > known_as_of:
                continue
            if isinstance(record, HoldPlaced):
                total = total + record.amount
            else:
                total = total - record.amount
        return total

    def state(
        self, auth_id: str, currency: Currency, known_as_of: int = LAST_DAY
    ) -> str:
        """
        A readable state for the per-day report, as it stood on a given day.

        It is computed from the records each time, so it cannot disagree with
        them.
        """
        if not self.is_known(auth_id, known_as_of):
            return "unknown"
        consumed = any(
            isinstance(r, HoldConsumed)
            and r.auth_id == auth_id
            and r.booking_day <= known_as_of
            for r in self._records
        )
        remaining = self.outstanding(auth_id, currency, known_as_of)
        if remaining.is_positive:
            return "active"
        return "settled" if consumed else "released"
