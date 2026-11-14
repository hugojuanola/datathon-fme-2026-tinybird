# 14 Nov, 14:06 CET — the gap to the reference is on known shoppers

**Model live:** v4 (`popularity × lifts`, A/B `v4a`/`v4b`). **Leaderboard:** team_06 conversion 1.21 (best of
all teams), cold 1.79; reference 2.02 / 1.93; baseline 0.71 / 1.27.

## What the numbers say

On the requests v4 served between 12:40 and 13:07 UTC:

| Shopper | Requests | Purchases | Conversion | Reference |
|---|---|---|---|---|
| New (`is_new_user`) | 1,494 | 33 | **2.21%** | 1.93% (its cold score) |
| Known | 3,437 | 42 | **1.22%** | ≈ 2.06% (implied: overall 2.02, cold 1.93, cold ≈ 32% of requests) |

New shoppers are already at the reference's level. The whole gap is on known shoppers, who are 70% of the traffic.

Known shoppers by page: product 1.23% (1,956 requests) · category 1.79% (783) · home 0.57% (707).

## What makes a known shopper buy, measured on live carousel feedback

All our feedback up to 13:10 UTC (team-served and fallback), known shoppers, per impression.

**Products the shopper never touched in the 60-day history** (no view, cart or purchase), by the shopper's
history in that product's subcategory:

| History in the subcategory | Impressions | Purchases | Purchases / impression | vs "only viewed" |
|---|---|---|---|---|
| Bought 3+ times | 3,479 | 13 | 0.374% | **14×** |
| Bought 1–2 times | 13,685 | 20 | 0.146% | **5.6×** |
| Only viewed | 70,542 | 18 | 0.026% | 1× |
| New subcategory | 62,203 | 16 | 0.026% | 1× |

Having bought in the subcategory is the signal; having only looked at it is worth nothing. Only 11% of these
impressions were in a subcategory with purchase history.

**By what the exact product was to the shopper** (fallback-served only, so free of our own selection):

| The shown product was… | Impressions | Purchases | Purchases / impression |
|---|---|---|---|
| Already bought | 10,618 | 3 | 0.028% |
| Carted, not bought | 5,227 | 22 | 0.421% |
| Only viewed | 17,835 | 10 | 0.056% |
| Never seen | 114,010 | 48 | 0.042% |

This confirms two things v4 already does — the ×10 lift for abandoned carts and never showing a bought
product — and says a historical view alone is worth little (1.3×).

## A trap for training

Organic `shop.events` shows **no satiation**: 22.0% of the live organic purchases by known shoppers (31,610)
are of products they had already bought, the same share as in the last week of the history (22.1%). The
satiation exists only in the carousel's hidden model. Labels from the old carousel log and from organic events
both say "already bought = good"; only `team_06.feedback` says the opposite.

## What to do with it

1. Give the ranker "the shopper has bought in this subcategory, and not this product". In the learned model
   these are `u_sub_purch` and `u_sub_purch_n`; check they come out strong on the live-feedback rows.
2. If the learned ranker is not ready, a hand-set lift of about ×5 (more for 3+ purchases) in
   `reco/recommend.py` targets the same gap, including `home` pages where a known shopper has no recent views.
3. Judge every new variant separately on new and known shoppers. `tick.py` reports both.

## How it was measured

`team_06.feedback` joined to `shop.requests` (shopper, `is_new_user`), exploded with `arrayJoin(shown)`, then
left-joined to per-shopper aggregates of `shop.history_events` at product level (views, carts, purchases) and
at subcategory level (through `shop.catalog`). The subcategory query is `LEVER` in [`../tick.py`](../tick.py),
which now tracks it every tick. Counts are small where the tables say so: treat the multipliers as "large",
not as exact.
