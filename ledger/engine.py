"""
The replay engine.

Order of processing. Events are consumed in the order the brief lists them, which
is not the same as booking day order. Event ten books on day five but is listed
after event nine, which books on day six. That is the only place in the stream
where the two disagree. The engine sweeps for overdraft fees at the point where it
is about to process an event belonging to a later day, and event ten arrives
afterwards as a late posting into a day already swept. This makes no difference to
any published figure, because event ten belongs to the other account and that
account is never overdrawn. There is a test for it.

Two phase apply. Every handler works out what it wants to write and hands it back
without touching anything. The engine then either writes the whole lot or writes
none of it. In an append only store there is no way to take an entry back, so
appending a settlement and only then discovering the authorisation does not exist
would leave a half finished posting in the permanent record.

Why the fee sweep terminates. A fee is dated to the day it punishes, which means
it sits inside that day's own closing balance. Read literally the rule never
stops: day two closes at minus 370.00, the fee takes it to minus 395.00, which is
still negative, which earns another fee, and so on forever. The once per day limit means a day that already carries a fee cannot earn a
second one, and days are swept in ascending order so a fee dated to day two is
already present by the time day three is checked. Sweeping in descending order
gives the wrong answer, and dropping the once per day limit never finishes. A
single ascending pass is therefore already the fixed point, and there is a test
that re-runs the sweep and asserts nothing new appears.
"""

from typing import Callable, Dict, List, NamedTuple

from ledger.accounts import ACCOUNTS, account
from ledger.constants import CAPITALISATION_DAY, FIRST_DAY, LAST_DAY
from ledger.entries import Entry, EntryType
from ledger.events import (
    Authorization,
    Credit,
    Debit,
    Reversal,
    Settlement,
)
from ledger.holds import HoldConsumed, HoldLog, HoldPlaced, HoldReleased
from ledger.interest import RESIDUAL, accrual_schedule, capitalisation
from ledger.ledger import Ledger
from ledger.money import Money
from ledger.outcomes import Outcome, Status
from ledger.allocation import split_evenly
from ledger.tariff import overdraft_fee


class Application(NamedTuple):
    """
    What a handler proposes. Nothing here has been written down yet.
    """

    entries: List[Entry]
    hold_records: List[object]
    outcome: Outcome


class Engine:
    def __init__(self, interest_strategy: str = RESIDUAL) -> None:
        self.ledger = Ledger()
        self.holds = HoldLog()
        self.outcomes: List[Outcome] = []
        self.interest_schedule: Dict[str, List[Money]] = {}
        self._interest_strategy = interest_strategy
        self._swept_through = FIRST_DAY - 1

    # ---------------------------------------------------------------- balances

    def available(self, account_id: str, day: int) -> Money:
        """
        What could be spent right now, which is the balance less anything held.

        The day is the booking day of the decision being made, used for both
        halves of the query. An authorisation is a question about money today, so
        it is answered with today's balance as known today.
        """
        acc = account(account_id)
        return self.ledger.balance(
            account_id, value_date=day, known_as_of=day
        ) - self.holds.outstanding_total(account_id, acc.currency, known_as_of=day)

    # ------------------------------------------------------------------ replay

    def replay(self, events) -> None:
        seen: set = set()
        for event in events:
            if event.event_id in seen:
                raise ValueError(
                    f"duplicate event id {event.event_id!r}. Replaying the same "
                    f"event twice would post it twice, and an append only store "
                    f"cannot take the second one back."
                )
            seen.add(event.event_id)

            # Everything belonging to an earlier day has now been heard, so those
            # days can be closed off before this event is applied.
            while self._swept_through < event.booking_day - 1:
                self._swept_through += 1
                self.assess_overdrafts(self._swept_through)

            self._apply(event)

        while self._swept_through < LAST_DAY:
            self._swept_through += 1
            self.assess_overdrafts(self._swept_through)

        self.capitalise_interest()

    def _apply(self, event) -> None:
        handlers: Dict[type, Callable] = {
            Credit: self._handle_credit,
            Debit: self._handle_debit,
            Authorization: self._handle_authorization,
            Settlement: self._handle_settlement,
            Reversal: self._handle_reversal,
        }
        application = handlers[type(event)](event)

        # Commit point. Up to here nothing has been written.
        for entry in application.entries:
            self.ledger.append(entry)
        for record in application.hold_records:
            self.holds.append(record)
        self.outcomes.append(application.outcome)

    # ---------------------------------------------------------------- handlers

    def _applied(self, event, entries, hold_records=()) -> Application:
        return Application(
            entries=list(entries),
            hold_records=list(hold_records),
            outcome=Outcome(
                event_id=event.event_id,
                booking_day=event.booking_day,
                status=Status.APPLIED,
            ),
        )

    def _refused(self, event, status: str, reason: str) -> Application:
        return Application(
            entries=[],
            hold_records=[],
            outcome=Outcome(
                event_id=event.event_id,
                booking_day=event.booking_day,
                status=status,
                reason=reason,
            ),
        )

    def _handle_credit(self, event: Credit) -> Application:
        """
        A credit, possibly paid in instalments.

        One event produces as many entries as there are instalments.
        """
        currency = account(event.account_id).currency
        parts = split_evenly(event.amount.minor, event.instalments)
        entries = [
            Entry(
                entry_id=f"{event.event_id}-{index + 1}",
                account_id=event.account_id,
                booking_day=event.booking_day,
                value_date=event.value_date,
                amount=Money(minor=part, currency=currency),
                entry_type=EntryType.CREDIT,
                caused_by_event_id=event.event_id,
            )
            for index, part in enumerate(parts)
        ]
        return self._applied(event, entries)

    def _handle_debit(self, event: Debit) -> Application:
        """
        A debit, which is posted whatever the balance says.

        Only authorisations are checked against available funds. A debit is money
        that has already moved, so refusing it here would not stop anything, it
        would only stop us recording it. Gate debits on available funds and the
        backdated debit on day five is refused, and then nothing else in the
        exercise happens.
        """
        return self._applied(
            event,
            [
                Entry(
                    entry_id=f"{event.event_id}-1",
                    account_id=event.account_id,
                    booking_day=event.booking_day,
                    value_date=event.value_date,
                    amount=-event.amount,
                    entry_type=EntryType.DEBIT,
                    caused_by_event_id=event.event_id,
                )
            ],
        )

    def _handle_authorization(self, event: Authorization) -> Application:
        """
        An authorisation, which is the only thing here that can be refused for
        lack of funds.

        Approved only if what remains after the hold is applied is still at or
        above zero. The hold produces no ledger entry. It reduces what can be
        spent without changing what is owned, which is the distinction acceptance
        criterion five describes.
        """
        available_now = self.available(event.account_id, event.booking_day)
        after_hold = available_now - event.amount
        if after_hold.minor < 0:
            return self._refused(
                event,
                Status.DECLINED,
                f"available {available_now} would fall to {after_hold} once a "
                f"hold of {event.amount} is applied",
            )
        return self._applied(
            event,
            [],
            [
                HoldPlaced(
                    auth_id=event.auth_id,
                    account_id=event.account_id,
                    booking_day=event.booking_day,
                    amount=event.amount,
                )
            ],
        )

    def _handle_settlement(self, event: Settlement) -> Application:
        """
        A settlement, which posts regardless of what the balance looks like.

        The hold reserved nothing, so there is no coverage that could have been
        lost. The commitment was made when the authorisation was approved, and a
        settlement is a statement that money has moved, not a request for
        permission. If the
        account cannot cover it the account goes overdrawn, which is what the
        overdraft fee exists for.

        A settlement pointing at an authorisation nobody granted is refused. This
        asks the hold log. Acceptance criterion four says such an authorisation is
        "not present
        in the ledger", which read strictly would be true of every authorisation
        including the one that settles perfectly well on day four.
        """
        currency = account(event.account_id).currency
        if not self.holds.is_known(event.auth_id):
            return self._refused(
                event,
                Status.REJECTED,
                f"settlement refers to {event.auth_id}, which was never "
                f"authorised. {event.amount} does not leave the account.",
            )

        entry_id = f"{event.event_id}-1"
        entry = Entry(
            entry_id=entry_id,
            account_id=event.account_id,
            booking_day=event.booking_day,
            value_date=event.value_date,
            amount=-event.amount,
            entry_type=EntryType.SETTLEMENT,
            caused_by_event_id=event.event_id,
        )

        outstanding = self.holds.outstanding(event.auth_id, currency)
        consumed = min(outstanding, event.amount)
        records = [
            HoldConsumed(
                auth_id=event.auth_id,
                account_id=event.account_id,
                booking_day=event.booking_day,
                amount=consumed,
                settlement_entry_id=entry_id,
            )
        ]
        remainder = outstanding - consumed
        if remainder.is_positive:
            # Cleared for less than was authorised, so the authorisation is
            # finished and the rest of the hold goes back. The alternative, which
            # is to leave it open for a second clearing, is the hotel and car
            # hire pattern rather than the ordinary retail one.
            records.append(
                HoldReleased(
                    auth_id=event.auth_id,
                    account_id=event.account_id,
                    booking_day=event.booking_day,
                    amount=remainder,
                    reason="cleared for less than the amount authorised",
                )
            )
        return self._applied(event, [entry], records)

    def _handle_reversal(self, event: Reversal) -> Application:
        """
        A reversal, which undoes every entry the original event produced.

        It does not delete anything. The original entry stays where it was and a
        new entry of the opposite sign is written beside it, carrying the
        original's value date so the day it landed on is the day it comes off.
        """
        originals = self.ledger.entries_by_event(event.reverses_event_id)
        if not originals:
            return self._refused(
                event,
                Status.REJECTED,
                f"nothing to reverse: {event.reverses_event_id} produced no "
                f"entries, so it was either refused or never seen",
            )
        for original in originals:
            if self.ledger.reversal_of(original.entry_id) is not None:
                return self._refused(
                    event,
                    Status.REJECTED,
                    f"{event.reverses_event_id} has already been reversed",
                )
        conflicting = [o for o in originals if o.value_date != event.value_date]
        if conflicting:
            return self._refused(
                event,
                Status.REJECTED,
                f"reversal declares value date D{event.value_date} but the "
                f"original landed on D{conflicting[0].value_date}. A reversal "
                f"takes an entry off the day it went on.",
            )

        entries = [
            Entry(
                entry_id=f"{event.event_id}-{index + 1}",
                account_id=original.account_id,
                booking_day=event.booking_day,
                value_date=original.value_date,
                amount=-original.amount,
                entry_type=EntryType.REVERSAL,
                caused_by_event_id=event.event_id,
                reverses_entry_id=original.entry_id,
            )
            for index, original in enumerate(originals)
        ]
        return self._applied(event, entries)

    # ------------------------------------------------------------ end of day

    def assess_overdrafts(self, day: int) -> List[Entry]:
        """
        Close off one day by charging for any day that is now overdrawn.

        Every day up to and including this one is looked at again, because a
        backdated entry can push a day that was fine at the time into the red
        long after it closed. Days are walked in ascending order so that a fee
        charged to an earlier day is already counted when a later day is checked.

        The fee is dated to the day that went negative and booked on the day the
        assessment ran. That is what lets the report say a fee was charged on day
        five with effect from day two, which is how a backdated adjustment is
        described to a customer.
        """
        assessed: List[Entry] = []
        for account_id in ACCOUNTS:
            acc = account(account_id)
            for value_date in range(FIRST_DAY, day + 1):
                balance = self.ledger.balance(
                    account_id, value_date=value_date, known_as_of=day
                )
                if not balance.is_negative:
                    continue
                if self.ledger.has_fee_for(account_id, value_date):
                    continue
                fee = overdraft_fee(acc.currency)
                entry = Entry(
                    entry_id=f"FEE-{account_id}-D{value_date}",
                    account_id=account_id,
                    booking_day=day,
                    value_date=value_date,
                    amount=-fee,
                    entry_type=EntryType.OVERDRAFT_FEE,
                    caused_by_event_id=f"overdraft-sweep-D{day}",
                )
                self.ledger.append(entry)
                assessed.append(entry)
        return assessed

    def capitalise_interest(self) -> None:
        """
        Work out the daily accruals and pay them as one credit.

        This runs last, after every event has been seen. Doing it the moment day
        six closed would have capitalised before
        event ten arrived, since that event books on day five but is listed last.
        The dinar account would then have accrued nothing and closed at 10.000
        instead of 10.008.

        The credit is not part of its own accrual base. The schedule is worked out
        from the balances first and only then is the entry written, so interest
        never earns interest on the day it is paid.
        """
        for account_id in ACCOUNTS:
            acc = account(account_id)
            closings = [
                self.ledger.balance(account_id, value_date=d, known_as_of=LAST_DAY)
                for d in range(FIRST_DAY, LAST_DAY + 1)
            ]
            schedule = accrual_schedule(
                closings, acc.currency, self._interest_strategy
            )
            self.interest_schedule[account_id] = schedule
            total = capitalisation(schedule, acc.currency)
            if total.minor == 0:
                continue
            self.ledger.append(
                Entry(
                    entry_id=f"INT-{account_id}",
                    account_id=account_id,
                    booking_day=LAST_DAY,
                    value_date=CAPITALISATION_DAY,
                    amount=total,
                    entry_type=EntryType.INTEREST,
                    caused_by_event_id="capitalisation",
                )
            )
