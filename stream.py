"""
These are the ten events from the brief, kept in the order the brief lists them.
Event ten books on day five but appears last, after event nine, which books on day
six. It is the only place where the listed order and the booking
day order disagree, and the brief is explicit that the stream is replayed in this
order, so it is treated as a late posting.
"""

from ledger.currency import AED, BHD
from ledger.events import (
    Authorization,
    Credit,
    Debit,
    Reversal,
    Settlement,
)
from ledger.money import Money

ACC1 = "ACC-001"
ACC2 = "ACC-002"


def aed(amount: str) -> Money:
    return Money.parse(amount, AED)


def bhd(amount: str) -> Money:
    return Money.parse(amount, BHD)


EVENTS = [
    Credit(
        event_id="E1", arrival_index=0, booking_day=1, value_date=1,
        account_id=ACC1, amount=aed("1200.00"),
    ),
    Debit(
        event_id="E2", arrival_index=1, booking_day=1, value_date=1,
        account_id=ACC1, amount=aed("950.00"),
    ),
    Authorization(
        event_id="E3", arrival_index=2, booking_day=2, value_date=2,
        account_id=ACC1, amount=aed("200.00"), auth_id="Auth-A",
    ),
    Credit(
        event_id="E4", arrival_index=3, booking_day=3, value_date=3,
        account_id=ACC1, amount=aed("400.00"),
    ),
    Settlement(
        event_id="E5", arrival_index=4, booking_day=4, value_date=4,
        account_id=ACC1, amount=aed("185.00"), auth_id="Auth-A",
    ),
    Settlement(
        event_id="E6", arrival_index=5, booking_day=4, value_date=4,
        account_id=ACC1, amount=aed("180.00"), auth_id="Auth-Z",
    ),
    # E7 arrives on day five carrying a value date of day two. It changes what
    # day two looked like without any existing record being edited.
    Debit(
        event_id="E7", arrival_index=6, booking_day=5, value_date=2,
        account_id=ACC1, amount=aed("620.00"),
    ),
    Authorization(
        event_id="E8", arrival_index=7, booking_day=5, value_date=5,
        account_id=ACC1, amount=aed("90.00"), auth_id="Auth-B",
    ),
    Reversal(
        event_id="E9", arrival_index=8, booking_day=6, value_date=2,
        account_id=ACC1, reverses_event_id="E7",
    ),
    # This one is listed last even though it books on day five.
    Credit(
        event_id="E10", arrival_index=9, booking_day=5, value_date=5,
        account_id=ACC2, amount=bhd("10.000"), instalments=3,
    ),
]
