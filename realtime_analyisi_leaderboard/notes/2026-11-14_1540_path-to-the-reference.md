# 14 Nov, 15:40 CET (revised 15:50) — the path to the reference, point by point

**Where we are.** Leaderboard at 15:37 CET: team_06 1.53 (rank 2 — team_19 passed us with 1.54), reference
2.10, baseline 0.73. The gap is 0.57 points. On the requests it actually serves, `skore_money_v5` converts
**1.94%** (142 purchases in 7,328 requests since 14:34 CET) and earns 1.03 € per request, more than the
reference's 0.94 €. So most of the gap on the board is not the model.

## The budget

| Where the points go | Size today | How it is measured |
|---|---|---|
| Requests we do not answer | **≈ 0.12** | 8.3% unanswered since 15:06 CET (460 of 5,546); a fallback request converts 0.42% (4 / 947) instead of 1.94% |
| The exploration arm | **≈ 0.22** | 20% of the traffic at 0.83% (11 / 1,323) instead of 1.94%. Deliberate, practice only |
| The model itself, against the reference | ≈ 0.16 | 2.10 − 1.94, with v5 known only to about ±0.3 |
| The rest | ≈ 0.07 | the hour on the board still holds 20 minutes of v4, and realised vs expected purchases |

With every request answered and no exploration, today's model would sit at about 1.9 — within reach of the
reference, not yet at it.

About the drop reported at 15:20: it eased. Per six minutes since 15:06 CET: 1.15, 1.13, 1.40, 1.56, 1.93,
1.47. v5 since 15:06 is at 1.60% (65 / 4,063), still 2.2 standard errors under the 2.35% of 14:34–15:06, so
the earlier stretch was probably a lucky one and the truth is near the 1.94% average.

## Where the model still loses: known shoppers

v5 converts new shoppers at 2.78% (61 / 2,193) — well above the reference's cold 1.96 — and known shoppers at
1.58% (81 / 5,135), against about 2.17 implied for the reference.

## The new lever: the brands a shopper has already bought

Known shoppers, every impression we served since 13:40 CET (v4 and v5, exploration excluded), products the
shopper had not bought — 133,800 impressions:

| The product is… | Impressions | Purchases | Purchases / impression |
|---|---|---|---|
| in a subcategory **and** of a brand the shopper has bought | 39,033 | 83 | **0.213%** |
| of a brand the shopper has bought, in a new subcategory | 13,456 | 22 | **0.163%** |
| in a subcategory the shopper has bought, of a new brand | 21,146 | 21 | 0.099% |
| neither | 60,165 | 40 | 0.066% |

A brand the shopper has bought before multiplies purchases by 2.2 inside their subcategories and by 2.5
outside them. **The model has no such feature**: `reco/features.py` knows the brand of the last viewed product
(`same_brand`) and the shopper's history per subcategory and category, but not per brand.

What it is worth, by the same arithmetic as before: today 65% of the impressions inside purchase-history
subcategories and 18% outside them are of a bought brand. Moving those to 90% and 60% would take known
shoppers from about 1.4% to about 1.7% per request — roughly **+0.2 overall**, the size of the model gap.

It should generalise: a brand purchase can be counted from the live stream the moment it happens, like the
subcategory purchases, so it exists for a shopper first seen in the final.

## What does not matter (so nobody spends time on it)

Same 133,800 impressions, inside purchase-history subcategories:

- **How recent the last purchase in the subcategory was**: 0.18% (0–3 days), 0.16%, 0.21%, 0.18%, 0.14% (31–60 days). Flat.
- **The product's price against what the shopper usually pays in that subcategory**: 0.14–0.21% across the range. Flat.
- **How popular the product is inside its subcategory**: top-1 0.18%, ranks 2–3 0.13%, 4–10 0.21%, 11+ 0.16%. Flat —
  for a known shopper the best seller of the subcategory is no better than its tenth product.
- **How many times they bought in the subcategory** does matter, as already known: 0.10% with one purchase, 0.27–0.29% with five or more.

## Two ideas from the first version of this note, checked and withdrawn

- **The `home` page.** It converts 0.56% for known shoppers against 1.7–2.1% on the other pages, and I
  suggested the lists there were generic. They are not: on `home` v5 already puts 62% of the impressions in
  purchase-history subcategories (60% on product pages) and the same share of best sellers (23%). The page
  itself converts less — it did in the 60-day log too (0.14% against 1.7%). No easy points there.
- **Impression discounting for repeat visits.** A returning shopper gets a list that repeats 6.9 of 10
  products, and repeat requests convert less (1.61% against 1.93% for first requests under v5). But on those
  requests the repeated products sell *more* than the fresh ones — 0.192% per impression (9 / 4,687) against
  0.094% (2 / 2,133), and 0.114% against 0.049% even when the previous list got no click. Repetition is not
  what costs the purchases; discounting repeated products would remove the better half of the list.

## What to do, in order

1. **Answer every request** (+0.12, and the 10 reliability points of the final). The instance started at
   15:35 CET with hedged requests is clean so far, and the laptop's upload fell from 100–130 KB/s to 20 KB/s
   once the call, the browser and OneDrive were closed.
2. **No exploration arm in the final** (+0.22 against today's board). Keep it now: it is what makes the next
   model trainable and testable.
3. **Add the shopper's brand history to the model** (≈ +0.2): purchases per brand in the shopper state, a
   share and a count as features, and a retrieval lift for brands bought, as was done for subcategories.
4. Shoppers with a medium history (10–19 purchases: 1.36% with v5, the same as with the rules): the brand
   feature is the first thing to try for them too, since it is defined after a single purchase.

## How it was measured

Light queries joining `shop.requests`, `team_06.feedback` and `team_06.submissions`, joined locally to the
cached 60-day purchases per shopper (subcategory, brand, price, date). Purchases are realised ones; the
leaderboard counts expected purchases, which agree on average. Not controlled for: a shopper with more
purchases has bought more brands, so part of the brand effect may be the purchase-count effect — the model
will separate them once the feature exists.
