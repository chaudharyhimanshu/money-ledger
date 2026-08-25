"""
The per-day report.

The brief asks for the closing ledger balance, fee assessments, authorisation
states and errors, for each day. With a backdated entry in the stream there is
more than one closing balance for the same day.

What is printed for a given day is the balance as it stood at the end of that
day, using only what was known by then. That is the figure a customer looking at
their account on that evening would have seen. When a later day changes an
earlier one, the change is shown on the day it became known, under a restatement
heading, rather than rewriting the earlier day's line. The final restated
position for every day is printed once at the end.

The day two line says 250.00 on day two because that is what was true then, and
the day five section says day two has been restated to minus 395.00 because that
is when it changed.
"""

from typing import Dict, List

from ledger.accounts import ACCOUNTS, account
from ledger.constants import FIRST_DAY, LAST_DAY
from ledger.entries import EntryType
from ledger.interest import capitalisation
from ledger.outcomes import Status

WIDTH = 74


def _rule(char: str = "=") -> str:
    return char * WIDTH


def render(engine, events) -> str:
    """
    Build the whole report as one string, so it can be printed or compared
    against a stored copy in a test.
    """
    # Outcomes record which event they belong to, not which account, so the
    # mapping is rebuilt here. Without it a rejection on one account would be
    # reported under both, which is what happened the first time this ran.
    auth_by_event = {e.event_id: getattr(e, "auth_id", None) for e in events}
    account_by_event = {e.event_id: e.account_id for e in events}
    lines: List[str] = []
    lines.append(_rule())
    lines.append("LEDGER REPLAY, DAY 1 TO DAY 6")
    lines.append(_rule())
    lines.append("")
    lines.append(
        "Balances shown per day are as known at the end of that day. When a "
        "later event"
    )
    lines.append(
        "changes an earlier day, it is reported as a restatement on the day it "
        "became"
    )
    lines.append("known. The final restated position appears at the end.")
    lines.append("")

    for day in range(FIRST_DAY, LAST_DAY + 1):
        lines.append(_rule())
        lines.append(f"DAY {day}")
        lines.append(_rule())
        for account_id in ACCOUNTS:
            lines.extend(
                _account_day(
                    engine, account_id, day, auth_by_event, account_by_event
                )
            )
        lines.append("")

    lines.extend(_summary(engine))
    return "\n".join(lines)


def _field(label: str, value: str) -> str:
    """This lines up one label and value pair in a fixed column."""
    return f"    {label}{value:>{WIDTH - 8 - len(label)}}"


def _account_day(
    engine, account_id: str, day: int, auth_by_event, account_by_event
) -> List[str]:
    acc = account(account_id)
    out: List[str] = []
    out.append("")
    out.append(f"  {account_id}  {acc.currency.code}")

    closing = engine.ledger.balance(account_id, value_date=day, known_as_of=day)
    out.append(_field("closing balance", str(closing)))

    # Any earlier day whose closing changed because of what arrived today.
    restatements = []
    for earlier in range(FIRST_DAY, day):
        before = engine.ledger.balance(account_id, earlier, day - 1)
        after = engine.ledger.balance(account_id, earlier, day)
        if before != after:
            restatements.append((earlier, before, after))
    if restatements:
        out.append("    restated by events that arrived today")
        for earlier, before, after in restatements:
            out.append(
                f"      Day {earlier}   {before}  becomes  {after}"
            )

    fees = [
        e
        for e in engine.ledger.entries_for(account_id)
        if e.entry_type == EntryType.OVERDRAFT_FEE and e.booking_day == day
    ]
    if fees:
        out.append("    fees assessed today")
        for fee in fees:
            out.append(
                f"      overdraft fee {fee.amount}   effective Day {fee.value_date}"
            )
    else:
        out.append(_field("fees assessed today", "none"))

    auth_lines = []
    for auth_id in dict.fromkeys(engine.holds.auth_ids_known_by(day)):
        placed = next(
            r for r in engine.holds.records
            if getattr(r, "auth_id", None) == auth_id and r.kind == "placed"
        )
        if placed.account_id != account_id:
            continue
        state = engine.holds.state(auth_id, acc.currency, day)
        held = engine.holds.outstanding(auth_id, acc.currency, day)
        auth_lines.append(f"      {auth_id}   {state}, held {held}")
    for outcome in engine.outcomes:
        if outcome.booking_day != day or outcome.status != Status.DECLINED:
            continue
        if account_by_event.get(outcome.event_id) != account_id:
            continue
        auth_id = auth_by_event.get(outcome.event_id)
        if auth_id is None:
            continue
        auth_lines.append(f"      {auth_id}   declined, {outcome.reason}")
    if auth_lines:
        out.append("    authorisations")
        out.extend(auth_lines)
    else:
        out.append(_field("authorisations", "none"))

    errors = [
        o
        for o in engine.outcomes
        if o.booking_day == day
        and o.is_error
        and account_by_event.get(o.event_id) == account_id
    ]
    if errors:
        out.append("    errors")
        for error in errors:
            out.append(f"      {error.event_id}   {error.reason}")
    else:
        out.append(_field("errors", "none"))

    if day == LAST_DAY:
        schedule = engine.interest_schedule.get(account_id, [])
        total = capitalisation(schedule, acc.currency)
        out.append("    interest capitalised today")
        daily = "  ".join(str(x) for x in schedule)
        out.append(f"      daily accruals   {daily}")
        out.append(f"      credited as a single entry of {total}")
    return out


def _summary(engine) -> List[str]:
    out = [_rule(), "FINAL RESTATED POSITION", _rule(), ""]
    out.append(
        "    Every day's closing balance as it stands once all ten events are in."
    )
    out.append("")
    for account_id in ACCOUNTS:
        acc = account(account_id)
        out.append(f"  {account_id}  {acc.currency.code}")
        for day in range(FIRST_DAY, LAST_DAY + 1):
            closing = engine.ledger.balance(account_id, day, LAST_DAY)
            out.append(f"      Day {day}{str(closing):>16}")
        out.append("")
    return out
