# Ambiguities

This lists every question the brief leaves open, how I settled it, and what the other
answer would have cost. Where an alternative changes a number, the number is computed.

## The counterfactuals

Final position of ACC-001 under each reading, with everything else held constant.

| reading | final | delta |
|---|---|---|
| as implemented | 390.92 | |
| interest by independent per-day rounding | 390.93 | +0.01 |
| fees value dated to the assessment day | 390.96 | +0.04 |
| interest accrued on as-known balances | 390.80 | −0.12 |
| no retroactive assessment, one fee on day five | 441.00 | +50.08 |
| the unmatched settlement force posted | 210.70 | −180.22 |

# Questions that change the numbers

## 1. What does "the day assessed" mean?

The fee is "booked with value_date equal to the day assessed". That can mean the day
being assessed, which is the day that closed negative, or the day the assessment ran.
For the backdated debit those are three days apart.

The fee is dated to the day being punished. The day two fee carries a value date of
day two and a booking day of day five.

Criterion 1 asks for day two's balance "at end of day five and before any fee is
assessed", which is empty unless a fee is about to land on day two. The brief also
says "booked with value_date", and a value date only carries information if it can
differ from the booking day. It is the only reading under which "once per day per
account" stays meaningful, since under the other reading all three fees would carry a
value date of day five, which either breaks the once-per-day rule or collapses three
fees into one.

Cost of the alternative: value dating all three to day five gives closings of 250.00,
250.00, 650.00, 465.00, 390.00, 390.00 and interest of 0.96, so 390.96. The balance
before interest is unchanged at 390.00, so the choice shows up in the intermediate
restated balances and in the interest.

A bank does neither of these. Item 4 has the detail.

## 2. Restated or as-known balances for interest?

Day two's closing balance is 250.00 as known on day two, minus 395.00 as known on day
five, and 225.00 as known on day six.

Interest uses the restated balances, and the whole schedule is computed in one pass
once every event has been seen.

The fee rule already defines a closing balance as every entry with a value date on or
before that day. Using a different definition of the same phrase for interest, inside
the same six day window, would be wrong. And because the credit is paid once at the
end, the six daily figures are a breakdown of a single payment, so no as-known figure
ever had to be committed.

Cost of the alternative: accruing on as-known balances gives 0.10, 0.10, 0.26, 0.19,
0.00, 0.16 and a total of 0.80, so 390.80. Day five contributes nothing because as
known at the time it closed at minus 230.00.

That 0.80 is the as-known method with the adjustment step missing. A core banking
system posts accruals daily at as-known amounts into an internal accrual account, and
when a back-valued entry lands it recalculates and posts an adjustment for the
difference. The total it converges on is the restated total. This implementation
computes the answer in one pass, so it keeps no record of what was believed on each
day.

## 3. How is the capitalised total derived?

"The rounded daily accruals must sum exactly to the capitalised total." Two methods
satisfy that and they disagree.

The total is the correctly rounded true accrual, and the daily figures carry the
remainder so they add up to it. True accrual 0.918, capitalised 0.92, dailies 0.10 /
0.09 / 0.25 / 0.17 / 0.15 / 0.16.

The ten dinar credit has its total fixed at 10.000 and its parts adjusted to 3.334 /
3.333 / 3.333, and criterion 7 refuses to let independently rounded parts override a
total that is already known. Interest is the same shape. Criterion 8's talk of "the
remainder" means something only in this frame, since under the other method the total
is defined as the sum of the parts.

Rounding each day alone also sends 0.166 up to 0.17 every time, which on a balance of
415.00 held for a year overpays by 1.46. Accrual engines either hold accruals at
higher precision and round once, or carry the residual. Both land on 0.92.

Cost of the alternative: 0.93, so 390.93. Both methods are implemented and
`tests/test_interest.py` asserts the sum-exactly rule under each.

## 4. Should a fee be charged retroactively at all?

Item 1 asks what value date a retroactive fee carries. This asks whether one should
exist.

It should, because the brief's own criterion 1 presupposes it.

A bank would not do this. Core systems support back-value posting as a controlled
operation with a configured limit, and the correction posts forward. The adjustment
carries today's booking date and lands in the currently open period. Once a day is
closed you cannot post into it.

For overdraft fees, retroactive assessment is hard to justify. A fee has to be tied to
a balance the customer had a chance to cure, and charging a day two fee on day five
gives no cure window. The mechanism for recapturing the economics of a back-valued
debit is a back-value interest adjustment, not a retroactively manufactured charge.

Cost of the alternative: one fee, on day five. Closings 250.00 / 250.00 / 650.00 /
465.00 / 440.00 / 440.00, interest 1.00, final 441.00. That would make criterion 2
nearly correct. Its refusal in `REJECTED.md` is marked conditional for this reason.

## 5. Is the fee inside or outside its own day's closing balance?

It is dated to that day, so it is inside it. The rule as written then does not
terminate. Day two closes at minus 370.00, the fee takes it to minus 395.00, which is
still negative, which earns another fee, forever.

The fee stays inside, and the once-per-day limit is what stops the loop.

A fee dated to day N only affects days from N onward, and days are visited in
ascending order, so a fee charged to an earlier day is already counted when a later
day is checked. The once-per-day limit stops day N re-triggering on itself. A
descending sweep gives the wrong answer, and without the limit the sweep never
terminates. `tests/test_overdraft.py` re-runs the sweep and asserts nothing new
appears.

Cost of the alternative: placing the fee outside its own day's balance changes day
two's accrual base from 225.00 to 250.00 and costs the customer 0.03 of interest.

## 6. Is "once per day" per value date or per processing run?

On day five this engine charges three fees in a single sweep.

The limit is per value date. Each day can carry at most one fee, and three distinct
days qualified.

Cost of the alternative: a cap per processing run gives one fee on day five and a
final of 441.00. Retail tariffs commonly cap overdraft fees at three to five per
processing day and a handful per statement cycle, and some banks have moved to one per
day or abolished them. 75.00 of fees against a peak overdraft of 370.00 is a charge of
twenty percent.

## 7. Refuse an unmatched settlement, or force post it?

Refuse, because criterion 4 requires it. The 180.00 stays in the account.

Card systems do the opposite. A clearing record is a financial message, and the issuer
cannot decline it. Unmatched clearings arrive routinely from stand-in authorisations,
expired authorisations, chip transactions approved offline at unattended terminals,
and transactions below a floor limit. The issuer posts them and pursues remediation
through the dispute system, which has reason codes for this and windows measured in
months.

The report says the funds do not leave the account. That is true of the customer's
account and false of the bank's books, since the acquirer is still paid through the
settlement cycle. In a bank the 180.00 would sit in a suspense account with an
investigation queue against it.

Cost of the alternative: force posting gives closings of 250.00 / 225.00 / 625.00 /
235.00 / 210.00 / 210.00 and a final of 210.70. The fee count is unchanged at three,
because day four was already negative.

## 8. Which snapshot does the per-day report print?

With a backdated entry there is more than one closing balance per day.

It prints both, each labelled. Each day shows its closing balance as known at the end
of that day. When a later event changes an earlier day, the change is reported under a
restatement heading on the day it became known. The final restated position is printed
once at the end.

## 9. Arrival order or booking day order?

The brief says the stream is replayed in the order listed, and the listed order is not
sorted by booking day. E10 happens on day five and is listed after E9, which happens
on day six. It is the only such place.

The engine keeps the listed order and treats E10 as a late posting into a day already
swept.

Cost of the alternative: nothing changes. `tests/test_ordering.py` replays both ways
and asserts an identical final position. That holds only because E10 belongs to the
account that never goes overdrawn.

An engine capitalising interest the moment day six closed would capitalise before E10
arrived, and the dinar account would accrue nothing and finish at 10.000 rather than
10.008.

## 10. Where does the instalment remainder go?

Ten thousand fils into three parts leaves one over.

It goes to the first instalment, giving 3.334 / 3.333 / 3.333.

Giving it to the last would be equally correct and is the more common convention in
repayment schedules. For a single leftover unit, largest remainder gives the same
answer.

Cost of the alternative: nothing in any balance. The choice shows up only in the entry
list. The three instalments are three separate entries, one per instalment.

# Questions that shape the design

## 11. Are debits checked against available funds?

No. Only authorisations are.

The authorisation rule is given explicitly and nothing says whether it applies to
anything else. Apply it to debits and the backdated debit on day five is refused for
insufficient funds, after which there is no overdraft, no fee, and nothing to reverse.

It is also correct. A debit records money that has already moved, so refusing it would
not stop anything, only stop us writing it down.

## 12. Does a settlement consult available balance?

No, never.

A hold reserves nothing. It posts no entry and creates no claim on the money ahead of
anything else. It only reduces the number the approval check looks at. Other debits
can consume the same money first, which is how accounts fall into unarranged
overdraft. The authorisation was approved when the money was there, unrelated debits
landed first, and the clearing forces the balance negative with nothing left to
decline against.

The commitment was made at authorisation time and a clearing has no decline path.
`tests/test_authorization.py` constructs an account with nothing behind it and asserts
the settlement posts anyway.

## 13. Under-settlement: release the remainder or keep the authorisation open?

Auth-A held 200.00 and cleared for 185.00.

The authorisation closes and the remaining 15.00 is released.

185.00 against a 200.00 authorisation is a final clearing for less than the amount
authorised, which is the ordinary retail case: an item out of stock, a discount at the
till. Partial settlement means one of several clearings against a single authorisation
that stays open, which is the hotel and car hire pattern. Somebody reading "partial
settlement" would expect the hold to remain, so the code and documents say
under-settlement.

Cost of the alternative: if the 15.00 stayed held, available on day five would be
−170.00. Auth-B is declined under all three readings:

| Auth-A hold treatment | available | after a 90.00 hold |
|---|---|---|
| released at settlement, as implemented | −155.00 | −245.00 |
| 15.00 left open | −170.00 | −260.00 |
| full 200.00 held until expiry | −355.00 | −445.00 |

## 14. Are authorisation decisions revisited when the past is restated?

No. This is the design's known weakness and the subject of the failing test.

Auth-A was approved on day two against a balance of 250.00. Once the backdated debit
restates day two to −395.00, that approval could not have been granted. The engine
keeps no record of the balance a decision was judged against and nothing revisits a
decision.

Whether a bank should claw back an approval after a backdated correction is a policy
question the brief does not answer. This design cannot ask the question at all, so it
never records an answer.

## 15. Is a declined authorisation an error?

No. Rejections and declines are separate statuses. A settlement naming an
authorisation that was never granted is the system finding something wrong and is
reported under errors. An authorisation refused for lack of funds is the system
working as designed and appears with the other authorisation states.

## 16. Are refusals part of the record, or just printed?

They are part of the record, appended to an outcome log.

Replaying the log has to reproduce the day four report, including the line explaining
why 180.00 never left the account.

## 17. A dirham fee on a dinar account

The fee is given as AED 25.00 and the rule says fees are assessed per account. One
account is in dinars.

The fee is a schedule keyed by currency, and the absence of a dinar entry is what
raises. What is missing is a published charge for dinar accounts, and the fix is to
publish one.

Core systems do have charge-currency-versus-account-currency machinery with defined
rate types, but it is used for corporate and trade charges. Retail fees are set per
currency at published round numbers, and the amount charged has to match the published
schedule. A converted figure of BHD 2.559 is not on any tariff sheet.

The dinar account never goes overdrawn, so `tests/test_tariff.py` calls this guard
directly.

## 18. Is the opening balance an entry or the starting value of the fold?

It is the starting value of the fold. Both accounts open at zero, so this makes no
arithmetic difference. The opening balance is not an event, so it is not in the entry
listing.

## 19. Does a zero balance earn interest or attract a fee?

Neither. "Positive balances only" excludes zero, and the fee tests for a negative
balance, which also excludes zero. The dinar account sits at zero for four days.

At zero this is moot, but the strictness of the comparison is not moot in general.
`NUMBERS.md` shows that at a fee of exactly 30.00, day three lands on zero and escapes
only because zero is not negative.

## 20. Does the capitalising credit earn interest on the day it is paid?

No. Day six accrues on 390.00.

If the credit were inside its own accrual base the calculation would refer to itself.
The schedule is computed from the balances first and the entry is written afterwards.

## 21. Intraday posting order

On day one a credit of 1,200.00 and a debit of 950.00 share a booking day. Reordered
debit first, the account touches −950.00 during the day.

It makes no difference, because the rule tests the closing balance. Events are applied
in stream order within a day and only the day's closing figure is assessed.

Posting order has been litigated heavily in retail overdraft practice. Reordering
transactions high to low within a day, which maximises the number of times the balance
goes negative, led to litigation and settlements, and banks now publish their posting
order.

## 22. There is no period close

The engine restates day two on day five and again on day six. A core banking system
cannot do that. The day's trial balance was struck, the ledger rolled, regulatory
returns filed, and a statement may have been produced.

The whole six day window is modelled as one open period. This is a large gap between
this model and a production system, and it is why real back-value corrections post
forward. A production implementation would need a period status and a back-value limit
refusing a value date before the last closed period.

## 23. Business days or calendar days?

Six consecutive calendar days, with no holiday calendar applied.

Core systems carry a holiday calendar per currency, and value dates landing on
non-business days roll under a stated convention. The UAE moved to a Saturday and
Sunday weekend in 2022, while Bahrain kept Friday and Saturday, so the two accounts
would run on different calendars and a value date valid for one could be invalid for
the other.

## 24. Authorisation events carry a value date the model has no use for

E3 and E8 both carry value dates. A hold is a memo item with no ledger impact, so a
value date is undefined for it.

The value date is recorded and ignored. The authorisation decision uses the booking
day for both halves of its balance query, because an authorisation asks about money
available today. A hold is normally given a placement timestamp and an expiry.

## 25. Hold expiry

Auth-B is never settled within the window.

There is no expiry in this model, because the six day window sits inside every scheme
window and Auth-B was declined so it holds nothing. If it had been approved, its hold
would depress available balance indefinitely. Holds expire in roughly seven days for
ordinary retail, up to thirty one for hotels and car hire, and immediately for cash.

## 26. Over-settlement, duplicate settlement, settlement of a closed authorisation

None of these occur in the stream and none is specified.

A settlement consumes at most the outstanding hold and the excess posts, since a
clearing cannot be refused. Card schemes permit over-settlement within a tolerance
that varies by merchant category, the canonical case being a restaurant tip
adjustment. Duplicate clearings against one authorisation are guarded by matching on
the authorisation identifier. I did not implement that guard, and the hold arithmetic
degrades safely without it.

## 27. Reversal semantics beyond the single case given

A reversal inherits the original entry's value date, as if it had never happened,
while a contra posts at today's value date and corrects forward. The brief chooses
reversal by giving E9 a value date of day two. A reversal declaring a value date that
conflicts with its original is refused.

A reversal resolves an event identifier to a list of entries. E10 shows why: one
credit, three instalment entries, so three compensating entries.

Reversing the same event twice is refused, and the guard is derived by scanning the
log, because an append only store has no flag on the original that could be set.

The brief gives no reason code. Who bears the fee depends on whether the original
debit was a bank posting error, a merchant reversal, a customer dispute, or fraud, and
a bank-caused error normally means the fee is refunded. The failing test's description
assumes bank error, but the brief never says so.

## 28. Forward value dating

Every backdated case here reaches backwards and no event carries a future value date.

The two date query handles it. A forward-dated credit must not count towards available
balance for an authorisation decision, since a credit that has not reached its value
date is not spendable. The authorisation check uses the booking day as the value date
ceiling.

## 29. No debit interest on overdrawn days

The brief gives an overdraft fee and no debit interest. The account spends three days
overdrawn, at −395.00, −205.00 and −230.00, and accrues nothing on those days.

I follow the brief. Unarranged overdrafts normally charge interest on the overdrawn
balance, typically at a substantial annual rate, in addition to or instead of a flat
fee. The UK abolished flat unarranged overdraft fees in favour of a single simple
interest rate in 2019, which would make a fee-only design non-compliant there.

## 30. Two different balance definitions coexist

The fee rule tests the ledger balance, which excludes holds. The authorisation rule
tests the available balance, which includes them.

Both stay, as given, because they answer different questions. On day two the account
is positive at 250.00 for fee purposes and has 50.00 that can be spent. Criterion 1
invites the same confusion, where subtracting the 200.00 hold gives −570.00, which is
not the ledger balance.

## 31. Is there a floor on value dates?

The window bounds, enforced by the event models. A value date outside days one to six
is refused at construction.

A production system would use a back-value limit, commonly thirty to ninety days with
tiered approvals.

## 32. Replay idempotency

Event identifiers must be unique, and a repeat is refused. Replaying the same event
twice into an append only store would post it twice with no way to take the second one
back.

## 33. Rounding rule and its behaviour on negatives

Half up, with negative numerators refused.

No accrual in this data is a tie, so the choice between half up and half to even is
never exercised. See `NUMBERS.md`. Half up below zero is ambiguous, so it raises.

## 34. Criterion 1 names a number the system never prints

The criterion is accepted, and −370.00 is correct. That figure appears in no line of
the report. The day five section shows −395.00, because by then the fees have been
charged, and the final section shows 225.00.

## 35. End of window disposition

Auth-A finishes settled with nothing outstanding. Auth-B was declined, so the brief's
note that it is never settled within the window does not apply, and it holds nothing.
Had it been approved, its hold would still be live at the end of day six, would appear
in the day six authorisation states, and would never have touched the ledger balance
or the interest.

## 36. Sharia compliance on the dinar account

Many Bahraini retail accounts are Sharia compliant, where interest is prohibited.
Interest cannot be credited and an overdraft charge has to be structured as a service
fee.

I assume a conventional product, since the brief specifies interest on both accounts.
The brief does not give the product type, so crediting 0.008 of interest may not be
permitted.

## 37. Withholding tax on capitalised interest

None applies. Neither the UAE nor Bahrain levies personal income tax. The mechanism
exists in most jurisdictions and would deduct before crediting.

## 38. No cross-currency total is printed

There is none. The two accounts hold different currencies and `Money` refuses to
combine them, so no combined figure appears in the report. There is no exchange rate
in scope.
