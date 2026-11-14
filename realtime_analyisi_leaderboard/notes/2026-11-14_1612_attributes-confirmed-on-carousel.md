# 14 Nov, 16:12 CET — the attribute lever, confirmed on the live carousel

**The lever** (found by the model session in the 60-day history): every product description names exactly 2
of 20 attributes ("organic ingredients", "luxury feel", "great value for money"…), and shoppers buy by them.
**This note** checks it where it counts — on what our carousel showed and sold — with every rate adjusted
for the slot the product was in. It holds, it is the largest effect measured so far, and it works across
subcategories and for new shoppers.

Data: all impressions we served since 13:40 CET (v4, v5, v6; exploration excluded). "Observed / expected" is
purchases divided by what the same slots sell on average, so 1.0 means "no better than its position".

## Known shoppers: affinity for the product's two attributes

Affinity = how much more often the shopper bought each of the product's two attributes than everybody does
(60-day purchases, smoothed), averaged over the two. Products not bought before, 154,370 impressions:

| Affinity | Impressions | Purchases | Purchases / impression | Observed / expected |
|---|---|---|---|---|
| under 0.8 | 43,668 (28%) | 13 | 0.030% | 0.25 |
| 0.8 – 1.0 | 24,833 (16%) | 12 | 0.048% | 0.37 |
| 1.0 – 1.25 | 23,137 | 25 | 0.108% | 0.81 |
| 1.25 – 1.75 | 33,011 | 61 | 0.185% | 1.35 |
| over 1.75 | 29,721 (19%) | 90 | **0.303%** | **2.19** |

Ten times more purchases at the top than at the bottom. The simpler version says the same: products with 0 /
1 / 2 of their attributes among the shopper's three most-bought sell 0.046% / 0.153% / **0.402%**.

It is not the subcategory effect in disguise:

| Affinity | Inside a subcategory they have bought | Outside |
|---|---|---|
| under 0.8 | 0.039% | 0.022% |
| 1.0 – 1.25 | 0.112% | 0.104% |
| over 1.75 | **0.358%** | **0.217%** |

A product from a subcategory the shopper has never bought, with the attributes they like, sells better
(0.217%) than the average product inside their own subcategories (0.176%).

**44% of what we show known shoppers today has an affinity under 1.0 and sells 0.03–0.05% per impression** —
close to nothing. That is where the room is.

## New shoppers: attributes shared with the product they just viewed

No history needed. Requests with a recent view, the viewed product itself excluded:

| Attributes shared with the last viewed product | New shoppers (55,044 impressions) | Known shoppers (126,658) |
|---|---|---|
| 0 | 0.207% (87 purchases) | 0.100% (95) |
| 1 | 0.474% (60) — 2.3× | 0.238% (72) — 2.4× |
| 2 | **1.157%** (5 of 432) — 5.6× | **0.643%** (7 of 1,088) — 6.4× |

Same result inside and outside the last view's subcategory (outside: 0.201% → 0.442% → 1.374%). Only 0.8% of
today's impressions share both attributes with the last view; there are about 27 products per attribute pair
in the catalogue, enough to fill a list.

## What it is worth

Arithmetic, with the usual warning that rates fall as a share grows. Known shoppers convert about 1.3% per
request on these impressions (0.130% per impression). If the 44% of low-affinity impressions were replaced by
products at the 1.25–1.75 level, that becomes about 2.0% — roughly **+0.45 overall**, three times the model's
gap to the reference. The session version adds to it for new shoppers, where we already lead.

## Brand history, re-checked with the slot adjustment

It survives: inside bought subcategories 0.225% against 0.086% (observed / expected 1.27 against 0.50);
outside 0.153% against 0.064%. But the model session finds that brand carries no information inside a
subcategory in the organic history, and that it added nothing to v6. The likely reading: a brand's products
tend to share attributes, so "bought this brand" was standing in for "likes these attributes". To be tested
by looking at brand inside each attribute-affinity band.

## For the final

This is the most transferable lever found so far. The attributes come from the description, which every
product has from the second it is added — including products with no sales history — and the session version
needs nothing about the shopper but the request itself.

## How it was measured

Attribute vocabulary rebuilt independently from the two unambiguous description templates (20 phrases; all
5,200 products match exactly 2). Shopper profiles from the cached 60-day purchases. One light query on the
live tables. Slot adjustment: expected purchases = sum over impressions of the average purchase rate of that
slot in the same set.
