# Three signals our lists do not use: co-purchase, co-view and "new product" (14 Nov, 23:00 CET)

**In one line**: inside the lists we served, the product that was clicked or bought is, more often than
its slot explains, (1) one that shoppers with the same purchases also bought, (2) one co-purchased with
what the shopper has just viewed, and (3) one added during the event. The ranker has no collaborative
feature at all, and it places new products too low. All three hold on clicks and on purchases, and in
slots 3-10 alone. They are the first candidates with evidence since the attributes.

Why now: four teams are within 0.05-0.13 of us and every team's ranker looks like ours (about 2.9 on cold
requests, 1.7-1.9 on warm ones). What separates teams from here is information the others do not use.

## The method

`python realtime_analyisi_leaderboard/signal_scan.py --since "2026-11-14 15:30:00"` (UTC). For every list
of ours that got a click (4,324) or a purchase (1,353): a conditional logit of which of the ten products was
chosen, on its slot and on properties of the product for that shopper. The slot terms absorb what the
ranker knew when it ordered the list; a property with a clearly positive coefficient is information the
order did not use. Staying inside a list removes the mix of requests, the trap of every per-impression
table of today. Repeated on slots 3-10 only, so the answer cannot come from the first two slots.

The collaborative property: the item-item cosine of the 60-day purchase history (548,160 purchases, 5,000
products; `C = B'B` on the shopper x product matrix, `S = C / sqrt(d_i d_j)`, two seconds to compute).
`co_hist` = sum of `S` between the candidate and the products the shopper bought; `co_view` = the same with
the products of the request's recent views. Both standardised inside each list.

## What it finds

Coefficient = log of the multiplier on the chance of being chosen, at the same slot and with the other
properties equal. `z` = coefficient over its standard error.

| Shoppers | Property | Clicks: multiplier (z) | Purchases: multiplier (z) | Slots 3-10 only, clicks / purchases |
|---|---|---|---|---|
| Known, with history | `co_hist`, one sd inside the list | x1.19 (+5.2) | x1.24 (+3.0) | x1.20 (+4.1) / x1.27 (+2.4) |
| Known, with history | `co_view`, one sd | x1.06 (+2.2) | x1.14 (+2.3) | x1.09 (+2.3) / x1.35 (+3.4) |
| New, with recent views | `co_view`, one sd | x1.22 (+5.0) | x1.28 (+3.8) | x1.28 (+4.4) / x1.45 (+3.6) |
| Known | product added during the event | x1.54 to x2.44 (+4.8 to +7.6) | x2.14 to x4.26 (+4.4 to +6.0) | x2.20 (+4.9) / x4.34 (+4.1) |
| New | product added during the event | x1.99 (+3.9) | x2.31 (+2.9) | x2.13 (+3.2) / x2.24 (+1.7) |
| Known | attribute affinity, one log unit (already a feature) | x1.28 (+3.3) | x1.57 (+2.9) | x1.26 (+2.4) / x1.93 (+2.8) |

(The two figures for new products among known shoppers are without and with the co-purchase terms in the
model; a new product has no purchase history, so its `co_hist` is zero and the second figure includes that.)

Not found: price (x0.95-0.98, nothing), popularity rank inside the subcategory (nothing once co-purchase is
in), same subcategory as the last view (nothing: the ranker uses it fully).

The plain version of the first row: in the 771 purchase lists of known shoppers, the product with the best
`co_hist` took the purchase 19.2 % of the time where its slot predicts 16.9 %.

**New products, by slot** (59,192 requests since 15:30 UTC). They are 7 to 10 % of our impressions (2 % of
the catalogue: the ranker already favours them) and still sell more than the others in the slots that count:

| Slot | Share of new products | Purchases per 1,000 impressions: new / others |
|---|---|---|
| 1 | 9.6 % | 14.1 / 9.5 |
| 2 | 9.0 % | 8.3 / 3.7 |
| 3 | 8.1 % | 2.5 / 2.1 |
| 4 | 7.9 % | 2.4 / 1.5 |
| 5 | 7.7 % | 2.0 / 1.3 |
| 6-10 | 7.2 % | level |

About 0.29 of our 2.2 purchases per 100 requests come from new products today.

## What to do with it

Two routes, the first one possible tonight.

1. **A multiplier on top of `v9`, as an arm** (no retraining, the same plumbing as the organic factor of
   `v32`): score x exp(0.2 x z(`co_hist`)) for known shoppers, x exp(0.2 x z(`co_view`)) for new ones, and
   x1.5 for a product added during the event. The exponents are the fitted coefficients, rounded down.
   An arm with 30 % of the traffic against `v9` reads to ± 0.05 by Sunday morning.
2. **Features in the next retrain**: `co_hist`, `co_view` (sum and maximum), and the co-purchase neighbours
   of the shopper's purchases and views as extra candidates for the retrieval. One trap: for rows of the old
   log, a matrix built on the whole history sees the future; build it on the weeks before, or learn these
   features from today's rows only.

New products have no row in a matrix built on the history. The organic stream gives them one within
minutes (they sell from their first ten minutes), so the matrix should take the live purchases too; until
then the "new product" multiplier covers them.

## How far to trust it

- It is a residual, not a gain: it says these products deserved a better slot, not how many purchases a
  reordered list wins. Slot 1 holds 44 % of the purchases; the gain depends on how often slot 1 changes.
  Only an arm measures it.
- The slot terms mix position and the ranker's own knowledge. The slots 3-10 runs answer that for the
  middle of the list; nothing answers it for slot 1.
- Attribute affinity, which is already a feature, also shows a positive residual. Either the ranker
  underweights it too, or part of every residual here is that the best products are better than their slot
  says. The co-purchase terms are as strong as it is and come on top of it in the same model.
- The 100 new products of today are one batch. The final brings another; the multiplier is keyed on "added
  during the event", not on these products.

## Lenses

- **Generalisation**: the matrix is keyed on product ids, so it works for the 5,000 known products and, fed
  from the stream, for new ones after their first sales. `co_view` needs no shopper history: it is a
  cold-start signal, where the ten cold-start points are.
- **Reference**: it leads every team on warm requests (2.15 against 1.7-2.0). A co-purchase recommender is
  the textbook baseline for known shoppers, and it is the one family of signal no team's numbers show.
- **Technique**: candidates from co-visitation matrices, ranked by gradient-boosted trees on interaction
  features, is the pattern of the top solutions of the two large public competitions on this problem (OTTO
  2023; H&M 2022, whose best single model was a LightGBM classifier on interaction features, as ours). The
  original is Amazon's item-to-item collaborative filtering (Linden, Smith and York, 2003).

Sources: [OTTO: co-visitation candidates and a GBDT reranker](https://towardsdatascience.com/building-a-recommender-system-using-machine-learning-2eefba9a692e) ·
[OTTO, co-visitation matrix variants](https://github.com/Fedorov-Artem/kaggle_OTTO/blob/main/README.md) ·
[OTTO, 3rd place team](https://github.com/bschifferer/Kaggle-Otto-Comp) ·
[H&M 1st place, summary](https://goldandrabbit.github.io/2022/05/15/H&M%20Recommendation%20Competition%20Top1%20%E6%96%B9%E6%A1%88) ·
[H&M winners used LightGBM and CatBoost rankers](https://arxiv.org/pdf/2310.03778v1.pdf)
