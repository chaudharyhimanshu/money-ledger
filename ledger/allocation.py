"""
Splitting one amount into several that add back up to it exactly.

Ten dinars in three equal instalments is arithmetically impossible, since ten
thousand fils does not divide by three. The brief asks for it anyway.

Rounding each instalment on its own gives 3.334 three times, which comes to
10.002. That hands the customer two extra fils out of nowhere. It is what
acceptance criterion seven proposes and why that criterion is refused. We know the
total, so the parts are adjusted to fit it and the remainder is handed out one
unit at a time.
"""

from typing import List


def split_evenly(total: int, parts: int) -> List[int]:
    """
    Divide a whole number of minor units into parts that sum back to it exactly.

    Ten thousand fils into three gives 3334, 3333, 3333. The leftover single fils
    goes to the first instalment. Giving it to the last instead would be equally
    correct and the choice is recorded in NUMBERS.md. The parts have to add back
    up to the total.

    Negative totals mirror positive ones exactly, so splitting a reversal of an
    instalment credit undoes it to the fils. Letting Python's floor division
    handle negatives directly would not do that, because divmod rounds towards
    negative infinity and the two splits would disagree.
    """
    if parts < 1:
        raise ValueError(f"cannot split into {parts} parts")
    sign = -1 if total < 0 else 1
    base, remainder = divmod(abs(total), parts)
    return [sign * (base + (1 if i < remainder else 0)) for i in range(parts)]
