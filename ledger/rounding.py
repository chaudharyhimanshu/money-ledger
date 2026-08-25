"""
Rounding for integer division.

Only one rounding rule is needed in this system and it is only needed in two
places, both of which are real divisions. One is the daily interest calculation
and the other is splitting a credit into instalments. Everywhere else the
arithmetic is exact integer addition and subtraction, so no rounding can occur.
"""


def round_half_up(numerator: int, denominator: int) -> int:
    """
    Divide and round to the nearest whole number, with exact halves going up.

    Implemented as (2n + d) // 2d so that no floating point value is ever
    created. Comparing 2n against d is the same test as comparing the remainder
    against half of d, but it stays in whole numbers throughout.

    Negative numerators are rejected because "round half up" is ambiguous below
    zero. Some readers expect minus 0.5 to become minus 1 because that is away
    from zero, and others expect it to become 0 because that is upward on the
    number line. Interest only accrues on positive balances, so the case never
    arises here. Raising means anyone who later adds interest on overdrawn
    balances has to pick a rule.
    """
    if denominator <= 0:
        raise ValueError(f"denominator must be positive, got {denominator}")
    if numerator < 0:
        raise ValueError(
            "round_half_up does not accept a negative numerator, because the "
            "meaning of rounding a half downward is ambiguous."
        )
    return (2 * numerator + denominator) // (2 * denominator)
