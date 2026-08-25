import pytest

from ledger.engine import Engine
from stream import EVENTS


@pytest.fixture
def engine():
    """Returns an engine with the whole event stream already replayed."""
    replayed = Engine()
    replayed.replay(EVENTS)
    return replayed
