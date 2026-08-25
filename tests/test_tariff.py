"""
The overdraft charge is published per currency, and only dirhams has one.

The dinar account never goes overdrawn in this replay, so the event stream never
reaches this guard and it is tested directly here.
"""

import pytest

from ledger.currency import AED, BHD
from ledger.money import Money
from ledger.tariff import MissingTariff, overdraft_fee


def test_dirhams_has_a_published_fee():
    assert overdraft_fee(AED) == Money.parse("25.00", AED)


def test_dinars_has_none_and_says_so():
    # The error says there is no published dinar charge. The fix is to publish a
    # dinar amount, because a retail charge has to match the published schedule to
    # the fils. Running the dirham figure through an exchange rate would not do
    # that.
    with pytest.raises(MissingTariff):
        overdraft_fee(BHD)
