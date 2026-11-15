# Data dictionary and measured profile

All data lives in RawTree. Our key can **read** the shared `shop` database and **read/write** `team_06`.
Schemas below are the official ones; the "Measured" notes were obtained by querying the live data on
**Sat 14 Nov 2026 ≈ 11:20 UTC** (≈ 2 h 20 min into the practice round). Live numbers drift: re-run the
query before relying on one. Every query in this file runs as-is with `python3 scripts/rt.py "<sql>"`.

## Things that will bite you (read first)

- **Every column is `Dynamic`.** Filters and most functions work directly; **JOIN keys, `argMax`/`argMin`,
  `GROUP BY` identity and many aggregates need a cast**: `product_id::String`, `ts::DateTime64(3)`,
  `price_eur::Float64`, `is_active::Bool`. Without it you get `Illegal type Dynamic` or silently skipped rows.
- **Timestamps are UTC**, stored as `DateTime64(9)` and returned as `"2026-11-14 11:20:42.025000000"`
  (space separator, 9 decimals, no `T`/`Z`) — not the ISO format shown in the brief's samples.
  Barcelona time is UTC+1.
- **`context` is stored as three sub-paths** `context.device`, `context.page`, `context.region`.
  `SELECT *` returns flat keys named `"context.device"` etc.; `SELECT context` returns the nested object.
- **`recent_views` is an array of objects** `{product_id, ts}`, oldest first. It is `[]` on every `home`
  request. Access with `recent_views[-1].product_id::String`; explode with `arrayJoin`.
- **Null conventions differ**: in `shop.history_sessions`, `clicked` / `purchased` are `NULL` when nothing
  happened; in `team_06.feedback` they are the empty string `''`.
- **`team_06.feedback` and `team_06.submissions` start with a placeholder row** `request_id = '__init__'`: filter it out.
- **Unknown path → `UNKNOWN_IDENTIFIER`** (e.g. a table that has no rows yet, like `team_06.scratch`).
- `SHOW TABLES` is not accepted by the Query API; use `SELECT name, total_rows FROM system.tables WHERE database IN ('shop','team_06')`.

## Tables at a glance

| Table | Rows (measured) | Kind | Purpose |
|---|---|---|---|
| `shop.catalog` | 5,000 | static | Product catalogue at the start of the stream |
| `shop.history_sessions` | 2,000,000 | static | 60 days of carousel impressions from the old system, with propensities |
| `shop.history_events` | 11,996,560 | static | 60 days of organic activity outside the carousel |
| `shop.requests` | ~3 / s | live, append-only | **What we answer** |
| `shop.events` | ~67 / s | live, append-only | Organic activity in real time (same shape as `history_events`) |
| `shop.catalog_updates` | few / 5 min | live, append-only | New products, price changes, stock changes |
| `team_06.submissions` | ours | write | Our answers |
| `team_06.feedback` | ours | read | Outcome of every request, written ≈4.2 s after the request `ts` |
| `team_06.scratch` | empty | read/write | Free table for our own features / embeddings / model outputs |

## `shop.catalog`

| Field | Type | Notes |
|---|---|---|
| `product_id` | String | Opaque, `p_` + 6 hex chars |
| `category` | String | 10 values |
| `subcategory` | String | 89 distinct in the initial catalogue (brief says 90) |
| `brand` | String | 80 distinct; 8 per category |
| `price_eur` | Float64 | Price at the start. Changes arrive in `shop.catalog_updates` |
| `description` | String | One or two sentences, templated: brand, subcategory, a couple of attributes |
| `created_at` | DateTime64 | 2024-05-29 → 2026-09-15 |
| `is_active` | Bool | All `true` in the initial catalogue |

Measured:

| Category | Products | Avg price € | Min | Max |
|---|---|---|---|---|
| Home & Garden | 640 | 44.48 | 6.99 | 237.99 |
| Pets | 613 | 39.63 | 3.99 | 280.99 |
| Electronics | 580 | 42.31 | 2.99 | 485.99 |
| Books & Media | 553 | 57.67 | 1.99 | 629.99 |
| Toys & Baby | 516 | 46.77 | 4.99 | 354.99 |
| Sports & Outdoors | 489 | 35.24 | 2.99 | 399.99 |
| Home & Kitchen | 466 | 62.25 | 1.99 | 481.99 |
| Computers & Gaming | 427 | 40.53 | 3.99 | 257.99 |
| Fashion | 394 | 62.39 | 1.99 | 405.99 |
| Beauty & Health | 322 | 44.98 | 2.99 | 643.99 |

Price quantiles (p10 / p50 / p90 / p99): 9.99 / 30.99 / 96.99 / 282 €. Each category has 8–9 subcategories.

**Current catalogue** = `shop.catalog` with the latest `shop.catalog_updates` record of each product on top
(query 1 in [`starter/queries.sql`](../starter/queries.sql)).

## `shop.history_sessions` — the old carousel's log (biased)

| Field | Type | Notes |
|---|---|---|
| `request_id` | String | |
| `ts` | DateTime64 | 2026-09-15 07:00 → 2026-11-14 07:00 UTC |
| `user_id` | String | 59,698 distinct |
| `context.device` / `.region` / `.page` | String | device: `web`, `ios`, `android`; page: `home`, `product`, `category`; 10 regions |
| `recent_views` | Array of `{product_id, ts}` | 0–6 items, oldest first |
| `shown` | Array(String) | The 10 products the old system showed, in order |
| `propensity` | Array(Float64) | Probability the old system had of showing each product in that slot, given the slots above |
| `clicked` | String or NULL | |
| `purchased` | String or NULL | |
| `revenue_eur` | Float64 | 0 when no purchase |

The old system is "best sellers plus a bit of randomness", so the log is **biased towards popular products**;
`propensity` allows inverse-propensity correction (see [`starter/offline_eval.ipynb`](../starter/offline_eval.ipynb)).

Measured:

- Overall: **CTR 3.75%**, **conversion 1.40%**, revenue 0.491 €/request.
  37.4% of clicks end in a purchase, and `purchased` always equals `clicked` (a shopper buys only what they clicked).
- By page — the page is a very strong signal:

  | page | share | CTR % | conversion % |
  |---|---|---|---|
  | product | 56% | 4.48 | 1.72 |
  | category | 24% | 4.49 | 1.71 |
  | home | 20% | 0.79 | 0.14 |

  `home` impressions always have `recent_views = []`.
- By device: android 1.57% · web 1.38% · ios 1.25% conversion.
- By region (conversion %): Murcia 2.13 · Andalucía 1.86 · Canarias 1.76 · Catalunya 1.24 · Madrid 1.24 ·
  Comunitat Valenciana 1.23 · Galicia 1.19 · País Vasco 1.18 · Castilla y León 1.17 · Aragón 0.97.
- By `length(recent_views)` (conversion %): 0 → 0.14 · 1 → 2.06 · 2 → 1.68 · 3 → 1.53 · 4 → 1.49 · 5 → 1.45 · 6 → 1.39.
- **Position bias** (clicks per slot 1→10): 21483, 12015, 8805, 6836, 5629, 5043, 4438, 3923, 3483, 3260.
  Slot 1 gets 6.6× the clicks of slot 10.
- When there is a recent view, **every click in the log is on a product of the same category as the last
  product viewed** (71,769 of 71,769). The old system only showed same-category products in that case, so this
  is a property of what was *shown*, not proof that shoppers never buy across categories.
- Propensities are per-slot conditionals; some are 0 or tiny (≈7e-5), so clip weights when doing IPS.

## `shop.history_events` — organic activity (not from the carousel)

| Field | Type | Notes |
|---|---|---|
| `ts` | DateTime64 | 2026-09-15 07:00 → 2026-11-14 07:08 UTC |
| `event_type` | String | `view`, `add_to_cart`, `purchase` |
| `user_id`, `session_id` | String | |
| `product_id` | String | |
| `price_eur` | Float64 | Price at the time of the event |
| `device`, `region` | String | |

Measured:

| event_type | Rows | Users | Sessions | Products |
|---|---|---|---|---|
| view | 10,354,047 | 59,841 | 2,500,000 | 5,000 |
| add_to_cart | 1,094,353 | 55,956 | 805,858 | 4,906 |
| purchase | 548,160 | 51,799 | 464,465 | 4,809 |

Top all-time sellers (this *is* the baseline/fallback ranking, ties broken by higher `product_id`):
`p_adc3e6` 6260 · `p_69d40e` 5357 · `p_0210c5` 4649 · `p_09a938` 4060 · `p_1036d3` 3769 · `p_e2454f` 3348 ·
`p_5969fa` 3199 · `p_2c88d5` 3162 · `p_8ca8ed` 3142 · `p_55ab57` 2532 · `p_050730` 2457 · `p_5733ef` 2366.

## `shop.requests` — live, what we answer

```json
{"request_id": "r_0a3716288ea73eae", "ts": "2026-11-14 11:20:42.025000000", "user_id": "u_db5b5661",
 "is_new_user": true,
 "context": {"device": "android", "region": "Comunitat Valenciana", "page": "product"},
 "recent_views": [{"product_id": "p_c2b258", "ts": "2026-11-14 11:17:41.944000000"}, "..."]}
```

Measured (practice round):

- Stream opened at **2026-11-14 09:00:00 UTC** (10:00 CET). Rate: **3.0 requests/s**.
- A new request becomes queryable **≈250–400 ms after its `ts`**; the clock is the server's UTC `now64(3)`.
- **30% of requests have `is_new_user = true`**; 70% of requests come from a `user_id` present in `shop.history_events`.
- Page mix: product 57% · category 24% · home 20%. `home` → `recent_views = []` (always cold on context).
- `length(recent_views)` distribution: 0 → 20% · 1 → 26% · 2 → 20% · 3 → 15% · 4 → 10% · 5 → 6% · 6 → 4%.

## `shop.events` — live organic activity

Same shape as `shop.history_events`. Measured rates: **view 57.5/s · add_to_cart 6.1/s · purchase 3.0/s**
(≈67 events/s total). Covers 5,100 products: the 5,000 originals plus the 100 added during the event.
Newest event is ≈400 ms behind server time.

## `shop.catalog_updates` — live catalogue changes

One record per change: the **full product after the change** plus `ts` and `change`.

| `change` | Measured so far | Pattern |
|---|---|---|
| `out_of_stock` | 87 | **Every 5 minutes on the dot**, 3 products go out |
| `back_in_stock` | 51 | Every 5 minutes, 3 products come back (from 10:00 UTC) |
| `new_product` | 400 | **100 every 4 hours**: 10:00, 14:00, 18:00, 22:00 UTC (the first one 1 h after the stream opened) |
| `price_change` | 4,596 | **A promotion every 3 hours**: at 10:30, 13:30, 16:30, 19:30 UTC 500–665 products drop ≈17–20 %, and two hours later (12:30, 15:30, 18:30, 21:30) the same number go back to the catalogue price; mostly different products each time |

≈36 products are out of stock at any moment. Out-of-stock test (from the starter): latest of
`out_of_stock` / `back_in_stock` per product is `out_of_stock`. Expect the final round to bring its own
new products, price changes and trends.

**The store runs on a calendar** (measured 14 Nov, 09:00–22:07 UTC, on `shop.catalog_updates` and the
stream). Trends: one subcategory for 45 minutes from :30 of the odd UTC hours (09:30, 11:30, 13:30, 15:30,
19:30, 21:30; none seen at 17:30). Promotions: every 3 hours from 10:30, for 2 hours. New products: every
4 hours from 10:00. If it keeps running, the final (09:00–11:00 UTC) holds the 07:30 promotion until 09:30,
a trend 09:30–10:15, 100 new products at 10:00 and a promotion from 10:30: a trend for 45 of its 120
minutes, a promotion for 60, a fresh batch of products for the last hour. We use it to read the arms by
regime, never as a rule in the recommender: the subcategories and products of the final are new.

## `team_06.submissions` — what we write

```json
{"request_id": "r_...", "items": ["p_...", "(10 ids)"], "model_version": "v1-something"}
```

`POST https://api.rawtree.com/v1/tables/submissions?database=team_06` with a JSON array body.

## `team_06.feedback` — what happened

```json
{"request_id": "r_a25c18dbe974c786", "ts": "2026-11-14 11:20:43.260000000",
 "shown": ["p_0210c5", "p_09a938", "..."], "served_by": "fallback", "fallback_reason": "missing",
 "latency_ms": null, "clicked": "", "purchased": "", "revenue_eur": 0}
```

| Field | Notes |
|---|---|
| `shown` | The 10 products the shopper actually saw (ours, or the fallback's) |
| `served_by` | `team` or `fallback` |
| `fallback_reason` | `''`, `missing`, `late`, `invalid` |
| `latency_ms` | Our answer's latency from the request `ts`; `null` when missing |
| `clicked`, `purchased` | Product ID or `''` |
| `revenue_eur` | 0 when no purchase |

Measured: feedback is written **≈4.23 s after the request `ts`** (p95 4.25 s). Our feedback starts at
10:20:49 UTC (when the key was issued) and, until our system is started, every row is `fallback / missing`.
That gives a free measurement of the baseline on live traffic: **CTR 2.36%, realised conversion 0.82%,
0.147 €/request** over 10,890 requests.

The feedback row's own `ts` is that write time, not the request's: a minute of feedback holds the requests
of 4.2 s earlier (measured again on 15 Nov: 4,202–4,251 ms on 90 requests). Join on `request_id`, or shift,
when lining feedback up with a log. How late an answer may land (measured 15 Nov): since 14 Nov 20:00 UTC,
86 of our 83,231 answers that were used had `latency_ms` above 3,000 (17 above 3,300, the latest 3,459),
and no row of ours says `late`, only `missing`. The brief says the 3 seconds are "measured by the
organisers' clock (polled every half second)", which fits answers being taken up to about 3.5 s. We stop
answering a request 2.8 s after its ts (`MAX_AGE_MS` in `reco/serve.py`), so where `late` begins was never
reached, and whether an answer between 3,000 and 3,459 ms counts as on time for the reliability score is
not known: nothing to lean on.

## Public leaderboard numbers (practice, last hour, same moment)

| | Conversion (exp. purchases / 100 req) | Cold conversion | € / request |
|---|---|---|---|
| baseline | 0.717 | 1.327 | 0.118 |
| organisers' reference | **2.243** | 2.222 | 1.147 |

The reference converts ~3.1× the baseline and earns ~10× the revenue per request, so it recommends much
more relevant *and* more expensive products than the global best sellers. The oracle is not published.
Leaderboard conversion counts all requests, including the ones the fallback served. Get the live table
with `python3 scripts/leaderboard.py`.
