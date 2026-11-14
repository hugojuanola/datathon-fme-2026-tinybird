# 14 Nov, 16:55 CET — at the reference on the board; the attribute models' gain is on new shoppers

## How much is missing

Official board (expected purchases per 100 requests):

| Window | team_06 | Reference | Missing | Cold: us / reference | On time |
|---|---|---|---|---|---|
| Last hour (to 16:52 CET) | 2.027 | 2.063 | **0.036** (97% of the way) | 2.69 / 1.89 | 100% |
| Last 15 minutes (16:52) | 2.115 | 1.985 | **above by 0.13** | 2.91 / 1.93 | 100% |
| Last 15 minutes (16:42) | 2.135 | 2.011 | above by 0.12 | 2.69 / 1.83 | 100% |

Two consecutive 15-minute readings above the reference, and the hour is closing on it. Best rival: team_26 at
1.80. Revenue per request 1.03 € against the reference's 0.89 €.

## The A/B: attribute models (v7, then v8) against v5, same minutes (15:12–15:41 UTC)

| Shoppers | v7 + v8 | v5 (control) | Difference | In standard errors |
|---|---|---|---|---|
| Known | 1.49% (39 purchases / 2,617) | 1.33% (15 / 1,127) | +0.16 | 0.4 — none |
| New | 3.56% (38 / 1,068) | 2.63% (12 / 457) | +0.93 | 1.0 — not conclusive |
| All | 2.09% (77 / 3,685) | 1.70% (27 / 1,584) | +0.39 | 1.0 — not conclusive |

(v8 is counted to 15:51, ten minutes past the end of the control.) The attribute models are ahead, on new
shoppers; on known shoppers they are level with v5. The 2.1% that the per-impression table predicted for
known shoppers is ruled out (the upper end of the two-standard-error band is 1.96%). The control arm was
removed at 15:41 UTC, so this is the last clean comparison against v5.

## Why known shoppers did not move: the products added at the margin are weaker

Known shoppers, products not bought, purchases per impression inside each attribute-affinity band:

| Affinity band | Inside v5's lists | Inside v8's lists |
|---|---|---|
| under 1.0 | 0.023% (1 / 4,358) | 0.061% (1 / 1,632) |
| 1.0 – 1.25 | 0.059% (1 / 1,706) | 0.195% (3 / 1,542) |
| 1.25 – 1.75 | 0.296% (7 / 2,365) | **0.128%** (5 / 3,915) |
| over 1.75 | 0.213% (5 / 2,351) | **0.191%** (17 / 8,911) |

v8 shows four times as many top-band products as v5, but each sells less than the ones v5 had picked: the
effect measured at 16:12 was partly the company those products kept (v5 chose them for their subcategory,
cart and popularity as well). v8's lists are also more spread out — 6.3 distinct subcategories per list
against 5.6, and 56% of impressions in a bought subcategory against 61%. In the 16:12 table a liked attribute
sells 0.358% *inside* a bought subcategory and 0.217% outside: the lever is strongest as a way of choosing
among the products of the shopper's own subcategories, and v8 uses part of it to leave them.

Small counts throughout — one to seventeen purchases per cell — so this is a reading, not a proof.

## New arms since 15:41 UTC

`skore_money_v9` 3.39% (18 / 531; known 2.68%, new 5.06%) and `skore_money_v8c` 2.03% (11 / 543) in their
first ten minutes, next to v8 at 2.17%. Too early to rank them. In the ten minutes since 15:41 all arms
together convert known shoppers at 2.23% (31 / 1,393) and new ones at 2.93% (17 / 581).

## What to do

1. Keep what is live: the board says it is at the reference.
2. For known shoppers, keep the share of impressions in bought subcategories at v5's level (about 62%) and let
   the attribute affinity order the products *within* them; use attributes across subcategories mainly for
   new shoppers and for the session signal, where the gain showed up.
3. With no control arm left, compare the next variants against v8 over the same minutes, and keep reading
   known and new shoppers apart.

## For the final

The gain is on new shoppers and needs only the description and the request — the part most likely to carry
over. Exploration should be off (10% of traffic today).
