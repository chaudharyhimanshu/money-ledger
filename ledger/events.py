"""
The event stream, as models.

Each event carries three separate notions of when.

  arrival_index  where the event sits in the list we were given. The brief says
                 the stream is replayed in this order, and the list is not sorted
                 by booking day, so this is its own axis.
  booking_day    the day the event becomes known to the system. Nothing can be
                 known before it arrives, so this is what governs what the
                 system could have believed at any point.
  value_date     the day whose balance the event lands on. This is allowed to
                 point backwards, which is how the history changes without any
                 record being edited.

Amounts here are always positive. Whether an event adds to or subtracts from a
balance is carried by the type of the event, not by the sign of its amount, so
a credit can never subtract from a balance.
"""

from typing import Annotated, Literal, Union

from pydantic import Field, field_validator

from ledger.base import Record
from ledger.constants import FIRST_DAY, LAST_DAY
from ledger.money import Money


class BaseEvent(Record):
    event_id: str
    arrival_index: int = Field(ge=0)
    booking_day: int = Field(ge=FIRST_DAY, le=LAST_DAY)
    value_date: int = Field(ge=FIRST_DAY, le=LAST_DAY)
    account_id: str


class AmountEvent(BaseEvent):
    amount: Money

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Money) -> Money:
        """
        Direction lives in the event type, so a gross amount is always above
        zero. A debit of minus fifty would add to the balance instead of
        subtracting from it, and nothing later on would catch it.
        """
        if not value.is_positive:
            raise ValueError(f"event amount must be positive, got {value!r}")
        return value


class Credit(AmountEvent):
    kind: Literal["credit"] = "credit"
    instalments: int = Field(default=1, ge=1)


class Debit(AmountEvent):
    kind: Literal["debit"] = "debit"


class Authorization(AmountEvent):
    kind: Literal["authorization"] = "authorization"
    auth_id: str


class Settlement(AmountEvent):
    kind: Literal["settlement"] = "settlement"
    auth_id: str


class Reversal(BaseEvent):
    kind: Literal["reversal"] = "reversal"
    reverses_event_id: str


# An event with an unrecognised kind raises here. A bare union would try each
# member in turn and produce a confusing error, and an isinstance chain in the
# engine would skip it without saying anything.
Event = Annotated[
    Union[Credit, Debit, Authorization, Settlement, Reversal],
    Field(discriminator="kind"),
]
