# The store runs on a calendar; and four alternatives that do not help (14 Nov, 23:10 CET)

**In one line**: trends, promotions and new products arrive on a fixed clock, and if it keeps running the
two hours of the final hold a trend for 45 minutes, a promotion for 60 and a fresh batch of new products
for the last hour. That is where the room is. Inside a list, v9 has already taken what the shopper's and
the product's signals give: four more ideas were tested against its own prediction and none adds anything.

Why: four teams are within 0.03 to 0.07 of us on the short boards. Looking for what could still open a gap.

## The calendar

From `shop.catalog_updates` and the organic stream, 09:00-22:00 UTC on 14 Nov (CET = UTC + 1):

| What | When (UTC) | How long | Size |
|---|---|---|---|
| Trend: one subcategory sells about ten times its usual share | 09:30, 11:30, 13:30, 15:30, 19:30, 21:30 (none seen at 17:30) | 45 minutes | Game Consoles reached 11 % of all purchases, Face Cream 0.9 % |
| Promotion: prices drop 17 to 20 % | 10:30, 13:30, 16:30, 19:30 | 2 hours, then back to the catalogue price | 485 to 640 products, mostly different ones each time (1,274 promoted once, 497 twice) |
| New products | 10:00, 14:00, 18:00, 22:00 | they stay | 100 products over about 55 subcategories |
| Stock | every 5 minutes | | 3 out, 3 back |

Every 2, 3 and 4 hours, from the start of the practice round at 09:00 UTC: first trend at +0:30, first new
products at +1:00, first promotion at +1:30.

If it keeps running the same way:

- **Tonight**: promotion at 22:30; trend at 23:30; trend and promotion at 01:30; new products at 02:00; trend
  at 03:30; promotion at 04:30; trend at 05:30; new products at 06:00; trend and promotion at 07:30.
- **The final, 09:00-11:00 UTC**: the 07:30 promotion still on until 09:30; a trend from 09:30 to 10:15; new
  products at 10:00; a promotion from 10:30. A final that restarts the clock at its own start gives the same
  three events at the same minutes.

How to use it **without overfitting**: to read the arms by regime (trend minutes, promotion minutes, the
rest) and to rehearse tonight what the final will bring; not as a rule inside the recommender. The brief
says the final has new trends: the detector has to keep finding them in the stream, as it does.

## Where the points are, by regime

- **Trend minutes.** In the Game Consoles window we read 2.61 against the reference's 2.14, and over
  19:30-20:00 UTC 2.70 against 2.38 for the next team: a gap of 0.3 where the rest of the evening gives 0.05
  to 0.1. A trend is 45 of the final's 120 minutes.
- **Promotion minutes: a candidate.** For the products that were on promotion when they were shown (7.4 % of
  the impressions of the lists v9 had not seen, 17:00-20:20 UTC; mean price 0.835 of the catalogue price),
  observed over v9's prediction is 1.14 on clicks (se 0.09) and 1.29 on purchases (se 0.17, 56 purchases);
  never promoted 0.99 and 0.98; promotion over 0.99 and 1.02. In the conditional logit with v9's prediction
  held equal: +0.21 (z +1.0) on clicks, +0.62 (z +1.3) on purchases. Not significant on its own, and it
  agrees with the elasticity already in the findings (a 19 % drop sells x1.3 to x1.45). `recommend()` has a
  `price` multiplier that no arm uses. Worth the model session's test on the longer table: a promotion
  covers half of the final.
- **New products.** All shoppers together, observed over predicted purchases 1.35 (se 0.13) against 0.96 for
  the original catalogue: the model session's result, live as `v36` for known shoppers. The batch of 22:00
  UTC, in its first three minutes: 173 views, 9 carts and 2 purchases in the store on 69 of the 100
  products; 87 of our 591 lists already held one (mean slot 7.0 in `v31`, 5.6 in `v32`, 4.4 in `v33`, 5.4 in
  `v36`); 27 requests had one among the recent views, which makes them cold by the rules.

## Four alternatives that do not help

Tested on the model session's table of 30,891 lists v9 had not been trained on, with v9's predicted click
and purchase probability for every product shown (the control that slot dummies alone do not give).

| Idea | Test | Result |
|---|---|---|
| Wait a second longer, to see the shopper's next events | organic events of the same shopper from 6 s before to 8 s after the request, last 30 minutes | about 100 events for 5,220 requests: there is nothing to wait for |
| Spread a list: products of the same subcategory may take clicks from each other (`list_effects.py`) | observed / predicted for the first, second, third-or-later product of its subcategory in the list | clicks 0.99 / 1.06 / 0.95, purchases 1.02 / 0.90 / 1.01; logit +0.09 (z +1.3) and -0.07 (-0.7); reordering with a penalty on repeats never beats v9's order (reciprocal rank of the bought product 0.5590, with penalties 0.5583 to 0.5567). Products do not take from each other |
| Recency: a purchase of last week may say more than one of two months ago (`recency_check.py`) | observed / predicted by days since the shopper's last purchase in the product's subcategory | 0-7 days 0.93 / 0.96, 8-21 days 1.00 / 0.96, 22-42 days 1.00 / 1.00, 43-60 days 0.96 / 0.87; logit +0.13 (z +1.5) for the last week, -0.17 (-1.4) for the oldest: small at most |
| Co-purchase ("who bought this also bought that") | the model session's test | nothing beyond v9 for known shoppers (note of 22:05, corrected) |

Also checked: v9 is calibrated by slot (observed / predicted clicks 1.00 in slot 1, 0.93 in 2-3, 1.11 in
4-6, 0.99 in 7-10), so its order is not distorted by position.

What this says: for a given shopper and a given list the score is about as good as these signals allow.
What moves the board from here is how fast and how well the system follows the store: trends, promotions,
new products, and the organic factor, which are the arms now running.

## Update, 23:15 CET — the promotion candidate is closed, and where the gap comes from

**Promotions: a price multiplier adds nothing.** The model session ran the test on a longer table (lists
from 16:14 UTC, 38,629 lists, 904 purchases; 7.5 % of impressions on a promoted product, 60 purchases):
observed over v9's prediction is 1.05 ± 0.07 on clicks and 1.06 ± 0.14 on purchases on promotion, against
0.93 and 0.94 at catalogue price. A ratio of 1.13 where the shorter window above read 1.32: the same
direction, both inside the noise. The test that decides, where the purchased product ends up among the ten
when the score is multiplied by (price / catalogue price) ^ -e: 0.384 for v9 at e = 0, 0.8, 1.6 and 2.5;
0.406 for v9 x organic at all four. No arm for it. The calendar is now in `docs/data.md`.

So five ideas are closed with the same control: co-purchase, spreading a list, recency, waiting for the
shopper's events, a price multiplier. One was kept (new products for known shoppers, live as `v36`).

**Where our gap to the next team comes from**, by quarter-hour (UTC), conversion of the whole team against
the best of team_03, team_14, team_22 and team_42:

| Window | What the store was doing | Us | Best of the four | Gap |
|---|---|---|---|---|
| 19:25-19:40 | Game Consoles trend starts (19:30) | 2.66 | 2.53 | +0.13 |
| 19:40-19:55 | trend | 2.61 | 2.28 | +0.33 |
| 19:55-20:10 | trend | 2.70 | 2.47 | +0.23 |
| 20:10-20:25 | trend ends (20:15) | 2.11 | 2.06 | +0.05 |
| 20:25-20:40 | nothing | 2.40 | 2.39 | 0.00 |
| 20:40-20:55 | nothing | 2.21 | 2.14 | +0.07 |
| 20:55-21:10 | nothing | 2.24 | 2.22 | +0.02 |
| 21:10-21:25 | nothing | 2.20 | 2.09 | +0.11 |
| 21:25-21:40 | Face Cream trend starts (21:30) | 2.28 | 2.25 | +0.03 |
| 21:40-21:55 | trend (our organic arms flawed until 21:51) | 2.18 | 2.14 | +0.04 |
| 21:55-22:10 | trend; 100 new products at 22:00 | 2.02 | 1.95 | +0.07 |

Outside a large trend the four teams are level with us to within 0.05 on average: their rankers have
reached ours. The gap was made in the one large trend (0.13 to 0.33 for 45 minutes) and it did not open in
the small one. Two things can widen it from here, and both are already live as arms: the organic factor
(`v32` read 2.44 against 2.16 for v9 before its flaw; if that holds and it takes all the traffic, the team's
number rises by about 0.14), and whatever a large trend gives.

One thing can close it at once: answers lost. Four minutes without answering, as at 19:53 CET, cost 723
requests; in a two-hour final that is 3.3 % of the requests answered by the fallback instead of us, about
0.06 of conversion — the whole of today's gap — plus the reliability points.

## Update, 23:30 CET — a new product is not clicked in its first 20 minutes on the carousel

Read at the batch of 22:00 UTC and checked on the two earlier batches we served from their first minute
(14:00 and 18:00 UTC). New products on our carousel by time since they were added; "expected" is what any
product gets at the same slots:

| Time since added | Impressions | Clicks (expected) | Purchases (expected) | Clicks / expected | Purchases / expected |
|---|---|---|---|---|---|
| 0-10 minutes | 525 | 0 (3.2) | 0 (0.9) | 0.00 | 0.00 |
| 10-20 minutes | 663 | 1 (4.0) | 0 (1.2) | 0.25 | 0.00 |
| 20-40 minutes | 1,101 | 9 (6.8) | 3 (2.0) | 1.33 | 1.51 |
| 40-90 minutes | 3,374 | 35 (21.5) | 10 (6.4) | 1.63 | 1.56 |
| 1.5-4 hours | 15,373 | 127 (103.0) | 40 (31.2) | 1.23 | 1.28 |
| 4 hours or more | 48,703 | 536 (377.6) | 184 (119.6) | 1.42 | 1.54 |

One click on 1,188 impressions where 7.2 were expected: about one chance in 150 if these were ordinary
products, and each of the three batches says the same (0 of 79, 1 of 376, 0 of 733 impressions). Of the
1,006 lists that held such a product, 49 got a click and 9 a purchase: one click and no purchase went to it.
From the twentieth minute on, new products are what the model session measured: 1.3 to 1.6 times an
ordinary product at the same slot.

In the store it is not so: the same products are viewed, carted and bought from their first minute at the
rate they keep afterwards (about 700 views and 37 purchases per ten minutes for a batch of 100).

What it is worth: little. A just-added product takes one slot, around the middle of the list, in 11 to 23 %
of our lists (the most in `v36`, whose x1.5 pushes them) for twenty minutes every four hours: about 0.03
purchases per 100 requests during those twenty minutes. It is a free one all the same, and the final has a
batch at 10:00 UTC if the calendar holds: a product younger than twenty minutes should be left out of the
lists, and the new-product lift should start at twenty minutes. Passed on as a candidate; it is a read of
slots, not yet of v9's own prediction, and on small numbers.
