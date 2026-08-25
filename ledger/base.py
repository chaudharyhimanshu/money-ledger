"""
Every record type in this package inherits this pydantic configuration.

In pydantic's default lax mode an int field accepts 25.0, the string "25", and
True, which it converts to 1. Any of those would put an amount into the ledger
that the fixed point design is meant to rule out. Strict mode rejects all three,
so an unrounded amount cannot be constructed at all.

frozen makes every record immutable, which is what the append only rule needs at
the level of an individual record. extra="forbid" means a typo in a field name is
an error at construction rather than a keyword that is accepted and ignored.
"""

from pydantic import BaseModel, ConfigDict


class Record(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
