# The trend lift, read on a real trend; and the warm ranker (14 Nov, 21:30 CET)

**In one line**: on the first trend with the lift live (Game Consoles, 19:30-20:15 UTC) the lift at ^0.75
neither helped nor hurt: 2.60 expected purchases per 100 requests with it, 2.63 without (+0.03 ± 0.20 once
the arms' earlier difference is taken out). The trend products it adds do sell, and the products they push
down lose as much. The same window settled something else: on warm requests `v9` beats `v16`.

## The trend

Organic purchases in Game Consoles went from about 10 to about 100 per five minutes at 19:30:00 UTC, stayed
there (11 % of all purchases) and fell back to 4 at 20:15:00. The detector logged it 41 seconds in, at lift
3.6, and let go a minute and a half after the end. It is the first trend since 15:30 UTC and it kept the
earlier pattern: half past an odd UTC hour, 45 minutes.

## What the lift did

`python realtime_analyisi_leaderboard/trend_read.py --sub "Game Consoles" --since "2026-11-14 19:30:00"
--until "2026-11-14 20:15:00"` (our feedback, realised) and `python scripts/arms.py 19:30 20:15` (expected).
Odd versions have no lift, even versions have it.

| During the trend | Requests | Trend products per list | Lists with one | Purchases per 1,000 impressions, slots alike: trend / other | Realised purchases per 100 requests: all = trend + other | Expected per 100 |
|---|---|---|---|---|---|---|
| No lift (v21, v23, v25, v27) | 1,979 | 0.17 | 11.6 % | 15.79 / 2.98 | 3.18 = 0.25 + 2.93 | 2.632 |
| Lift ^0.75 (v22, v24, v26, v28) | 6,121 | 1.37 | 49.8 % | 4.89 / 2.28 | 2.70 = 0.77 + 1.93 | 2.602 |

In the 105 minutes before the trend both groups ran the same code and showed 0.13 Game Consoles products per
list; the expected metric read 2.186 and 2.122. So the lift's effect on the organisers' number is
(2.602 - 2.632) - (2.122 - 2.186) = **+0.03, with a standard error of about 0.20**. The reference read 2.14.

Three things are measured, and they fit together:

1. **A trend product is wanted.** Inside the lists that hold one, it takes 50.4 % of the clicks where its
   slots predict 32.4 % (224 lists, +5.8 se) and 61.8 % of the purchases where they predict 39.7 % (76
   lists, +3.9 se). In the arms without the lift, the few the ranker picked on its own took 41 % of the
   clicks against 21 % predicted.
2. **The lift delivers them.** Half the lists get one, a third of those in slots 1-3, and they bring +0.52
   purchases per 100 requests (0.77 against 0.25).
3. **The total does not move.** Whatever enters a list pushes the ranker's own candidates down, and slot 1
   alone holds 45 % of our purchases. On the expected metric the others lose what the trend products gain.

So ^0.75 is harmless and, on one trend, worth nothing. This does not say whether more lift or less would be
better: point 1 says the trend products still sit too low, point 3 says moving them up is paid for by the
others. Only arms at different strengths, or a lift that never takes slot 1, can separate the two.

**What to do**: nothing on this evidence. If the two-hour pattern holds there are trends at 21:30, 23:30,
01:30, 03:30, 05:30 and 07:30 UTC; each adds about 8,100 requests, and by Sunday morning the comparison
with and without the lift has a standard error near 0.08. Optional, and only with Javier's go-ahead for a
swap tonight: give half of the even arms a second strength (for instance ^1.5) so the night also measures
the dose.

## The warm ranker: `v9`

`python scripts/arms.py 17:45 20:15`, pooled by the ranker that answers each kind of request:

| Warm requests | Ranker | Requests | Expected purchases per 100 | Reference |
|---|---|---|---|---|
| The night so far | **v9** (v21 to v24) | 8,162 | **1.99** | 2.09 |
| The night so far | v16 (v25 to v28) | 8,151 | 1.76 | 2.09 |
| Trend window only | **v9** | 2,480 | **2.39** | 2.19 |
| Trend window only | v16 | 2,488 | 1.84 | 2.19 |
| Outside the trend | v9 | 5,682 | 1.82 | |
| Outside the trend | v16 | 5,663 | 1.72 | |

A lead of 0.24 on 8,150 requests each is about three standard errors (the spread between arms running the same code is 4.75 per warm request, measured in `pool_arms.py`), in the same direction in and out of
the trend, and with all four `v9` arms at or above 1.99 in the trend window against 1.68 to 2.21 for the
`v16` arms. This passes the bar set in the 20:30 note (more than 0.15 and two standard errors): **warm
requests go to `v9`**. Most of the lead was made during the trend, which is also when the final's points
are made: `v9` was above the reference there (2.39 against 2.19), `v16` well below.

Cold requests are not settled: `v9` 2.97, `v9w` 2.63, `v16` 3.07, `v16w` 3.14 on about 2,500 each
(reference 1.82). The lead of `v16` over `v9` seen at 95 minutes is gone; `v9w` trails `v16w` by 0.51, about
two standard errors.

For the final's single arm, as it stands: `v9` for warm requests; for cold ones `v9`, `v16` or `v16w`,
level so far, and not `v9w`. `v9` everywhere (`v21` / `v22`) is the simplest set-up that satisfies both and
leads the night overall (+0.39 over the reference on 6,551 requests).

## Lenses

- **Generalisation**: the lift is keyed on a subcategory selling above its usual share, whatever it is; the
  final's trends are new ones and the detector does not know the schedule. One trend is one sample.
- **Reference**: in the trend window it read 2.14 overall; we read 2.61 across all arms.
- **Technique**: a boost that reorders a slate has a displacement cost whenever the top slot dominates;
  the usual remedies are to cap the boosted items per slate or to protect the first slot.

## Update, 22:45 CET — Face Cream (21:30 UTC): a trend in views, not in purchases (first 12 minutes)

All arms now carry the lift at full strength (`v31` v9, `v32` v9 x organic, `v33` v9b, `v36` = `v32` with
new products x1.5). The second trend of the evening is not like the first.

| Organic stream, per 5 minutes | Before | During | Ratio |
|---|---|---|---|
| Face Cream views | 35-70 | 274-292 | x5.5 |
| Face Cream carts | 2-4 | 20 | x7 |
| Face Cream purchases | 2-3 | 6-7 | x2.5 (0.8 % of all purchases) |
| Game Consoles purchases (19:30 UTC) | 10 | 100 | x10 (11 % of all purchases) |

The detector reports a lift of 11.1 for Face Cream: it is carried by views and carts on a very small base.

On our carousel, 21:30-21:42 UTC: 1,820 Face Cream impressions, **2 clicks, 0 purchases**. Other products
at the same slots get about 11 clicks and 2 to 3 purchases on that many impressions.

| Arm | Face Cream products per list | Lists with one | Lists with one in slot 1 | Impressions / clicks / purchases |
|---|---|---|---|---|
| `v31` (v9) | 0.25 | 17 % | 1.1 % | 130 / 0 / 0 |
| `v33` (v9b) | 0.27 | 17 % | 1.5 % | 108 / 1 / 0 |
| `v32` (v9 x organic) | 1.74 | 57 % | 13.6 % | 964 / 1 / 0 |
| `v36` (organic, new x1.5) | 1.82 | 57 % | 16.0 % | 618 / 0 / 0 |

v9 multiplied by the lift still leaves these products out of most lists, because it rates them far below
the tenth candidate for most shoppers; the clicks agree with it. The organic factor sees the same spike of
views as the detector and fills more than half of the lists. Sent to the model session at 21:45 UTC with
the suggestion that the lift follow the purchase ratio, with a floor on the number of purchases. The whole
window per arm, with the organisers' metric, follows when the trend ends.

## Correction, 23:00 CET — Face Cream was a real trend; the flaw was in the organic factor, and it is fixed

Two things in the section above were wrong or incomplete, both set right by the model session.

- **It is a trend in purchases too.** My x2.5 compared the trend with the half hour before it, when Face
  Cream was already selling 3.5 times its usual share. Against the day (96 purchases in the 12 hours
  before, 0.67 per five minutes) it is x11 to x12, as the detector said; views x5.5, carts x17. It is a very
  small subcategory: x11 of very little.
- **The cause was the organic model, not the detector.** It learned which product a shopper buys next among
  the candidates the rules retrieve on an ordinary day. Face Cream products were candidates only because the
  lift put them there, so its answer for them meant nothing, and it sent them to the top. Reproduced offline
  on 120 requests with a made-up x10: v9 with the lift 0.24 trending products per list, v9 x organic with the
  lift 3.05 (slot 1 in 24 % of lists), v9 x organic without a trend 0.02.

What stands from the section above is what the carousel showed: 1,820 impressions, 2 clicks, no purchase,
with `v32` and `v36` filling more than half of their lists. That is what made it worth acting on before the
trend ended.

**The fix**, live since 21:51:01 UTC (`reco.recommend.level_trending`, commit 938b995): while a trend runs,
a trending product takes the organic factor of the products v9 scores about as high, so the organic model
has no say on it and it keeps the place v9 x lift gives it. Live after the fix: `v31` 0.21 trending products
per list, `v32` 0.24, `v33` 0.20, `v36` 0.08, none in slot 1. Before: `v32` 2.24 per list (slot 1 in 19 %).

For the reads from here on: `v32` and `v36` count from 21:52 UTC; their 21:30-21:51 window is the flaw, not
the organic factor. In every trend, the first thing to look at is the number of trending products per list
by arm: the arms should be within a factor of two of each other.

## Update, 23:25 CET — Face Cream, the whole window, and the arms by regime

**The store.** Face Cream purchases per five minutes from 21:30 to 22:15 UTC: 6, 7, 8, 11, 14, 9, 5, 15, 9
(0.67 on an ordinary five minutes of the day: about x14); views 204 to 292 (about x5). It stopped at 22:15
on the dot and the detector let go at 22:16:33.

**After the fix (21:52-22:15 UTC), per arm**: Face Cream products per list 0.30 (`v31`), 0.20 (`v32`), 0.22
(`v36`), 0.30 (`v33`); in slot 1 in 1 to 3 % of the lists. In line with each other, as they should be.
The first Face Cream product of a list (688 impressions, mean slot 5.0) sold 2.91 per 1,000 against 2.47 for
the other products at those slots: placed where v9 x lift puts them, they sell like their neighbours, which
is what a right score looks like. (Before the fix: 1,820 impressions, 2 clicks, no purchase.)

**The arms by regime**, organisers' expected metric (`scripts/arms.py | pool_arms.py`). The organic arms
count from 21:55 UTC.

| Minutes (UTC) | Regime | `v31` v9 | `v32` v9 x organic | `v36` organic, new x1.5 | `v33` v9b | Reference |
|---|---|---|---|---|---|---|
| 20:35-21:30 | no trend (v9 = v31 + v34 + v35) | 2.162 on 4,811 | 2.440 on 3,097 (+1.9 se) | not live | 2.293 on 1,986 | 2.022 |
| 21:55-22:15 | trend, Face Cream | 2.054 on 1,052 | 2.249 on 1,057 (+0.7 se) | 2.052 on 732 | 1.980 on 757 | 1.906 |
| 21:55-22:20 | all minutes since the fix | 2.088 on 1,340 | 2.209 on 1,315 (+0.5 se) | 2.176 on 908 | 2.069 on 935 | 1.908 |

Nothing to read yet after the fix: 25 minutes. The organic arms together are +0.12 over `v31` (+0.6 se).

## Update, 01:35 CET — Vitamins (00:30-01:15 CET): a large trend, read whole

**The store.** Vitamins purchases per five minutes from 23:30 to 00:15 UTC: 103, 97, 101, 110, 101, 124, 108,
84, 116, against 13.4 on an ordinary five minutes of the day (1,932 in the twelve hours before): x7.8, and
11.0 % of all purchases against 1.5 % usually. Views about 1,000 against 250 (x4), carts about 200 against
22. It started and stopped on the minute; the detector had it 43 seconds in and let go at 00:16:47 UTC.

**Our carousel, per arm** (8,099 requests; all arms carry the lift at full strength):

| Arm | Requests | Vitamins products per list | Lists with one | Lists with one in slot 1 | Purchases per 1,000 impressions, slots alike: Vitamins / others | Expected purchases per 100 (organisers) |
|---|---|---|---|---|---|---|
| `v31` v9 | 2,374 | 1.87 | 48.7 % | 21.9 % | 4.48 / 2.85 | 2.702 |
| `v37` v9 picks the ten, organic orders them | 1,662 | 2.01 | 50.2 % | 18.5 % | 3.66 / 2.33 | 2.427 (-1.3 se) |
| `v32` v9 x organic | 2,399 | 1.65 | 45.0 % | 15.6 % | 3.12 / 2.15 | 2.532 (-0.9 se) |
| `v36` organic, new products x1.5 | 1,664 | 1.60 | 45.1 % | 16.1 % | 4.34 / 2.72 | 2.880 (+0.9 se) |

Reference 2.142. The arms show the trend alike (within a factor of 1.3): no repeat of the Face Cream flaw.

**Do the later trend products of a list still sell?** Yes. The first Vitamins product of a list (mean slot
3.3) sold 7.6 per 1,000 against 5.4 for the other products at those slots; the second (slot 4.3) 4.0
against 2.4; the third and later (slot 6.7) 2.2 against 1.3. A list that takes several does not waste them.

**Is the trend product in the right place?** In v9's lists, yes: of the clicks made in lists that hold
one, 50.6 % went to it where its slots predict 54.3 % (-0.7 se), and 65.6 % of the purchases against
67.9 %. In the organic arms it gets more than its slots predict: clicks 51.6 % against 37.9 % for `v37`
(+2.3 se) and 54.3 % against 44.1 % for `v32` (+1.7 se), and they put it first less often (15.6 to 18.5 %
of the lists against 21.9 %). The organic factor lets other products pass a trending one that v9 x lift
had placed right. Inside the trend `v37` and `v32` read 0.28 and 0.17 under `v31` (1.3 and 0.9 se);
outside it, over the 105 minutes without a trend since 23:25 CET, the four arms are level (2.27, 2.24, 2.28,
2.27). One trend: a question with a mechanism behind it, not a finding.

**Our gap to the next team inside the trend**: +0.19, +0.17 and +0.17 on the 15-, 30- and 60-minute boards
at 00:59 CET; +0.10, +0.14 and +0.14 at 01:15; +0.06 to +0.09 in the hours without a trend. Three large
trends so far (Game Consoles, Vitamins, and before them the afternoon's): each is where the gap is made.

## Update, 15 Nov 03:20 CET — Leashes (02:30-03:15 CET): a large trend, the four arms alike, and the gap did not open

**In one line**: the store sold ten times its usual share of Leashes, our four arms showed the trend alike,
and inside it we read 2.34 against 1.95 for the reference; but the next teams rose with us (2.29 and 2.28),
so the gap was +0.06 where the two large trends before gave +0.10 to +0.33.

**The store** (`shop.events` per 5 minutes, against the subcategory's share from 14 Nov 09:00 to 15 Nov
01:00 UTC): Leashes went from 1.93 % of the views to 7.9 % (x4.1) and from 1.11 % of the purchases to
11.4 % (x10.3), flat over the 45 minutes (9.9 to 13.7 % per 5 minutes). As large as Game Consoles. The
server found it 36 seconds in. Its log line says `{'Leashes': 2.8}`: that is the lift at the moment of
detection, from the views. The line is printed only when the set of trending groups changes; the lift then
follows the purchases of the last five minutes, capped at 12. It is not the size of the trend.

**The four arms on our carousel** (8,099 requests; the last column is the organisers' metric):

| Arm | Requests | Trending products per list | Lists with one | Slot 1 is a trending product | Expected purchases per 100 |
|---|---|---|---|---|---|
| `v31`: v9 | 2,024 | 2.22 | 50.8 % | 22.2 % | 2.372 |
| `v38`: v9, new x1.5 | 2,068 | 2.23 | 50.9 % | 21.6 % | 2.415 |
| `v39`: organic order | 2,023 | 2.14 | 51.5 % | 20.5 % | 2.197 |
| `v40`: organic order, new x1.5 | 1,984 | 2.22 | 50.4 % | 21.4 % | 2.376 |

Before the trend: 0.14 to 0.18 per list, 7 to 9 % of the lists, slot 1 in 1.2 to 1.5 %. `hold_trending`
does what it was written for: the organic arms put a trending product first as often as v9's arms
(20.9 % of the lists against 21.9 %, -1.1 se; in the Vitamins trend it was 18.5 % against 21.9 %).

**The two questions inside the trend** (01:30-02:15 UTC, reference 1.951). The organic order: -0.107
(-0.7 se), cold requests -0.56 (-1.8 se), warm ones +0.24 (+1.7 se); 1.10 EUR per request against 1.16.
New products x1.5: +0.111 (+0.8 se), warm +0.26 (+1.9 se); 1.22 EUR against 1.03. The rule for the final
lets the organic order be up to one standard error below in the minutes of a trend: this trend is inside
it. It is the second trend in a row in which the organic arms read below v9's (Vitamins: -0.9 and -1.3 se
for the two organic arms of then).

**Against the other teams** (organisers' metric, the whole team, requests left unanswered included;
`trend_board.py`):

| | Reference | Us | team_14 | team_03 | team_17 | team_37 |
|---|---|---|---|---|---|---|
| The 45 minutes before (00:45-01:30 UTC) | 1.905 | 2.148 | 1.774 | 2.131 | 2.110 | 2.106 |
| Inside the trend (01:30-02:15 UTC) | 1.951 | 2.340 | 2.285 | 2.280 | 2.170 | 2.210 |

The teams that were already at our level rise inside a trend by 0.06 to 0.15: the shoppers who follow it
arrive with trending products among their recent views, and any ranker that follows the session shows
them. We rose by 0.19. team_14 rose by 0.51 and team_33 by 0.35 (1.85 to 2.20): a better version went in
around the start of the trend. Our gap to the next team was +0.02 before and +0.06 inside (+0.07 on cold
requests). Two teams over 45 minutes differ by 0.10 by chance, so this is neither clearly the +0.10 to
+0.33 of Game Consoles and Vitamins nor clearly less; quarter-hour by quarter-hour it read +0.03 to +0.05
where those two read +0.10 to +0.33. What it does say: the trend is no longer ours alone. team_14 and
team_03 were within 0.06 of us inside it.

**A flag, not a finding: across lists, the trending products sold less than their slot neighbours.**

| Trending product of a list | Impressions | Mean slot | Clicks per 1,000 (others at those slots) | Purchases per 1,000 (others) | Purchases: observed, expected by slot |
|---|---|---|---|---|---|
| first | 4,098 | 3.3 | 9.8 (16.2) | 2.68 (6.25) | 11, 25.6 |
| second | 3,009 | 4.2 | 6.3 (7.9) | 0.66 (2.30) | 2, 6.9 |
| third or later | 10,629 | 6.8 | 4.2 (4.6) | 0.66 (1.12) | 7, 11.9 |

Twenty purchases where the slots give 44 (3.6 standard errors below) and 104 clicks where they give 139,
on 22 % of all our impressions (this table was read on 8,059 of the trend's 8,099 requests). In the earlier trends the same table read above the neighbours. But inside
a list that holds a trending product, it takes the share of the clicks its slots predict (44.1 % against
42.5 %, 236 lists) and of the purchases (`v31`: 6 of 18, against 35.5 %). So the deficit is between lists,
not inside them: in `v31` the lists that hold a trending product gave 1.75 purchases per 100, the lists
that do not, 2.82. Two readings that the slots cannot tell apart. Either the lift brings the trend into
the lists of shoppers with weak signals, who buy little whatever they are shown: no harm. Or four trending
products in the list of a shopper who is after something else take the place of products that would have
sold: harm. The test that counts is the model session's table with v9's own prediction held equal:
observed over predicted for the trending products by how many of them a list holds, and for the other
products of those lists. Put to the model session as a question; the organisers' metric says the minutes of
the trend were our better ones (+0.39 over the reference against +0.25 before it).

**New products**: the batch of 03:00 CET arrived on the dot (100 products) and none was in any arm's lists
in its first twenty minutes (3,600 lists), as the hold-out intends; from the twentieth minute they were in
19 % of the lists: 16 % in `v31` and `v39`, 21 and 23 % in the two arms with the new-product lift.

### The model session's answer (03:30 CET): no harm at the margin, and what to watch in the next trends

The share inside a list answers the question. In the lists that hold them, the trending products took
44.4 % of the clicks where their slots predict 42.6 % (239 lists, all arms, the complete trend) and 34.4 %
of the purchases where the slots predict 32.4 % (61 lists); in Vitamins the clicks read 50.6 % against
54.3 %. Slot for slot they did as well as the other products of the same list, and those are the shopper's
own best candidates, which v9 ranks above the ones the trending products pushed out (its ranks 7 to 14
without the lift). A product that does as well as the best of the list cannot be worse than the ones
ranked below them. A lift twice too strong would show as a share of about 27 % (0.5 x 42.5 / (0.5 x 42.5
+ 57.5)); it is on the prediction in two trends of different size. The first, second and later trending
products of a list read 0.43, 0.29 and 0.59 of their slot neighbours on purchases: no fall with the rank,
so the later ones are not substitutes of the first. The gap across lists is then which requests they are:
a list fills with trending products where the shopper's own signals are weak, and there every product
draws about three quarters of the slot average. 1.75 purchases per 100 against 2.82 is what those requests
are worth, not what the lift cost.

The table with v9's prediction is not built: it needs a pull of the night and a replay of the store on the
serving laptop, for an answer that would not change what serves the final (no cap and no weaker lift goes
in without a live test). What would change it, read here after the trends of 04:30 and 06:30 CET: the
share of the clicks inside a list, all arms together, clearly under the slots' prediction — under 0.8 of
it on 300 lists or more. That is the case for lift ^0.5, one number in the arms (it ran as `v35` on
Saturday), and it has to reach the model session before 08:00 CET. `trend_read.py` now prints that line
for all arms together, with the ratio to the prediction.
