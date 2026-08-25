"""These tests cover splitting an amount into parts that add back up to the original."""

import pytest

from ledger.allocation import split_evenly


def test_ten_dinars_into_three():
    # Acceptance criterion seven asks for 3.334 three times, which comes to
    # 10.002 and hands over two fils that were never credited.
    assert split_evenly(10_000, 3) == [3_334, 3_333, 3_333]
    assert sum(split_evenly(10_000, 3)) == 10_000


@pytest.mark.parametrize("total", [0, 1, 7, 100, 9_999, 10_000, 123_457])
@pytest.mark.parametrize("parts", [1, 2, 3, 7, 12])
def test_a_split_always_adds_back_up(total, parts):
    assert sum(split_evenly(total, parts)) == total


@pytest.mark.parametrize("total", [1, 7, 10_000, 123_457])
@pytest.mark.parametrize("parts", [2, 3, 7])
def test_negative_splits_mirror_positive_ones(total, parts):
    # Reversing a credit paid in instalments has to undo it to the fils. Plain
    # floor division rounds towards negative infinity, so the two splits would not
    # line up.
    assert split_evenly(-total, parts) == [-p for p in split_evenly(total, parts)]


def test_parts_must_be_at_least_one():
    with pytest.raises(ValueError):
        split_evenly(100, 0)
