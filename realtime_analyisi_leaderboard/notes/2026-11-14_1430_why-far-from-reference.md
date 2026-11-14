# 14 Nov, 14:30 CET — why we are far from the reference

**Short answer.** We build the list around the *session* (what the shopper just looked at). That is enough for
new shoppers, where we match the reference. Known shoppers buy according to their *purchase history*, which
v4 ignores apart from abandoned carts — and known shoppers are 68% of the traffic and all of the gap.

## 1 · The gap, decomposed

Leaderboard at 14:21 CET: us 1.378 overall / 1.855 cold; reference 2.038 / 1.880. Cold requests are ≈32% of
the traffic (30% new shoppers + 2% known shoppers who viewed a new product), which implies:

| | Cold (32%) | Not cold (68%) | Overall |
|---|---|---|---|
| Reference | 1.88 | ≈ 2.11 | 2.04 |
| team_06 (v4) | 1.86 | ≈ 1.15 | 1.38 |
| Contribution to the gap | 0.01 | **0.65** | 0.66 |

Our own feedback agrees: in the last 30 minutes v4 converted new shoppers at 1.62% and known shoppers at 1.02%.

## 2 · What known shoppers want — two independent measurements

**a) The shopper's next organic purchase.** For every organic purchase (`shop.events`) made within 30 minutes
after a request we served, we looked at the purchased product
([`next_purchase_recall.sql`](../queries/next_purchase_recall.sql)). Known shoppers, products they had not
bought before (655 purchases):

| The purchased product was… | Share |
|---|---|
| in our 10 | 8.7% |
| in a subcategory where the shopper has bought before | **63.4%** |
| in the same category as the last viewed product | 21.5% |
| in the same subcategory as the last viewed product | 5.0% |
| carted in the history | 15.9% |
| in `recent_views` | 0.2% |
| none of the above | 28.4% |

A known shopper has bought in 10.5 of the 89 subcategories on average, so chance would put 12% of purchases
there; the data puts 62–63% (5×). The category of the last view — the main lift in v4 (×5) — explains 21.5%.

Where inside the history ([`next_purchase_where.sql`](../queries/next_purchase_where.sql), 1,666 purchases):
13% fall in the shopper's most-bought subcategory, 29% in the top 3, 38% in the top 5, 51% in the top 10. By
popularity inside the subcategory, 28% are a top-3 product, 55% a top-10, 75% a top-20.

**b) The carousel's own feedback, per impression** ([14:06 note](2026-11-14_1406_known-shoppers-gap.md)):
products never touched by the shopper sell at 0.374% per impression in a subcategory with 3+ past purchases,
0.146% with 1–2, and 0.026% everywhere else.

Both say the same thing from different data: organic behaviour and the hidden carousel model.

## 3 · How much is there to win

In the last 30 minutes, 34% of the impressions we gave known shoppers were in a purchase-history subcategory,
selling at 0.182% per impression; the other 66% sold at 0.064%. That reproduces what we measure:
10 × (0.34 × 0.182 + 0.66 × 0.064) = 1.04% per request (measured: 1.02%).

| Share of known-shopper impressions in purchase-history subcategories | Known-shopper conversion | Overall (cold stays at 1.86) |
|---|---|---|
| 34% (today) | 1.04% | 1.30 |
| 60% | 1.35% | 1.51 |
| 80% | 1.58% | 1.67 |
| 80%, concentrated on 3+ purchase subcategories (≈0.25% per impression) | ≈ 2.1% | ≈ 2.0 |

This is arithmetic, not a forecast: it assumes the per-impression rates hold as the share grows (they will
drop as we reach less popular products) and that slots add up (a request has one click, so they do not fully).
It says the lever is big enough to explain the reference, not that we will land exactly there.

## 4 · Why the learned ranker may not find this on its own

- In the old carousel log every product shown on a product or category page was in the category of the last
  view. The log contains no example of a purchase-history product from another category, so a model trained
  on it cannot learn how the two signals trade off.
- The log has no satiation and rewards re-buying; the live carousel does not.
- Our live feedback so far is best sellers (fallback) and v1–v4, all session-centred.

So the evidence for this lever exists only in the 34% of impressions that happened to land there. **The
fastest way to get more is to show them on purpose.**

## 5 · Proposed experiment

One A/B arm on top of v4, half the traffic, known shoppers only:

    score ×= 1 + k · log(1 + purchases of this shopper in the product's subcategory)     (k ≈ 3)

keeping the block on already-bought products and every existing lift. It moves known-shopper impressions
towards purchase-history subcategories without removing the session signal. Read it with
`python realtime_analyisi_leaderboard/tick.py`: the arm should show a higher `lever_impr_share_pct` and, if the
analysis is right, a higher `known_conv_pct`; `new_conv_pct` must not move. With ≈1,800 known requests per
arm per 30 minutes, a jump from 1.0% to 1.5% is visible in about one hour.

## 6 · Does it generalise to the final?

Yes, in the form that matters: with live-only history the same lever gives 5.8× for new shoppers and 3.5×
for known ones, and the live stream alone gives a purchase history to 28% of requests by the second hour
([14:25 note](2026-11-14_1425_generalisation-reference-techniques.md)). The feature must therefore count
purchases from `shop.events` as they happen, not only from the 60 days.

## Caveats

- Organic purchases are not carousel purchases: 35% of them are re-purchases the carousel would not sell.
  They were removed from the table in section 2a, but the organic stream is a proxy for intent, not the target.
- The reference's split between cold and not-cold is implied from two published numbers and our 32% estimate.
- Counts are in the hundreds to low thousands; the direction is solid, the second decimal is not.
