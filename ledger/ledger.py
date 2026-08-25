"""
The append only entry store.

There is no method here that updates or deletes anything. Correcting a mistake
means writing another entry that offsets it.

The balance query takes two dates:

    value_date    which day's balance you are asking about
    known_as_of   how much of the story you are allowed to have heard

Asking for day two as known at the end of day four gives 250.00. Asking for the
same day two as known at the end of day five gives minus 395.00, because a debit
arrived on day five carrying a value date of day two. Asking again at the end of
day six gives 225.00, because the debit was reversed. The same day has three
answers, one for each day it is asked from.

A single date version of this query could only produce the last of those three
numbers. The earlier ones would exist only if something printed them at the right
moment during the replay.
"""
from typing import Iterable, List, Optional

from ledger.accounts import account
from ledger.entries import Entry, EntryType
from ledger.money import Money


class Ledger:
    def __init__(self) -> None:
        self._entries: List[Entry] = []

    def append(self, entry: Entry) -> None:
        self._entries.append(entry)

    @property
    def entries(self) -> tuple:
        """This returns a copy so a caller cannot edit the store."""
        return tuple(self._entries)

    def entries_for(self, account_id: str) -> Iterable[Entry]:
        return (e for e in self._entries if e.account_id == account_id)

    def balance(
        self, account_id: str, value_date: int, known_as_of: int
    ) -> Money:
        """
        The closing balance of one day, as it appeared at the end of another.

        It adds up every entry for this account whose value date has arrived by
        the day being asked about and which the system had heard about by the day
        it is asked from.
        """
        acc = account(account_id)
        total = acc.opening_balance
        for entry in self._entries:
            if entry.account_id != account_id:
                continue
            if entry.value_date <= value_date and entry.booking_day <= known_as_of:
                total = total + entry.amount
        return total

    def entries_by_event(self, event_id: str) -> List[Entry]:
        """
        Every entry a single event produced.

        This returns a list because the relationship is one to many, and a
        reversal of an event has to undo every entry it produced.
        """
        return [e for e in self._entries if e.caused_by_event_id == event_id]

    def reversal_of(self, entry_id: str) -> Optional[Entry]:
        """
        Whether some later entry already undid this one.

        It reads the log, because an append only store has no flag to set. This
        is what stops the same event being reversed twice.
        """
        for entry in self._entries:
            if entry.reverses_entry_id == entry_id:
                return entry
        return None

    def has_fee_for(self, account_id: str, value_date: int) -> bool:
        """
        Whether this day already carries an overdraft fee.

        This asks the log. The end of day sweep looks at day two again on every
        day from two through six, so without this check the account would pick up
        five fees for the same day. Holding the answer in a set on the engine
        would work for one run and break the moment anything replayed.
        """
        return any(
            e.account_id == account_id
            and e.entry_type == EntryType.OVERDRAFT_FEE
            and e.value_date == value_date
            for e in self._entries
        )
