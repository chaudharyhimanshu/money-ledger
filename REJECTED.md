# Rejected

The brief says some acceptance criteria are wrong and asks for the incorrect ones to
be identified and refused. Four are refused. Two are accepted with a note.

| # | criterion | verdict |
|---|---|---|
| 1 | day two at end of day five, before fees, is minus 370.00 | accept |
| 2 | E7 causes exactly one fee, on day two | refuse |
| 3 | the day four settlement of Auth-A must be accepted | accept |
| 4 | a settlement naming an unknown authorisation must be refused | accept, the wording is broken |
| 5 | if Auth-B is approved, its hold reduces available but not ledger balance | accept, it never applies |
| 6 | after E9, all balances and fees return to their pre-E7 values | refuse |
| 7 | the three instalments must each be BHD 3.334 | refuse |
| 8 | if the rounded accruals do not sum to the total, the remainder is discarded | refuse |

## Refused: criterion 2

There are three fees, effective on days two, four and five.

The criterion treats a backdated entry as affecting only the day it lands on. A
closing balance is every entry with a value date on or before that day, so a debit
dated to day two sits inside day three's balance, day four's, and day five's. It
lowers every later day by 620.00.

The history as it stood at the end of day five, with the backdated debit in and the
reversal not yet:

| day | closing before fees | negative | after fees carried forward |
|---|---|---|---|
| 1 | 250.00 | no | 250.00 |
| 2 | −370.00 | yes | −395.00 |
| 3 | 30.00 | no | 5.00 |
| 4 | −155.00 | yes | −205.00 |
| 5 | −180.00 | yes | −230.00 |

Three days close negative and each earns one fee. Day three escapes by 5.00, and only
because the fee is 25.00.

This refusal is conditional. It depends on reading "booked with value_date equal to
the day assessed" as the day being punished rather than the day the assessment ran.
Under the other reading there is exactly one fee, on day five, and the account
finishes at 441.00 against 390.92 here. That reading is closer to how a bank behaves
and is set out in `AMBIGUITIES.md`.

## Refused: criterion 6

The balances return. The fees do not, and 75.00 of them stays booked.

Strip the three fees out of the final ledger and the restated balances are the
figures from before the backdated debit arrived. Day four comes back to 465.00, and
every other day matches.

Append only is not the reason the fees survive. Append only forbids editing or
deleting a record. It does not forbid writing an offsetting record, which is the only
way an append only ledger corrects anything, so a refund would have been allowed. The
fees stand because the rules contain no provision for refunding a fee.

Days two, four and five all close positive in the final ledger and all three carry an
overdraft fee. The account is permanently 75.00 lighter on account of a debit that,
in the final state of the ledger, does not exist. A fee caused by an erroneous
posting is normally refunded when the posting is corrected, so a regulator would read
this as a defect.

## Refused: criterion 7

Three times 3.334 is 10.002. The credit was 10.000.

In whole units, 10,000 divided by three is 3,333 with one left over. The leftover can
only go to one of the three parts:

| | part 1 | part 2 | part 3 | total |
|---|---|---|---|---|
| criterion 7 | 3.334 | 3.334 | 3.334 | 10.002 |
| this implementation | 3.334 | 3.333 | 3.333 | 10.000 |

10.000 is fixed and the three parts are what we choose, so the parts have to add up
to it.

## Refused: criterion 8

This contradicts a rule the brief calls non negotiable, that the rounded daily
accruals must sum exactly to the capitalised total. Discarding a remainder is how
they stop summing to it.

The criterion asks the right question and gives the wrong answer. "If the rounded
daily accruals do not sum to the capitalised total" means something only if the total
was worked out independently and could differ from the sum of the parts. Under the
other method the total is defined as the sum of the parts, so they can never
disagree.

There is a remainder. It is carried, not discarded.

| | day 1 | 2 | 3 | 4 | 5 | 6 | total |
|---|---|---|---|---|---|---|---|
| true accrual | 0.100 | 0.090 | 0.250 | 0.166 | 0.156 | 0.156 | 0.918 |
| carry the remainder | 0.10 | 0.09 | 0.25 | 0.17 | 0.15 | 0.16 | 0.92 |
| round each day alone | 0.10 | 0.09 | 0.25 | 0.17 | 0.16 | 0.16 | 0.93 |
| discard, as criterion 8 asks | 0.10 | 0.09 | 0.25 | 0.17 | 0.16 | 0.16 | 0.92, and the parts do not add up |

The third row is criterion 7's error applied to interest. The fourth is criterion 8,
and it breaks the rule it was meant to support.

## Accepted: criterion 4

"Any settlement referencing an authorization ID not present in the ledger must be
rejected and the funds must not leave the account."

The intent is implemented. The Auth-Z settlement on day four is refused and its
180.00 stays put.

Read strictly, the wording contradicts criterion 3. Authorisations are holds. The
brief's own rule defines available balance as ledger balance minus active holds,
which only makes sense if holds are not ledger entries, and they are not: a hold
posts nothing and appears nowhere in the ledger. So no authorisation identifier is
ever in the ledger, including Auth-A, which settles normally on day four. Criterion 4
would require refusing that settlement and criterion 3 requires accepting it.

We read "the ledger" here as "the authorisation registry". The check in
`_handle_settlement` asks the hold log.

A card issuer would post an unmatched settlement instead of refusing it. A clearing
message states that money has moved, and an issuer receiving one for an authorisation
it has no record of posts it and pursues the matter through the dispute system, which
has reason codes for this. `AMBIGUITIES.md` has the numbers. Refusing is implemented
because the brief requires it.

## Accepted: criterion 5

"If Auth-B is approved, its hold reduces available balance but not ledger balance."

Auth-B is declined, so the condition is never met. The criterion is not wrong, and
refusing it would be wrong, because the property it describes is restated almost word
for word from the brief's own rule.

At the moment the decision is taken, the account's available balance is −155.00, and
a hold of 90.00 would take it to −245.00. The brief pairs "if Auth-B is approved"
with "Auth-B is never settled inside the window", which together read as an
invitation to assume it was approved.

Auth-A demonstrates the property anyway. While its hold is live:

| day | ledger balance | available |
|---|---|---|
| 2 | 250.00 | 50.00 |
| 3 | 650.00 | 450.00 |

The hold of 200.00 never touches the ledger and reduces only what can be spent.

# Approaches abandoned during the build

I dropped Decimal because it is exact but not rounded. `Decimal("415.00") *
Decimal("0.0004")` gives `0.166000` and stays that way until somebody calls
`quantize`, which leaves the precision rule depending on a habit. Whole numbers of
minor units make an unrounded amount impossible to write down.

I dropped plain dataclasses because a dataclass does not check its type annotations
at runtime. `Money(25.0, AED)` constructs without complaint and poisons every sum
downstream.

Pydantic in its default mode would have been worse than the dataclass it replaced. In
lax mode an integer field accepts `25.0`, accepts the string `"25"`, and accepts
`True`, converting that last one to `1`. The models would have looked validated while
admitting the values the design forbids. `strict=True` is set on the shared base class
and `tests/test_strictness.py` checks that it is in force.

My first balance query took one date and I threw it away. It could produce the final
answer for any day, and that was all it could do. The report has to say what day two
looked like at the end of day four, and with one date that can only be done by
printing it while the replay is standing in the right place.

Holds started as an object with a status field that gets reassigned. A mutable status
next to an append only ledger means the system as a whole is not append only, and the
hold state is what drives the approval decisions.

I tried holding fee de-duplication on the engine, which works once and breaks on any
replay. The end of day sweep re-examines day two on every day from two through six,
so the check that a day already carries a fee is doing all the correctness work. The
check reads the ledger for a fee already dated to that day.

Sorting the stream by booking day contradicts the brief, which says the events are
replayed in the order given. I kept the listed order and treat the one event that
arrives out of booking day order as a late posting. A test replays the stream both
ways and asserts the final position is identical.

I moved capitalisation from the close of day six to the end of the stream. E10 books
on day five but is listed last, so capitalising at the close of day six would run
before it arrived and the dinar account would finish at 10.000 rather than 10.008.

Independent per-day interest rounding is still in the code but is not the default. It
gives 0.93 against a true accrual of 0.918, and it errs the same way every time. It
stays because the brief's rule holds under both methods, and the tests assert it
under both.

I stopped marking the failing test as `xfail`. Strict `xfail` turns red if somebody
makes the failure pass by mutating history, but it makes the suite exit zero and
report all green, and the brief asked for a failing test. It also inverts the
meaning, since `xfail` says the code is wrong and we mean to fix it, whereas the claim
here is that the code is right and the design has a gap.

My first choice of failing test asserted that the day two fee is refunded after the
reversal, which is criterion 6. That was circular. A test that fails because it
asserts something already refused is a restatement of a rejection. I replaced it with
the authorisation test, which the rejections do not touch.

Reporting outcomes without filtering by account was a bug, found on the first run of
the report. Outcomes record which event they belong to but not which account, so the
Auth-Z rejection and the Auth-B decline were both printed under the dinar account as
well as the dirham one. The report now rebuilds the event to account mapping before
it prints.
