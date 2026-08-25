"""
What happened to each event, stored as records.

The brief asks for errors to be reported per day. A rejection is a fact about a
particular day just as much as a posting is, so it belongs in the log. If
replaying the log cannot reproduce the day four report including the line that
says the Auth-Z settlement was refused, then the log is missing part of what
happened.

Rejected and declined are separate statuses. Refusing a settlement that
points at an authorisation nobody ever granted is the system finding something
wrong. Refusing an authorisation because the money is not there is the system
working as intended. Reporting a decline as an error would be misleading.
"""

from pydantic import Field

from ledger.base import Record
from ledger.constants import FIRST_DAY, LAST_DAY


class Status:
    APPLIED = "applied"
    REJECTED = "rejected"
    DECLINED = "declined"


class Outcome(Record):
    event_id: str
    booking_day: int = Field(ge=FIRST_DAY, le=LAST_DAY)
    status: str
    reason: str = ""

    @property
    def is_error(self) -> bool:
        """
        Only a rejection counts as an error. A decline is a normal outcome and
        appears with the other authorisation states.
        """
        return self.status == Status.REJECTED
