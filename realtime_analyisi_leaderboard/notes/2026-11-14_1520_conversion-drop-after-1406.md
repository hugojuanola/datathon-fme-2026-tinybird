# 14 Nov, 15:20 CET — v5 converts half as much since 14:06 UTC, and the lists did not change

**What we see.** Since the server instance that started at 14:06:31 UTC, `skore_money_v5` converts 1.22% of
the requests it serves; in the 32 minutes before it converted 2.35%. Same model version, same kind of lists.

| Period (UTC) | Requests served by v5 | Purchases | Conversion | Clicks → purchases |
|---|---|---|---|---|
| A · 13:34–13:57 (A/B against v4) | 2,058 | 49 | 2.38% | — |
| B · 13:57–14:06 (v5 + exploration, first instance) | 1,047 | 24 | 2.29% | — |
| A + B | 3,105 | 73 | 2.35% | 174 clicks → 73 (42%) |
| **C · 14:06–14:16 (instance from the new environment)** | 1,473 | 18 | **1.22%** | 88 clicks → 22 (25%) |

A against C is 2.6 standard errors apart. Per six minutes, all arms: 2.40, 1.95, 2.04, 1.71, 1.88, then **1.15
and 1.08**. If the true rate were still 2%, 20 purchases or fewer in those 1,790 requests would happen about
3 times in 1,000. It is probably real, but it rests on 18 purchases: the next two ticks will settle it.

**Where it is.** Known shoppers click about as often as before (5.0% against 5.6%) but buy far less of what
they click: 9 purchases from 61 clicks (15%) against 42 from 117 (36%). On product pages they went from
2.22% (19 / 857) to 0.67% (4 / 596). New shoppers: 3.5% → 2.1%, on few purchases.

## What it is not — each one checked

| Suspect | Check | Result |
|---|---|---|
| The lists changed | Composition of v5's lists per period ([`list_composition_by_period.sql`](../queries/list_composition_by_period.sql)): in `recent_views`, same category / subcategory as the last view, new products, carted live, viewed live, bought live | Unchanged: 2.2–2.4% / 39–43% / 12–15% / 3% / 3–4% / 7% / 0% |
| The order changed | Clicks by slot | Same shape: slot 1 takes 38% of the clicks before and 33% after |
| The top of the list changed | Price, popularity, rank inside the subcategory of slots 1, 1–3 and 1–10; most frequent slot-1 products | Unchanged (median price 17 €, same six products on top) |
| Lists sent to the wrong shopper | The session-relative shares above would collapse | They did not |
| Two different answers per request | `team_06.submissions` | 8 of 2,013 requests answered twice, always with the same list |
| Different shoppers arriving | Known shoppers by period: mean past purchases 25.3–25.5, 34% with 20+, 20% on `home`; 30% new shoppers | Unchanged |
| The store went quiet | Organic stream per 10 minutes | Unchanged: 34.5 k views, 5.1–5.3 purchases per 100 views |
| Slow answers convert less | Period B had the same latency (p50 1.5 s) and converted 2.29% | Not latency |
| A price change | `shop.catalog_updates` | None since 12:30 UTC |

## What is left

1. **Chance** — unlikely (about 0.3%) but not excluded with 18 purchases.
2. **Something in the instance started at 14:06:31** that these checks do not see: the model file or the
   features it receives (the shopper-side ones — purchase shares per subcategory, usual price — would not show
   in list composition if the candidates are the same but their scores for *this* shopper are not).
3. **The store moved at 14:00 UTC**: a second batch of 100 products arrived, and one subcategory is trending
   (Cutting Boards went from 0.73% to 2.51% of organic purchases, ×3.4). Too small to explain a halving, but
   the hidden model may have changed more than the organic stream shows.

**The quickest way to tell 2 from 3**: serve a small share of traffic from the previous build (the one that
ran 13:57–14:06) side by side with the current one. If the old build still converts ≈2.3% while the new one
stays at ≈1.2%, it is the instance; if both are low, the store changed and the model needs the live signal.

## Reliability, same period

5.5% of requests unanswered since 14:06 (95 of 1,727), p95 2.6 s, and the leaderboard's `on_time` fell to
91.4%. OneDrive is closed, yet the laptop still uploads 113–124 KB/s: the processes sending now are the
browser (Opera) and Discord. The uplink is as full as before.

## A second finding on the way: repeat visits convert half as much

Known shoppers, requests we served since 12:40 UTC, by how many requests the same shopper had already made:

| Request of the shopper | Requests | Purchases | Conversion |
|---|---|---|---|
| First | 9,544 | 122 | 1.28% |
| Second | 1,761 | 12 | 0.68% |
| Third or fourth | 566 | 5 | 0.88% |
| Fifth or later | 105 | 0 | 0.00% |

One in five requests is a repeat visit, and the share grows as a round goes on. We show a returning shopper
much the same list they already ignored. Discounting products that were shown and not clicked ("impression
discounting") is the standard answer; here it is worth at most about 0.1 points overall, so it comes after
the two problems above.
