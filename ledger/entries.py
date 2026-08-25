"""
Ledger entries, which are the only things that move a balance.

An event is something that happened to us. An entry is what we wrote down as a
result. The relationship is one to many. Event ten is the case: a credit of ten
dinars payable in three instalments produces three separate entries. Anything that reverses an event therefore has to reverse all
of its entries, which is why a reversal resolves an event id to a list.

Every entry records both the day it was written down and the day it counts
towards. Without the first of those the log cannot answer what the system
believed on any past day.
"""

from typing import Optional

from pydantic import Field

from ledger.base import Record
from ledger.constants import FIRST_DAY, LAST_DAY
from ledger.money import Money


class EntryType:
    CREDIT = "credit"
    DEBIT = "debit"
    SETTLEMENT = "settlement"
    OVERDRAFT_FEE = "overdraft_fee"
    REVERSAL = "reversal"
    INTEREST = "interest"


class Entry(Record):
    entry_id: str
    account_id: str
    booking_day: int = Field(ge=FIRST_DAY, le=LAST_DAY)
    value_date: int = Field(ge=FIRST_DAY, le=LAST_DAY)
    amount: Money
    entry_type: str
    caused_by_event_id: str

    # Set only on an entry that undoes another entry. Reversal has to be
    # discoverable by reading the log, because an append only store has no flag
    # on the original that we could set to say it has already been undone.
    reverses_entry_id: Optional[str] = None

    def __str__(self) -> str:
        return (
            f"{self.entry_id} {self.entry_type} {self.amount!r} "
            f"value_date=D{self.value_date} booked=D{self.booking_day}"
        )
