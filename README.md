# In-memory account ledger core

This is an append-only ledger. It replays ten events across two accounts and
prints, for each of six days, the closing balance, any restatements, any fees
charged, the state of every authorisation, and any errors.

There is no web layer, no persistence, no user interface and no database.
Everything is in memory and runs from one script.

## Running it

```sh
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

./.venv/bin/python run.py                              # the per-day report
./.venv/bin/python -m pytest                           # 133 pass, 1 fails on purpose
./.venv/bin/python -m pytest -m "not known_failure"    # green
```

The suite exits non-zero on a normal run. See [The failing test](#the-failing-test).

## The three dates

| date | what it means |
|---|---|
| arrival | where the event sits in the list we were handed |
| booking day | the day the event becomes known to the system |
| value date | the day whose balance the event lands on |

Usually all three agree. Twice in this stream they do not.

E7 happens on day five and carries a value date of day two. It reaches back into a
day already reported on. The ledger does not touch the day two entries. It writes a
new entry dated to day two, and every balance that depends on day two changes.

E10 happens on day five but is listed last, after E9, which happens on day six. This
is the only place where the listed order and the booking day order disagree, so the
engine handles E10 as a late posting.

A balance query therefore needs two dates.

```python
ledger.balance("ACC-001", value_date=2, known_as_of=4)   #  250.00
ledger.balance("ACC-001", value_date=2, known_as_of=5)   # -395.00
ledger.balance("ACC-001", value_date=2, known_as_of=6)   #  225.00
```

Those three answers are the day two balance as the system knew it at the end of day
four, day five and day six. A query taking one date can only produce the last one.

## Reading the output

The report walks day by day. For each account it shows the closing balance as known
at the end of that day, which is what somebody looking at the account that evening
would have seen.

Below that come any restatements, meaning earlier days whose closing balance changed
because of something that arrived today.

Fees charged today appear with the day each one takes effect, so a fee charged on
day five with effect from day two shows under day five.

Every authorisation is listed with its state and how much is still held.

Errors come last, meaning anything the engine refused. A declined authorisation is
not an error and appears with the authorisations.

A final section prints every day's closing balance once all ten events are in.

The day two section shows 250.00, the day five section shows it restated to minus
395.00, and the final section shows 225.00.

## What happens

The account opens empty, takes in 1,200.00 and pays out 950.00 on day one. The engine
approves an authorisation for 200.00 on day two, and it clears for 185.00 on day four,
releasing the unused 15.00. A second settlement on day four points at an authorisation
that was never granted, so the engine refuses it and the 180.00 stays put. On day five
a debit for 620.00 arrives dated back to day two, which pushes days two, four and five
into the red and earns three overdraft fees of 25.00 each, charged that day but dated
to the days that went negative. The engine declines an authorisation for 90.00 on the
same day, because by then there is nothing to lend against. On day six the backdated
debit is reversed. The principal comes back in full. The 75.00 of fees does not,
because nothing in the rules provides for refunding one.

Final positions are AED 390.92 and BHD 10.008.

## The failing test

The brief asks for one failing test against your own design. It prints:

```
Auth-A was approved on day 2 but as known at the end of day 5 that day closed
at -395.00, so the hold of 200.00 would have left -595.00
```

Balances are restated when the past changes. Authorisation decisions are not. Auth-A
was approved on day two against a balance of 250.00, and once the backdated debit
restates that day to minus 395.00 the approval could not have been granted. The engine
cannot check this, because it does not record the balance a decision was judged
against and nothing revisits a decision.

It carries a marker, so `pytest -m "not known_failure"` gives a clean run. It is not
marked `xfail`, which would make the suite exit zero.

## The documents

| file | what is in it |
|---|---|
| `NUMBERS.md` | every constant and what happens at half of it |
| `AMBIGUITIES.md` | the questions the brief leaves open, how each was settled, and the cost of the alternative |
| `REJECTED.md` | the acceptance criteria refused, with the arithmetic, and approaches abandoned during the build |
| `DESIGN.md` | scaling, value dating in production, the authorisation lifecycle, and what was cut |
| `WORKLOG.md` | notes kept during the build |

## Layout

```
ledger/
  base.py         strict and frozen pydantic configuration, inherited by everything
  money.py        whole numbers of minor units, with a currency that never coerces
  currency.py     AED at two decimal places, BHD at three
  rounding.py     round half up over integers
  constants.py    every tunable number in one place
  events.py       the five event types, as a discriminated union
  entries.py      what moves a balance, carrying both dates
  outcomes.py     what happened to each event, including refusals
  ledger.py       the append only store and the two date balance query
  holds.py        authorisation holds, also append only
  tariff.py       charges, published per currency
  allocation.py   splitting an amount into parts that add back up
  interest.py     daily accrual and the single capitalising credit
  engine.py       replay, the end of day sweep, capitalisation
  report.py       the per-day output
stream.py         the ten events, in the order given
run.py            replay and print
```
