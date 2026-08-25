"""
Every tunable number in the system, gathered in one place.

NUMBERS.md explains how each of these values was chosen and can be checked
against this file.
"""

# The replay window is six days, numbered from one.
FIRST_DAY = 1
LAST_DAY = 6

# Daily interest of 0.04 percent, held as a whole number ratio rather than as
# the decimal 0.0004. A float literal would be the only inexact value in the
# system, and it would sit in the one calculation the brief asks to reconcile
# exactly.
DAILY_INTEREST_NUMERATOR = 4
DAILY_INTEREST_DENOMINATOR = 10_000

# Interest is credited as one entry at the end of the last day.
CAPITALISATION_DAY = LAST_DAY
