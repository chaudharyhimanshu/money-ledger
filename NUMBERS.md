# Numbers

Every constant in the code is listed here with the reason for its value. They live in
`ledger/constants.py`, `ledger/currency.py`, `ledger/tariff.py` and
`ledger/accounts.py`.

## Overdraft fee, AED 25.00

The brief sets this, and `ledger/tariff.py` holds it.

A fee is dated to the day that went negative, so it sits inside that day's closing
balance and carries into every later day. Day three closes at 30.00 before any fee is
charged. The day two fee of 25.00 brings it down to 5.00.

| fee | days charged | how many |
|---|---|---|
| 12.50, half | 2, 4, 5 | three |
| 25.00, given | 2, 4, 5 | three |
| 30.00 | 2, 4, 5 | three |
| 30.01 | 2, 3, 4, 5 | four |
| 50.00, double | 2, 3, 4, 5 | four |

Above 30.00, day three goes negative, earns a fee of its own, and every figure after
it moves.

At exactly 30.00 day three lands on zero and is not charged, because the rule tests
for a negative balance and zero is not negative. Change that comparison to `<= 0` and
a fee of 30.00 gives four fees.

Halving the fee to 12.50 charges the same three days and takes the total from 75.00
to 37.50.

## Daily interest rate, 4 over 10,000

The brief gives 0.04% per day. `ledger/constants.py` stores it as two whole numbers.

A float literal would be the only inexact value in the system, and it would sit in
the one calculation the brief asks to reconcile exactly. As a ratio the accrual is
`balance * 4 / 10000`, and the division is the only place rounding can enter.

At half the rate:

| rate | residual carry | independent rounding |
|---|---|---|
| 4/10,000, given | 0.92 | 0.93 |
| 2/10,000, half | 0.46 | 0.47 |

Halving the rate does not remove the rounding question. The two methods still
disagree by one fils, because halving produces a different set of days landing part
way between two fils.

0.04% per day is about 14.6% a year simple, which is a borrowing rate, and no current
account pays it. Quoting a daily rate also avoids the day count question, since an
annual rate is ambiguous until you know whether the year has 360 or 365 days.

## Minor units, 100 for AED and 1,000 for BHD

The brief gives AED two decimal places and BHD three. Each currency in
`ledger/currency.py` stores the number of smallest units in one whole unit, and the
decimal places are derived from that, so the two cannot disagree.

Ten dinars splits into 3.334, 3.333 and 3.333, where ten dirhams would split into
3.34, 3.33 and 3.33. Interest on the dinar account is exact at 0.004 a day, and the
dirham account leaves a remainder on four days out of six.

For the same reason `Money` cannot be built without a currency and refuses to combine
two currencies:

| mistake | result | actually worth |
|---|---|---|
| reuse the integer `2500` in dinars | BHD 2.500 | about AED 24.4 |
| reuse the string `"25.00"` in dinars | BHD 25.000 | about AED 244 |

The second is a ten times overcharge. The first is more dangerous because it is
almost right and would survive review. `Money.parse` rejects `"25.00"` for dinars,
since that string has two decimal places and dinars take three.

## Opening balances, AED 0.00 and BHD 0.000

Both accounts open at zero. `ledger/accounts.py` holds them as the starting value of
the balance fold rather than an entry dated before the window. The choice makes no
arithmetic difference at zero, and a ledger listing should only contain things that
happened.

Writing them as `0.00` and `0.000` sets each account's precision. `Money.parse`
rejects `0.00` for the dinar account.

## Three instalments

The brief asks for three equal instalments, and `stream.py` sets the count.

Ten thousand fils does not divide by three, so the three parts cannot be equal. The
total is held at 10.000 and one part absorbs the extra fils.

| approach | parts | sums to |
|---|---|---|
| round each part on its own | 3.334, 3.334, 3.334 | 10.002 |
| hold the total, hand out the remainder | 3.334, 3.333, 3.333 | 10.000 |

At two instalments the split is 5.000 and 5.000 and the problem disappears. Any count
that does not divide ten thousand behaves the same way.

The leftover fils goes to the first instalment. Giving it to the last would be
equally correct and is the more common convention in repayment schedules. For a
single leftover unit, largest remainder gives the same answer. The choice does not
show up in any balance, only in the entry list.

## Window, six days

The brief gives six days. `ledger/constants.py` numbers them from one, with both ends
inclusive, and the event models reject a day outside the range.

At three days the exercise has no content. The backdated debit arrives on day five
and the reversal on day six.

## Capitalisation day, day six

The brief says interest capitalises at the end of day six.

The credit is not part of its own accrual base, because otherwise the calculation
would refer to itself. The engine computes the schedule from the closing balances
first and writes the entry afterwards, so day six accrues on 390.00.

Capitalising at the end of day three instead would change the answer, because the
credit would sit in the accrual base for days four onwards and earn interest.

## Round half up

The brief does not say which rounding rule to use. `ledger/rounding.py` uses half up.

No accrual in this data is a tie. The six daily accruals land on 0.100, 0.090, 0.250,
0.166, 0.156 and 0.156, and the dinar account on 0.004. Half up and half to even give
the same answers throughout.

Half up is what a reader expects when no rule is stated. Half to even exists to
correct the drift that comes from rounding every day independently, and the residual
carry method already removes that drift at the source.

The tie case is tested with a constructed balance of 12.50, which accrues exactly
0.005 and rounds up to 0.01.

Negative numerators raise instead of rounding. Half up is ambiguous below zero, where
some readers expect minus 0.5 to become minus 1 and others expect zero. Interest only
accrues on positive balances, so the case never arises here.

## Three thresholds

`ledger/money.py` and `ledger/engine.py` hold three comparisons.

| rule | test | effect |
|---|---|---|
| overdraft fee | closing balance `< 0` | a day at exactly zero is not charged |
| interest | closing balance `> 0` | a day at exactly zero earns nothing |
| authorisation | remaining `>= 0` | a hold landing on zero is approved |

The first two leave a balance of exactly zero alone. The dinar account sits at zero
for four days.

The third comes from the brief, which says the balance must remain at or above zero.
Making it strict would mean an account could never be spent down to empty.

Moving the interest and authorisation thresholds between strict and inclusive changes
nothing in this run. Moving the overdraft threshold to `<= 0` adds a fourth fee on
day three.
