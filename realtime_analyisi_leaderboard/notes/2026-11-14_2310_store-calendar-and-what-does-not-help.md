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
