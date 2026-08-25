"""
The one test the brief asks for that fails against our own design.

This is not one of the acceptance criteria we refused, because that disagreement
would be with the brief and not with anything we built. The failure below is a
hole in our own design.

Run the suite normally and this fails, on purpose. Run

    pytest -m "not known_failure"

for a green suite.
"""

import pytest

from ledger.constants import LAST_DAY
from ledger.holds import HoldPlaced
from ledger.money import Money


@pytest.mark.known_failure
def test_an_approved_authorisation_stays_justifiable(engine):
    """
    Balances are restated when the past changes, and authorisation decisions are
    not.

    Auth-A was approved on day two. At the time the account held 250.00, so a
    hold of 200.00 left 50.00 and the rule was satisfied. Then on day five a
    debit arrived carrying a value date of day two, and day two was restated to
    minus 395.00. Against that history the hold could never have been granted,
    since it would have taken the available balance to minus 595.00.

    The engine has no way to notice. It restates every balance bitemporally and
    then treats an approval as a fact fixed at the moment it was taken, so the
    two halves of the system disagree about whether the past is allowed to
    change. Nothing revisits a decision, and no record is kept of the balance a
    decision was taken against, so there is nothing to go back to.

    Whether a bank should claw back an approved authorisation after a backdated
    correction is a policy question and the brief does not answer it. A design
    that cannot ask the question has made the choice by accident.

    The fix is not large. An approval would record the balance it was judged
    against alongside the decision, and the end of day sweep that already
    revisits every prior day for overdraft purposes would also flag approvals
    that the restated history no longer supports.
    """
    unsupported = []
    for record in engine.holds.records:
        if not isinstance(record, HoldPlaced):
            continue
        decision_day = record.booking_day
        for known_as_of in range(decision_day, LAST_DAY + 1):
            balance = engine.ledger.balance(
                record.account_id, value_date=decision_day, known_as_of=known_as_of
            )
            remaining = balance - record.amount
            if remaining.minor < 0:
                unsupported.append(
                    f"{record.auth_id} was approved on day {decision_day} but "
                    f"as known at the end of day {known_as_of} that day closed "
                    f"at {balance}, so the hold of {record.amount} would have "
                    f"left {remaining}"
                )

    assert not unsupported, (
        "an approval is still standing that the restated history cannot "
        "support:\n  " + "\n  ".join(unsupported)
    )
