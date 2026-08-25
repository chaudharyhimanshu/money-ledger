# Design notes

## Append only at scale

Every read folds the whole log. `Ledger.balance` walks every entry and filters by
account. `has_fee_for`, `entries_by_event` and `reversal_of` do the same.
`HoldLog.outstanding_total` walks every hold record ever written.

The end of day sweep breaks first, because it is the only part that is superlinear.
For each booking day it re-examines every day up to that point, and each of those is a
fold. With E entries over D days the sweep costs `accounts * E * D(D+1)/2`.

Replaying the ten events does 56 balance folds and 3 fee-check folds against a log of
14 entries. The 56 breaks down as 42 from the sweep, 12 from capitalisation, and 2
from availability checks on the two authorisation requests.

Cost of a six day sweep as the log grows:

| entries | sweep |
|---|---|
| 100 | 1.3 ms |
| 1,000 | 14.2 ms |
| 10,000 | 126.9 ms |
| 100,000 | 1,383.2 ms |

The sweep is linear in log size for a fixed window, so 100x the volume is 100x the
time. The day count is the second problem. Here D is 6 and `D(D+1)/2` is 21. A bank
closing books daily across a year has D around 250, where the same term is 31,375.
That is roughly 1,500 times more folds over the same log.

### Where state accumulates without bound

The entry list grows forever, which is what append only means. The cost is that every
read walks all of it.

The hold log is the one that hurts first. Placed, consumed and released records are
never removed, so an availability check walks holds that closed years ago.
Availability runs on the authorisation path, on every card transaction, where the
latency budget is tight.

The outcome log grows by one record per event, including refused ones.

None of the three is compacted or archived.

### Cheapest change that defers it

Materialise the closing balance per account per value date and update it on append.
The sweep then reads a number instead of folding the log, and its cost drops from
`accounts * E * D(D+1)/2` to `accounts * D`. The same treatment on the hold log gives
a per-account outstanding total, which takes availability off the full scan.

A materialised balance only answers the current `known_as_of`. A query about what was
believed on some past day still folds the log. That split is workable, because "what
is true now" runs constantly and "what did we believe on day four" is an audit
question that runs rarely.

This does not solve the problem. The log still grows. The next step is a period close
that writes a checkpoint balance per account and the set of open holds, so a fold
starts at the checkpoint instead of at zero. That also creates the boundary past which
entries can be archived.

## Value dated entries in production

A value date that points backwards changes a number the bank has already used for
something else.

| what it touches | what a back-value entry does to it |
|---|---|
| accounting close | changes a balance inside a closed period, and the general ledger cannot be edited to match |
| prudential reporting | changes a figure already filed with the CBUAE, so it needs a restatement or a compensating adjustment in the current period |
| VAT | explicit banking fees in the UAE carry 5% VAT, so a back-valued fee moves output tax into a period whose return has gone in |
| customer statements | a statement issued for a period that later changes has to be reissued, and the customer has to be told why the closing balance moved |
| interest | changes the accrual base for days already accrued, so the engine recalculates those days and posts the difference as an adjustment |
| transaction monitoring | AML systems score patterns over rolling windows, and a backdated entry changes a window already scored, so a reportable pattern can appear after the fact |
| dormancy | CBUAE dormant account rules run off the date of last customer-initiated activity, and a back-value entry can move that date |
| conduct | charging a fee against a day the customer could not have seen and could not have cured is an exposure under the CBUAE Consumer Protection Standards |

This implementation charges that fee, as the brief requires.

### One control before go-live

Refuse any value date earlier than the last closed accounting period.

Anything earlier posts as an adjustment in the current open period, carrying a reason
code, a reference to the intended original value date, and a second approver. The
general ledger and the filed returns stay unchanged, and the intended value date is
stored on the adjustment as data.

## Authorisation lifecycle

An authorisation in this model can end without a settlement that matches it exactly.

| how it ends | real scenario | what I would mandate |
|---|---|---|
| declined at request, no hold placed | available balance would go below zero | record the balance the decision was judged against as well as the reason text, so a later restatement can find approvals it no longer supports |
| under-settled, remainder released | item out of stock, discount at the till, tip not added | this is correct for single-message retail. Drive the release off merchant category, because hotel, car hire and split shipment clear in parts and the authorisation has to stay open |
| over-settled, hold fully consumed and the excess posts | restaurant tip adjustment, fuel dispenser final amount | accept within the scheme tolerance for the merchant category and flag anything above it for investigation |
| never ends, hold stays active past the window | merchant abandons the transaction, terminal fails after approval | expiry per merchant category, around seven days for ordinary retail and thirty one for travel and entertainment, with a scheduled release that writes a record |

The last row is a defect. This model has no expiry, so an approved authorisation that
is never settled holds funds indefinitely.

Three more endings should exist and do not.

| missing ending | real scenario | what I would mandate |
|---|---|---|
| merchant void before clearing | customer cancels at the till | an explicit reversal event that releases the hold and writes a release record |
| settlement reversal | the clearing itself is reversed | restore the hold to outstanding or close the authorisation explicitly. The reversal handler here touches ledger entries only, so reversing a settlement leaves the hold consumed and the two logs disagreeing |
| duplicate clearing | the same clearing presented twice | match on the authorisation identifier and refuse the second unless the merchant category permits partial clearing |

## What was cut

| simplification | risk it defers |
|---|---|
| in memory only, no persistence | nothing survives a restart, and there is no crash recovery |
| single process, no concurrency control | two settlements against one hold can race, and two authorisations can both pass the availability check against the same funds |
| no period close | back-value reaches any day, and the ledger has no immutable boundary |
| no hold expiry | an approved authorisation that is never settled holds funds indefinitely |
| authorisation decisions are never revisited | approvals stand that the restated history cannot support. This is the failing test |
| settlement reversal does not restore holds | hold accounting drifts from ledger accounting after any reversal |
| no duplicate settlement guard | a repeated clearing posts twice |
| no debit interest | overdrawn balances cost a flat fee only, which is not how overdrafts are priced |
| fee tariff holds one currency | a non-AED account going overdrawn raises instead of charging |
| no back-value limit | value dates are bounded only by the six day window, not by policy |
| every read folds the whole log | read cost grows with the log, with no index or snapshot |
| nothing is archived or compacted | storage and read cost grow without bound |
| two hard-coded accounts, no lifecycle | no opening, closing, dormancy or status |
| no maker-checker on postings | any caller can append any entry |
| the report is the only output | anything not printed is unreachable without writing code |
