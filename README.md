# What I found when I went looking for edge in prediction markets

## 1. What this is

Over about three weeks in July 2026 I ran a systematic search for
exploitable mispricing on Kalshi, a US-regulated prediction market where
contracts pay $1 if an event happens and $0 if it doesn't. Polymarket, its
larger crypto-settled counterpart, served as a reference venue. The search
covered contracts resolving between early June and late July: about
2.2 million of them, and roughly 9.5 million historical price bars carrying
best bid and ask. No book depth, which is a limitation that matters later.
The categories were sports, crypto, weather, politics, financial indices,
and the exotic tail of multi-leg parlays. Every hypothesis was registered
before its data was examined, with the evidence thresholds fixed in advance,
and every apparent edge was attacked with the specific artifact checks
described below before being believed.

The headline: **Kalshi is efficient net of retail taker costs wherever this
platform could test it with power, which turned out to be wherever an
external anchor already polices the price. The rest is measured ignorance,
not efficiency.**

Two things make that sentence worth a reader's time. First, the nulls are
*powered*. For every "no edge" claim I state the smallest edge the test
could have detected, its minimum detectable effect, because "no edge" only
ever means "no edge larger than what I could see." Where a test couldn't
see effects of economically relevant size, I say "untested," not
"efficient," and several fashionable-looking categories land in that bucket.
Second, four times during the program I found what looked like real,
tradable edge, once worth several cents a contract, and four times it
dissolved under my own artifact checks. Those four incidents, and the rules
they forced, are the most useful thing this document contains.

This is not investment advice, and the program's conclusion is not that
prediction markets are unbeatable. It is narrower and, I think, more useful:
an accounting of which inefficiency classes a careful retail participant can
rule out, at what statistical strength, under which cost structure, and
which classes remain open because the data to test them does not yet exist.

## 2. What the method could see, and what it structurally could not

Everything here rests on one kind of evidence: price history compared with
resolution outcomes. The method asks a single question in many forms. When
the market said 20%, how often did the event happen? Then it asks whether
any systematic gap between price and frequency survives realistic trading
costs. That question can be asked with power, at scale, from public data.
But it is one question among several that "is this market beatable?"
contains, and honesty requires the full list.

There are, roughly, six ways to make money in venues like these:

1. **Statistical mispricing:** prices systematically wrong about
   frequencies. *This is what I tested.*
2. **Market making:** earning the bid-ask spread as a resting-order
   liquidity provider. Invisible to my data, because it requires modelling
   order cancellation and queue position, and its economics depend on maker
   fee tiers I don't trade under.
3. **Latency arbitrage:** being faster than other participants to react.
   Invisible: no message-level data, and irrelevant to a manual trader.
4. **Information edge:** an outside model (weather ensembles, poll
   aggregation, sports models) that beats the market's forecast. Invisible
   by construction: my method asks whether prices predict their own errors,
   never whether an external model predicts prices' errors. These are
   different questions, and only the first was tested.
5. **Venue incentive capture:** rebates and liquidity programs. Not
   mispricing, and not pursued.
6. **Risk premium harvesting:** being paid a small premium for absorbing
   flow others won't. Partially visible. The one persistent bias I confirmed
   (a roughly one-cent in-play sports effect, discussed later) most
   plausibly lives here.

So when this document says "efficient," it means: no exploitable pattern of
type 1, at retail taker costs, at the tested statistical power. A market
maker with a fee advantage, or a forecaster with a better model, could
profit in a market this document calls efficient, and nothing here
contradicts them. The costs matter as much as the statistics. Kalshi's taker
fee peaks at 1.75 cents per contract and falls toward the extremes, and the
median quoted spread in my corpus is 1 to 2 cents in most categories, which
puts the typical hurdle around two to three cents and considerably higher in
the thin ones. Every expected-value figure here is net of the actual spread
on each observation rather than an assumed one, at a stated order size.

A knowledgeable skeptic's strongest objection deserves answering here rather
than in a footnote. *One month of quiet-season data on one venue, analyzed
by one person: aren't your "powered nulls" really statements about a single
June-to-July window?* Partly, yes. The category-level calibration results
are bound to their season and corpus, and I present them that way. Three
things do not depend on the season: the fee arithmetic, which is a schedule
rather than a sample; the break-even structure of cross-venue trades, which
is algebra; and the methodology, since the selection-mechanism forensics and
the power discipline transfer to any window anyone cares to re-run them on.
Distinguishing which conclusions are which is half the point of writing this
down.

One more scope line, drawn sharply because a month of quiet data cannot
speak to it. Everything here describes quiet-period behavior. Whether these
markets stay efficient inside a major event window, an election night with
retail flow orders of magnitude above baseline, is a different regime. It is
explicitly untested here, and it is the one place my own research program
still holds an open position.

## 3. What was ruled out, and at what strength

Before the results, the three things that make a null worth reading, and a
note on how to check any of it.

**The detection threshold.** Any test can fail to find an effect; the
question is how big an effect it would have caught. For every result below
I compute the *minimum detectable effect*, the smallest edge the test had
an 80% chance of detecting, given the observed variability and sample size.
"No edge" then means something specific: no edge larger than that number.
The figure is computed against a corrected significance bar, because I am
scanning dozens of price-band-by-category cells at once and, at the usual
5% threshold, roughly one in twenty such cells produces a "significant"
result from noise alone. Correcting for the size of the family raises the
bar by about 37%, and every threshold quoted here includes that penalty
unless I say otherwise.

One trap inside that, which caught me four separate times before I named it.
A detection threshold is only meaningful if its population unit matches the
unit the decision turns on. Ticks, trades, fills, contracts and per-band
observations are not interchangeable, and a threshold computed on the wrong
one can be off by an order of magnitude while looking rigorous. The version
that nearly slipped through here: a criterion written in terms of expected
value per executed trade, checked against a threshold computed on
fifteen-minute price increments. There are thousands of the increments and
dozens of the trades, so the number came out reassuringly tiny and meant
nothing. Write the criterion's unit and the threshold's unit next to each
other. If they differ, the threshold is invalid on its face.

**Complete coverage.** Within any series I tested, I used *every* contract
that resolved, not a sample. This sounds pedantic and turned out to be the
single most consequential methodological choice in the program. §5
explains what happened the one time I violated it.

**One filter, which I should have disclosed here originally.** The
calibration engine excludes observations whose quoted spread exceeds 10
cents, because a mid sitting between a 20-cent bid and a 60-cent ask is not
a price anything trades at. That drops 14.6% of observations, and far more
in some categories: 36% of financials, 23% of economics, 17% of mentions.
A reader asked whether that filter had been audited the way §5 says every
sampling rule must be. It had not, so I audited it, and the last part of §5
is what came back.

**The cost hurdle.** Kalshi charges takers a fee that peaks near 1.75 cents
per contract at even-money prices and falls toward the extremes, and an edge
must clear that fee plus the spread it crosses. Across 260,000 observations
the median quoted spread is 1 to 2 cents in nine of twelve categories, 4 to
5 cents in financials and economics, and effectively unbounded in the exotic
parlays, so the typical hurdle is around two to three cents rather than the
three to six I assumed before measuring it. Every expected-value figure
below uses the actual spread on each contract, so the numbers never depended
on that assumption, but the framing did.

**A note on checking this.** The analysis code behind every number below is
public: the fee model, the calibration engine with its interval and
detection-threshold machinery, the jump-drift and resting-order simulations,
and the synthetic-fixture test suites. It lives at
**https://github.com/jklein07/prediction-market-efficiency**.
What it does not contain is market data: Kalshi's data terms restrict
redistributing archived datasets, so nothing raw or derived ships with it.
That is a real limit on reproducibility. The compensation is that every
headline result carries its sample size, its detection threshold and its
cost assumptions, in the text where it appears or in the appendix table, so
the arithmetic can be checked without the underlying rows. Illustrative
numbers inside the narrative come from those same tables. You should not
have to take my word for any of this; you should be able to recompute the
arithmetic and read the code that produced it.

### Ruled out with power

Most of these tests could see effects of three to seven cents. A few cells
are weaker than that, up to eight or nine, and I flag them where they occur.
None of them found anything that survived costs.

**Pregame sports, main lines.** Across 17,749 match-winner contracts
(tennis, MLB, World Cup, WNBA, UFC, every contract in those series), prices
six hours before the event are calibrated to within about two percentage
points in every band. Contracts trading near 25 cents resolved yes about
25% of the time; contracts near 75 cents, about 75%. Detection thresholds
ran 3.8 to 5.1 cents. No band offered positive expected value on either
side after fees and spread. This confirms on a regulated US exchange what
the sports-betting economics literature has reported on European exchanges
for two decades.

**Pregame sports, strike ladders.** The obvious follow-up: main lines get
professional attention, but what about the long menu of derived contracts:
game totals, run spreads, first-five-innings totals, World Cup goal counts?
Fewer eyes, thinner books, plausibly sloppier prices. I fetched 15,011
contracts across four such series and found the same answer: calibrated
within a couple of points, 246 to 1,891 observations per band, thresholds
2.5 to 7.0 cents, nothing tradable. I had pre-committed to the direction I
expected (totals markets biased toward the over, a well-documented retail
tendency in sports betting). It did not appear.

That 15,011 was complete coverage of the four series when I ran it in July
and is now 95.6% of them, because 684 more contracts closing inside the same
window have settled since and were never backfilled. They are late-arriving
records rather than an outcome-selected subset, so this is not the H-001
problem in a new costume, but it is a claim that quietly expired between
running the analysis and writing about it, which is its own small lesson
about how long "complete" stays true.

**Crypto price strikes.** Hourly Bitcoin and Ethereum contracts, which ask
whether the coin is above a given strike at the top of the hour (will BTC be
above $62,250?), are the cleanest null in the dataset. Measured five minutes before expiry across 4,136 observations,
every single price band's implied probability sat inside the confidence
interval of its realized frequency: 2.1% implied versus 2.1% realized at
the cheap end, 97.9 versus 98.3 at the expensive end. Every expected value
was negative after fees. This category also served as a negative control.
If a research pipeline reports edge in a market that is continuously
arbitraged against a live spot price visible to everyone, the pipeline has
a bug. Mine repeatedly declined to find one, which is a large part of why I
believe its other outputs.

**Post-move drift.** If prediction markets under-react to news, then after
a large confirmed price move the price should keep drifting the same way,
and a trader entering an hour or two later should profit. I tested this on
complete coverage of every long-lived contract that resolved in the window
(23,137 contracts, 1.4 million price bars), requiring a jump to be
confirmed by an actual trade rather than a quote flicker. In the categories
with enough resolutions to test properly the answer is a flat no. Entering
one hourly candle after the jump, weather gives 2,090 and 1,747
observations by direction, mentions markets 1,120 and 1,056, commodities 771
and 1,022, and sports 1,251 and 1,423. Corrected
thresholds run 3.4 to 5.9 cents in weather, mentions and commodities, and
expected values are negative nearly everywhere. Sports is a null here too,
but it rests on the complete-coverage calibration work above rather than on
this test's power. Whatever these markets do after news, they do it faster
than a person with a manual approval step can act on.

**Pregame momentum and reversion.** A separate question from calibration:
never mind whether prices are *right*, do they *trend*? If a contract drifts
up between six hours and one hour before an event, does it keep going, or
does it snap back? Across 341 to 1,091 observations in
the three cells with real samples, neither: every one of them has its
implied probability sitting inside the confidence interval of what actually
happened. Thresholds there run 5.8 to 8.5 cents corrected. Six further cells
split by direction of the move carry only 21 to 170 observations each, with
thresholds of 15 to 34 cents, and are reported as insufficient rather than
null. They could not have detected a large effect, let alone a tradable one.

**Passive capture of the one bias that is real.** Covered in §4. Rejected
with a powered test of its own, and for an interesting reason.

### Untested where it would have mattered

This is the more interesting half of the ledger, and the half most easily
lost when results get summarized.

Two categories sit in an uncomfortable middle. Mentions markets ("will the
president say X") and commodities cleared the bar for *large* effects but
not for economically interesting ones: their corrected thresholds were 4.8
and 4.8–5.9 cents respectively, against a typical hurdle of two to three
cents. They cannot rule out an edge anywhere in the two-to-five-cent band,
which is the whole of the economically interesting range rather than part of
it. Calling them efficient would be a category error. They are untested
where it counts.

And then the thin cells. Financial-index events (77–119 observations,
thresholds 9.1–11.8 cents), entertainment (151–161, 7.3–8.9), long-dated
crypto (104–171, 9.0–11.2), economics releases (75–76, 12.1–12.5), politics
(77–90, 12.2–13.8), elections (20–32, 16.1–21.0), science and technology
(18, 17.9–24.3). Those figures are the
*uncorrected* thresholds, the only place in this document where that is
true, and I quote them that way because applying the family penalty makes
them worse by another 37% without changing anything about the conclusion.
A threshold of twenty cents means the test would have missed a twelve-cent
edge, an enormous and obviously exploitable one, without blinking. These
categories were not
found efficient. They were not measured. Reporting them as nulls would have
been the most consequential error available to this program, and for a
while I did report them that way, before an audit of my own power
calculations forced the correction.

Why so thin? These are slow markets. An election contract resolves once; a
crypto hourly resolves 24 times a day. A 31-day window produces hundreds
of thousands of the latter and dozens of the former, and no amount of
analytical care manufactures resolutions that have not happened yet. The
honest response is to wait, and to say so, which is what a follow-up study
does: pre-registered before the data exists, with price bands fixed in
advance on theoretical grounds rather than chosen afterward to maximize
significance, targeting exactly these categories once enough of them have
resolved.

## 4. What was found

**A real bias, too small to keep.** In live, in-play sports, meaning roughly
the last hour of a match, favorites are systematically underpriced and
longshots overpriced: contracts priced at 92.5 cents win 95.8% of the time
(n=905); contracts priced at 7 cents win about 4% of the time. This is the
classic favorite-longshot bias, documented in betting markets for seventy
years and already reported on modern prediction venues. My contribution is
confirming it at complete coverage on a regulated venue, and then doing the
arithmetic on capturing it.

The arithmetic is where it stops being interesting. Taking liquidity, the
edge is worth about a cent per contract *after* the fee and after entering
at the touched side of the spread. Positive, but small, and smaller than
this study's threshold for telling an expected value apart from zero in that
price range, which is 2.6 to 4.2 cents. So two different things are true at
once, and keeping them apart matters. The calibration gap is statistically
solid: significant in all three favorite bands in the first half of the
corpus, and still significant in two of the three when the test is repeated
on the later half it was not fitted to. The claim that a retail participant
can convert that gap into money is not something this data can support.

A caveat about that phrase "out of sample," since §5
shows a completely fake edge surviving exactly this test: a date split
catches a result that was fitted to one period, not a result produced by a
biased sampling rule, because a biased rule contaminates both halves
equally. It is worth something here only because this corpus is complete
coverage, every contract in the series, so there is no sampling rule left to
do the biasing. On the volume-ranked corpus in §5 the same split was worth
nothing, and I treated it as reassurance anyway.

One of those out-of-sample bands did produce a positive expected value of
+3.6 cents, and I do not count it, for two reasons that are worth separating.
The first is power: splitting the corpus in half halves the sample behind
each band and raises its detection threshold accordingly, so that band's
threshold is 6.8 cents on the out-of-sample half against the 2.6-to-4.2
range the full corpus supports, and +3.6 sits below the bar it would have to
clear. The second I only found when I went back to reproduce it. Its
bootstrap interval sits directly on zero, and whether the lower bound lands
above or below depends on the resampling seed: across ten seeds it excluded
zero six times. I had originally written that the interval excluded zero,
which was one draw from a distribution that straddles it. Counting the one
cell out of six that cleared an uncorrected bar would have been the exact
move this document's power discipline exists to prevent, and it turns out
the cell did not reliably clear even that.

*A note on order size, because it moves this number.* Kalshi rounds its fee
up to the whole cent per **order**, not per contract, so the effective
per-contract cost falls with size wherever the raw fee sits below a cent,
which is exactly the favorite price range. In the 70–80 cent band the same
edge is worth about 1.3 cents per contract on a one-contract order and about
2.0 cents on a hundred-contract order. Unless a figure says otherwise, it
assumes a one-contract order, which is the conservative end. The
larger figures also assume the whole order fills at the quoted price, which
I could not verify, because my data records the best bid and ask but not the
size available behind them.

Providing liquidity instead, posting resting orders and collecting the
spread rather than paying it, fails for a reason worth naming precisely.
In 3,820 simulated resting orders, using a deliberately pessimistic rule
that only counts a fill when the market traded *through* my price, orders
filled 62% of the time. That sounds like plenty of free spread. But the
fills arrived preferentially in exactly the games where the favorite was
collapsing: I was buying from people who knew something I didn't, at the
moments they knew it. This is adverse selection, and it consumed more than
the entire spread. The passive version lost about a third of a cent per
fill, against a positive cent for simply crossing the spread, so posting
turned a small winner into a small loser.

That result needs a boundary drawn around it, because it is the single
easiest sentence in this document to over-read. What failed is **retail
passive posting: retail fee tier, no ability to cancel and re-post as
conditions change, no inventory management.** It is emphatically *not*
evidence that market making does not work on Kalshi. Professional market
makers are active on this exchange. Susquehanna built the first dedicated
prediction-markets desk at a major quantitative trading firm and makes
markets on regulated venues including this one, and DRW, IMC and Jump have
since built desks of their own. Their edge lives exactly where mine was
absent: cancellation speed, and a maker fee roughly a quarter of the taker
rate. Spread capture is a real business for participants equipped to do it.
It is not a retail strategy, and my experiment measures only the retail
version. The bias is real; at retail terms it is a risk premium someone
else is better positioned to earn.

**The structure that explains the nulls.** Every powered null in this
study sits in a category where an external anchor already polices the
price: spot crypto, sportsbook lines, index futures. Kalshi is sharp
exactly where being wrong is cheap to correct. The corollary cuts both
ways: the un-anchored categories are where inefficiency could survive, and
they are precisely the ones the data cannot yet power a test on.

**The break-even structure of cross-venue "arbitrage."** The same contract
often trades on both Kalshi and Polymarket, at prices that visibly differ.
A recent large-scale study by Gebele and Matthes, *Semantic Non-Fungibility
and Violations of the Law of One Price in Prediction Markets*
([arXiv:2601.01706](https://arxiv.org/abs/2601.01706)), aligned 100,000+
events across ten venues. They found persistent execution-aware deviations
of 2–4% and attributed them to *semantic non-fungibility*: nominally identical
contracts differ subtly in resolution terms, and positions cannot be netted
across venues, so arbitrage capital cannot force convergence. I can carry
their mechanism one step further, and the step changes the conclusion. A
cross-venue convergence trade earns its margin *m* only if both contracts
settle the same way, and loses roughly the full dollar when they do not.
The trade is profitable in expectation only when the mismatch probability
*p* satisfies: **p < m/(100+m)**. A 2-cent margin requires p below about
2%; a 5-cent margin, below 4.8%. Those are demanding bounds. I reviewed the
top 25 candidate pairs against the full rules text on both venues and
rejected 11 of them, a mismatch rate of 44% among pairs that a lexical
matcher had ranked as near-identical. The rejections were off-by-one
thresholds, "confirms" versus "completes," a tie-handling clause that flips
one venue's outcome and not the other's. Twenty-five is a small review and
the rate carries a wide interval, but the direction is not subtle.

What "full rules text" means here is worth spelling out, because it is the
difference between my divergence numbers and anyone else's. The text a
matcher naturally reads is the summary on a Kalshi market page, and that
summary is not what settles the contract. The binding terms are the
CFTC-certified contract rules reached through the series, plus the
event-level settlement sources, and those two documents routinely say more
than the summary does. One of my pairs looked like a minor tail mismatch in
the truncated summary and turned out, in the certified terms, to differ on
the operative definition: an exact tie in the underlying measurement
resolves YES on one venue and NO on the other. The related habit I had to
break was qualifying a whole batch of pairs from one exemplar. Checking a
template on a single market, plus a weak per-item invariant like matching
names, is not verification of the batch. You have to diff the full property
across every item before you treat any of it as verified.

On my ten pairs whose events have since resolved, settlements agreed ten
times out of ten. That sounds reassuring until you compute the bound it
buys: a 95% upper limit of 28% on the true mismatch rate, an order of
magnitude short of break-even. The deviations Gebele and Matthes measure are
real and their explanation is right. What the deviation is *not*, until
someone bounds the mismatch rate, is an opportunity.

I wanted to compare their divergence magnitudes against mine and I cannot,
which is worth explaining because the reason is instructive. My pairs
diverge by about a third of a cent at the median, against their 2–4%, and
that looks like evidence that stricter verification produces tighter
agreement. It is not. The median contract in my pair set trades at one cent
and three quarters of my quotes sit below a nickel, because the set is
dominated by a nomination ladder full of candidates nobody expects to win. A
contract priced at a penny cannot diverge by three cents, so my small
absolute gaps are a fact about which contracts I happened to verify rather
than about how I verified them. Measured relative to price my gaps are much
larger than theirs, which is equally uninformative for the same reason.
Testing the idea properly needs matched price levels, and with 36 pairs
clustered at a penny I do not have the range. The general rule I take from this, for any spread
trade across nominally equivalent instruments anywhere, is that **a margin
means nothing until the non-equivalence tail is bounded, and a manual review
process bounds it only as well as its measured miss rate.**

I should be explicit about what happened to this line of work, because the
arithmetic above is all that came of it. The cross-venue program was
supposed to answer a narrower question. Does one venue systematically lead
the other, and can the lag be traded? It never ran. Its pre-registration
required at least fifty contract pairs verified as equivalent
before any analysis began, and strict rules review never produced more than
forty-seven, of which one later failed re-review and ten retired when their
events resolved. I could have topped the count back up by reviewing more
candidates from the queue; what I could not do was give newly verified pairs
the weeks of price history the test also required, and a pair reviewed in a
hurry is precisely the kind that widens the mismatch tail the arithmetic
above says is already the binding constraint. So the program closed without
producing an estimate. Publishing a lead-lag number from a study whose own
entry condition was never met would have been the easiest self-deception
available here, and the entry condition existed to make that call before I
knew what the number would have been. The question is open, not answered,
and reopening it needs both the pairs and a bounded mismatch rate.

## 5. Four edges that dissolved

Everything above is only as credible as the process that would have caught
it being wrong. Here is that process failing to be fooled, four times, in
increasing order of subtlety, and then a fifth case where it did not catch
the problem at all and a reader did.

### The edge that was a sampling choice

The first calibration tables I ran were thrilling. Across thousands of
sports contracts, cheap longshots were resolving yes far more often than
their prices implied, by five to nine percentage points depending on the
band, with a contract at 15 cents winning 20% of the time. Expensive
favorites showed the mirror image. The implied strategy was almost
embarrassingly simple: buy cheap contracts, sell expensive ones, collect
several cents per contract after fees. That is not a marginal edge. That is
a business.

I have to hedge that magnitude, and the reason is itself a small lesson. The
observation table behind those first numbers was rebuilt many times against
a growing corpus and no longer exists in its July form, so when I tried to
reproduce the exact figure I had originally believed, I could recover the
mechanism and the direction but not the size. The gap reconstructs at five
to nine points and the strategy at a few cents rather than the ten I
remember. Numbers you do not record are numbers you cannot check later, even
against your own pipeline.

It was also backwards. The textbook favorite-longshot bias runs the *other*
way: bettors overpay for longshots, they don't underpay. Finding the
reverse on a modern exchange would have been a novel result,
which should have been the first warning and instead felt like discovery.

So I attacked it. I restricted to contracts with tight bid-ask spreads, in
case wide quotes were polluting the midpoints: it survived. I split the
sample by date and re-ran on the later period only, in case it was a fluke
of one week: it survived. I deduplicated contracts belonging to the same
game, in case correlated outcomes were inflating my sample: it not only
survived, it got *stronger*, which I took as confirmation.

What I had not examined was how those thousands of contracts came to be in
my dataset. Fetching price history is slow, so I had prioritized: pull the
highest-volume contracts first. Volume seems like a neutral quality filter:
more trading, better prices, cleaner data. It is not neutral at all.
Games that end in upsets generate frantic late trading; games that go
according to form do not. Ranking by lifetime volume had quietly
over-selected the games where the underdog won, and an over-selection of
upsets looks exactly like longshots being underpriced.

The test was to stop sampling. I fetched *every* contract in all eight
match-winner series across those sports, 17,749 of them, upsets and
blowouts alike, and re-ran
the identical analysis. The effect vanished to the third decimal. What
remained was the ordinary favorite-longshot bias, in the ordinary
direction, at ordinary magnitude. Nothing about the market had been
inefficient. My sample had been.

### The safeguard with the same disease

Look again at the robustness check that made the false edge *stronger*: I
deduplicated correlated contracts by keeping, per game, the one with the
highest volume. Same mechanism, one level down. Within a single game, the
most heavily traded strike is the dramatic one: the total that stayed live
into the ninth inning, the spread that swung. My safeguard was selecting on
the outcome it existed to protect against.

I found this only because the deduplicated numbers were absurd: sixty-point
calibration gaps, a contract priced at 84 cents resolving yes 20% of the
time. Effects that large in liquid markets are not discoveries, they are
diagnostics, and this one pointed at my own code. Pooled analysis of the
same contracts showed no such gap. The rule that came out of it: every
sampling key, tie-break, and deduplication rule in the pipeline must be
provably independent of outcomes. It sounds obvious written down. It was
not obvious while writing a helper function whose only apparent job was to
avoid double-counting.

### The nine-cent edge sitting on quotes nobody would honor

Later, hunting for post-news drift, one category lit up: financial-index
contracts, where entering after a confirmed upward jump appeared to earn
nine cents. The sample was small but the effect was large and the mechanism
was plausible, since index contracts should lag the underlying, and a retail
venue might reprice slowly.

The flaw was in what my backtest "paid." Entry prices came from the last
quoted ask in these books, and these books are thin. A quote that has not
moved since the underlying index moved is not a price you can trade. It is
a stale limit order that will be pulled or repriced the instant anyone
tries to hit it, and if it *does* fill, it fills because the person on the
other side has decided they want your side of it. I re-ran the analysis
requiring that entry occur only at prices where a trade had actually
printed. The nine cents became six with a confidence interval spanning
zero, and the small sample never had the power to say more. Historical
quotes are promises nobody was ever obliged to keep, and a backtest that
transacts against them is measuring an imaginary market.

### The spread that paid its earners nothing

The fourth is the maker experiment from §4, and it belongs here because of
how it failed. A 62% fill rate on resting orders is a good fill rate. The
edge appeared to be real, and the mechanism for capturing it appeared to be
available. It died only when I asked *which* orders filled: conditioning on
the state of the game at fill time turned free spread into a systematic
transfer to better-informed counterparties. No sampling error, no stale
data. The analysis was correct and the strategy simply loses money for a
reason that only becomes visible when you look at the conditional
distribution rather than the average.

### What the four have in common

Each survived at least one standard robustness check before dying to a
targeted one. Two came from my own sampling decisions; one from trusting
recorded prices as executable; one from averaging over a conditional
distribution. None came from bad statistics in the textbook sense. The
confidence intervals were computed correctly throughout, on data that had
already been corrupted upstream.

The sentence I would put on the wall of any research shop: **in a nearly
efficient market, the most likely source of your apparent edge is your own
selection mechanism.** The corollary is a working habit rather than a
principle. When a result is good enough to be exciting, the first
hypothesis to test is not that the market is wrong, but that the pipeline
is.

### And one filter, which somebody else found

After this went up, Josh B of OVERROUND read the code and pointed out that
the rule I had just written down, that every sampling key and tie-break and
dedup rule must be provably independent of outcomes, extends one step
further than I had taken it. A row filter is the same kind of decision, and
the spread filter had never been audited. He was right, and it is the one
place in the pipeline I had exempted from my own standard without noticing.

The audit says the filter removes exactly the population you would worry
about. The observations it keeps are calibrated almost perfectly, and the
ones it discards are not:

| horizon | group | observations | implied | resolved | gap |
|---|---|---|---|---|---|
| 1 hour | kept | 62,958 | 39.9c | 39.4% | −0.5 pts |
| 1 hour | **dropped** | 8,155 | 47.7c | 38.8% | **−8.9 pts** |
| 6 hours | kept | 60,413 | 39.1c | 39.2% | +0.1 pts |
| 6 hours | **dropped** | 11,757 | 51.0c | 40.0% | **−11.0 pts** |
| 24 hours | kept | 45,468 | 35.5c | 35.4% | −0.1 pts |
| 24 hours | **dropped** | 8,706 | 47.8c | 45.2% | **−2.6 pts** |

Read alone, that is damning. An eleven point calibration gap sitting in the
14.6% of the data I had excluded, in a document whose headline is that the
market is efficient, is the exact shape of a result being produced by its
own filter.

What rescues it is the second question, which I had not asked either. Those
markets are wrong, but nobody can act on it, because the spread you would
cross to reach the mispricing is far larger than the mispricing. At the six
hour horizon the discarded rows carry a median spread of 70 cents against
that 11 point gap, and even the tightest quarter of them sit at 29 cents.
The worst single cell is the 40-to-60 cent band six hours out, where a 14.5
point gap sits behind a 91 cent median spread. You would pay ninety-one
cents of spread to collect fourteen cents of error.

So the filter survives, but for a reason I had not written down and had not
checked, which is a weaker position than I thought I was in. The honest
summary is that a filter I called a data-quality decision was also, silently,
part of the definition of tradability, and it took an outside reader to make
me prove it.

That is the argument for publishing the code alongside the claims. The four
above I caught myself, and this one needed somebody with no stake in the
answer, which is a thing you can only get by making the code readable and
then waiting.

### If you are replicating this

Two traps that cost me time and are invisible until they bite, neither of
them statistical.

The first is the corpus. Ask any dataset what window it actually covers
rather than what you asked it for. My first "thirty-day" crawl of settled
contracts turned out to hold about three hours of them, because the global
settled feed I was paging returns newest-first and the newest listings that
day were overwhelmingly multi-leg parlays, so the crawl spent its whole
budget inside a single evening. Crawling per series instead gave real
coverage. I am describing what I hit rather than a stable property of the
API, since I never went back to measure the feed composition and my stored
corpus is the post-fix one, which cannot show it. That is the point:
whatever venue you are on, query the resolution timestamps you actually
received before you believe the date range you intended.

The second is the price you calibrate against. Do not use a settled
contract's last traded price. By the time a contract settles its price has
converged to the outcome, so calibrating against it produces gorgeous curves
that measure nothing except that markets know the answer once the answer is
known. Use pre-close quotes at a fixed horizon, six hours out or one hour
out, chosen before you look. This sounds obvious written down and is very
easy to do by accident, because the settled record is the convenient one to
join against.

## 6. What stays running

Three instruments outlive this write-up, and each is designed to answer a
question this study window could not.

**The settlement-agreement counter.** Every cross-venue pair whose event
resolves adds one observation to the mismatch-rate measurement: did the two
venues actually settle the same way? Ten so far, ten agreements, which
bounds the true rate only at 28%, nowhere near the one-to-five percent that
would make the break-even arithmetic favorable.

The thing I got wrong about this instrument is worth stating, because I only
noticed it after publishing. Each verified pair yields exactly one
observation, at its resolution, so the ceiling is the number of pairs I have
verified rather than the time I let it run. With 36 live pairs the counter
tops out at 46 observations ever, and because those pairs all resolve in
2027 and 2028 it produces none at all before then. It is not slow, it is
stalled, and reaching the hundred resolutions that would make the bound
useful requires verifying roughly ninety more pairs rather than waiting. The
queue is now ordered by resolution date rather than match score, which is
what built a 2028-heavy book in the first place.

**The September calibration study.** The un-anchored categories (politics,
elections, weather forecasting) are the ones the summer could not power a
test on, and they are where inefficiency is most plausible precisely
because no arbitrage anchor polices them. The study is already registered:
three price bands per category rather than twelve, with the boundaries
fixed in advance on theoretical grounds (the favorite-longshot literature
locates effects at the extremes, so the bands are longshot tail, middle,
favorite tail), and the expected direction named per band before any data
exists. Coarser bands buy statistical power two ways: more observations per
cell, and a smaller family of cells to correct for. Pre-committing to them
is what separates a legitimate power gain from choosing the grouping that
produces the prettiest p-value after the fact.

Running the power projection forward from current accumulation says it will
probably not deliver all three categories. Weather clears comfortably,
politics is marginal and depends on where the floor is set, and both
election tails currently contain zero instances of the outcome that creates
the dispersion, which makes their variance unestimable rather than small. An
election longshot band where no longshot has yet won tells you nothing about
longshots, however many observations it holds. I would rather say that now
than discover it in September.

**November.** Everything in this document describes quiet-season behavior.
The one hypothesis the program still holds open is whether these markets
stay efficient inside a real event window: a midterm election night, retail
volume orders of magnitude above baseline, the moment when the marginal
participant is least likely to be a professional. No amount of quiet-season
data can answer that, and it is the only place where I would expect the
answer to differ.

## 7. What it added up to

Financially, the honest accounting is: one real bias found, worth about a
cent net of costs and too small for this data to tell apart from zero;
everything else either efficient where tested or untested where it would
have mattered; the plausible remaining
upside is a single event window in November, and it is a bet, not a plan.
Anyone hunting alpha in these venues at retail terms should expect the
market to be better than they are wherever an anchor exists, and should
expect their own tooling to generate more false edges than the market
yields real ones.

What the program certainly produced is the thing this document is: a
bounded map. Which questions are closed, at what strength; which are open,
and what data would close them; four named ways a careful person fools
themselves, with the checks that catch each; and one small piece of
arithmetic, p < m/(100+m), that turns "look at that spread" into a
question with a number in it. That was worth three weeks. Whether it is
worth more than that, November will say.

---

## Appendix: evidence inventory

Every terminal result, with the sample it rests on and the smallest effect
it could have detected. Detection thresholds are given first uncorrected,
then corrected for the size of the cell family being scanned; the corrected
figure is the one that governs. Unless noted, all expected-value figures
assume a one-contract order at the general taker fee rate, held to
resolution, entering at the touched side of the quoted spread. The
calibration and momentum results rest on a 31-day corpus of contracts
resolving 9 June – 9 July 2026; the post-jump drift study runs to 12 July;
the cross-venue quote collection covers 11 – 27 July.

| Result | Verdict | Sample | Detection threshold or bound | Power status |
|---|---|---|---|---|
| Pregame match-winner calibration | No edge | 161–1,636 per band | 2.8–3.7c / 3.8–5.1c | Powered; marginal in the thinnest bands |
| Pregame strike ladders (totals, spreads, goals) | No edge | 246–1,891 per band | 1.8–5.1c / 2.5–7.0c | Powered to marginal; 15,011 of the 15,695 now settled in-window (95.6%) |
| Crypto hourly strikes (negative control) | No edge | 205–717 per band | 1.4–9.8c / 1.9–13.4c | Powered in liquid bands |
| In-play favorite-longshot bias | **Real calibration gap**; EV ~+1c net of costs, below the EV threshold | 905–1,612 per band | 1.9–3.1c / 2.6–4.2c | Gap powered; out-of-sample replication in 2 of 3 favorite bands; EV not resolvable |
| Retail passive capture of that bias | Fails (adverse selection) | 3,820 orders / 2,371 fills | 2.1c (single pre-named test) | Powered against its 2c bar |
| Pregame momentum / reversion | No edge (cells with real samples) | 341–1,091 core; 21–170 directional | 4.2–6.2c / 5.8–8.5c core | Core powered; six directional cells insufficient (to 34c) |
| Post-jump drift, weather, mentions, commodities, sports | No edge | 771–2,090 per cell | 2.5–4.3c / 3.4–5.9c | Weather powered; mentions & commodities **untested in the 2–5c band**; sports rests on the calibration work, not this test |
| Post-jump drift, financials, economics, politics, elections, entertainment, sci-tech, long-dated crypto | **Insufficient data** | 18–171 per cell | 7.3–24.3c uncorrected | Not measured |
| Exotic multi-leg parlays | Untradable | — | — | No pre-resolution quotes exist |
| Cross-venue lead-lag / convergence | **Not measured**: entry condition unmet | 36 verified pairs vs 50 required | — | Program closed before analysis |
| Cross-venue settlement agreement | Running instrument | 10 resolutions | 95% upper bound 28% on mismatch rate | Stalled: ceiling is 46 at current pair inventory, none before 2027 |

A note on the last two rows, expanding on §4. The cross-venue program was
closed without producing a lead-lag estimate, because it had registered in
advance that it required at least fifty contract pairs verified as
equivalent. Strict rules review peaked at forty-seven; one of those failed a
later full-text re-review, and ten retired when their events resolved,
leaving thirty-six. What the collected data does support is the break-even
arithmetic in §4 and the settlement-agreement instrument in §6.

---

## Corrections

If something here is wrong, I would rather know. The analysis code is public
and every headline result carries the sample and threshold it rests on, so
errors should be findable, and four of the results in this document only
exist because a check caught something I believed.

Jon Klein, jonklein.quant@gmail.com, or open an issue at
[github.com/jklein07/prediction-market-efficiency](https://github.com/jklein07/prediction-market-efficiency).

---

## About this repository

This repository contains both the write-up above and the analysis code behind
every number in it. See **[CODE.md](CODE.md)** for what each module does, the
data policy, and how to run the test suite.

Licensed MIT. No market data is redistributed here; see CODE.md for why.
