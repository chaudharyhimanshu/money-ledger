# Worklog

## 2026-08-24, afternoon and evening

The whole session was done on paper. I am glad I did not write a line of code,
because my first reading of the brief was wrong in a way that would have cost me
a rewrite.

The first thing I missed is that each event has two different dates, and they are
not the same question. There is the day an event happens and the day it matters.
They concur on eight of the ten events so it is easy to read straight past. Then
on day five E7 arrives with a value date of day two, and a day I already reported
on suddenly has a different closing balance to what it did yesterday. Nothing was
edited. A new entry landed behind it.

Once I had seen that, I looked for another one and found it. E10 happens on day
five but is listed tenth, after E9, which happens on day six. That is the only
place where the listed order and the booking day order disagree. I decided to keep
the listed order and treat E10 as a late posting.

So there are three dates to keep track of: the day the event happened, the day we
heard about it, and the day it lands on.

I worked the arithmetic by hand and then checked it with a short script. There are
three fees. A debit dated back to day two lowers day three, four and five by 620.00
as well. Day three ends at 5.00. I first thought the day two fee was what kept it
positive, which is the wrong way round. It stays positive despite the fee.

I also worked out that Auth-B has to be declined. The brief says "if Auth-B is
approved", and separately says Auth-B is never settled inside the window. By the
time it is asked there is nothing left to lend against.

I went through the acceptance criteria and marked the ones that are wrong. Four
are clearly wrong. Criterion 4 took longer. Its intent is fine, but the wording
puts it in conflict with criterion 3.

## 2026-08-25, 10:00

I considered Decimal and chose plain integers instead. Decimal is exact but it is
not rounded, so 415.00 times 0.0004 gives 0.166000 and stays that way until
someone calls quantize. That leaves the precision rule depending on a habit. Whole
numbers of fils mean an unrounded amount cannot be written down at all.

I used pydantic for the record types. Its default mode turns 25.0 into 25, the
string "25" into 25, and True into 1. That is worse than no validation, because it
looks like validation. Strict mode on the shared base class fixes it. I added a
test file that checks strict mode is on. Turn strict off and six of its nine
checks fail.

I threw away my first balance query. I had written it to take one day, so it could
only tell me what was true at that moment. The report has to say what day two
looked like at the end of day four. With one date the only way to get that is to
print it while the replay is standing in the right place, which makes the report
depend on how the loop is written. The second version takes both dates.

I also made holds an append only log. I started with a hold object that had a
status field getting reassigned, then realised that a mutable status next to an
append only ledger means the system is not append only, and there would be no
history behind the records the availability check reads.

Then I hit the fee sweep. A fee is dated to the day it is charged for, so it sits
inside that day's own closing balance, and read literally the rule never stops.
Day two goes to minus 395.00, which is still negative, so another fee, and so on.
What stops it is the once per day limit together with sweeping days in ascending
order. Neither is obvious, so I wrote the reasoning into the code and added a test
that runs the sweep twice and checks nothing new appears.

The first full replay matched the numbers I had worked out by hand.

## 2026-08-25, 15:37

The report had a bug on its first run. Outcomes record which event they belong to
but not which account, so the Auth-Z rejection and the Auth-B decline were printed
under the dinar account as well as the dirham one. I only saw it when I read the
output.

While writing the tests I asserted that available balance on day five is minus
155.00, and got minus 230.00. I assumed the engine was wrong. It was not. Minus
155.00 is what the decision was taken against, and minus 230.00 is what you get
from the finished engine, because the fee sweep has run by then. Both are correct
answers to different questions. The test now checks both.

I replaced the failing test. My first one asserted that the day two fee is
refunded after the reversal, which is criterion 6 restated, and I had already
written that criterion 6 is wrong. A test that fails because it asserts something
I refused does not say anything about my own design. The new one is about Auth-A.
It was approved on day two against 250.00, and once the backdated debit restates
that day to minus 395.00 the approval could not have been granted. When the past
changes the balances are restated. The decisions already taken are not. The engine
cannot check this, because it does not record what a decision was judged against.

I left it failing. Xfail makes the suite exit green, and the brief asked for a
failing test. There is a marker if you want a clean run.

I also had to correct myself on criterion 6. I had written that the fees survive
because the ledger is append only. That is wrong. Append only stops you editing a
record. It does not stop you writing an offsetting one. The reason the fees stand
is that the rules contain no provision for refunding one. I fixed it in three
places.

For the ambiguities document I computed each counterfactual: 390.93, 390.96,
441.00, 390.80, 210.70. Day three only goes negative once the fee is above 30.00.
At exactly 30.00 it lands on zero and is not charged, because the rule tests for
negative, and zero is not negative.

I finished with 133 tests passing and the one test I left failing.

## 2026-08-25, 16:17

I wrote the arch design file: what breaks when the log grows, what value dating
costs a UAE-licensed bank, how an authorisation can end, and what was cut.

I benchmarked the sweep. A six day sweep over 100,000 entries takes 1.4 seconds.
The day count costs more than the log size does, and the arithmetic is in the
arch design file.

A normal replay does 56 balance folds against 14 entries: 42 from the sweep, 12
from capitalisation and 2 from the availability checks.

Writing the authorisation section turned up a gap I had not noticed. The reversal
handler touches ledger entries and never touches holds, so reversing a settlement
leaves the hold consumed. The ledger and the hold log disagree from that point on.
I did not fix it. It is recorded in the document.
