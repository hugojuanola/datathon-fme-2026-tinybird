# Findings — what drives a purchase in this store

Measured on Sat 14 Nov 2026, 12:00–12:30 UTC. Each number comes from a query that can be re-run
(`python scripts/rt.py "<sql>"`); the per-impression tables explode `shown` with
`arrayJoin(arrayZip(shown::Array(String), range(1, 11)))`.

## 1. The shopper's own signals dwarf everything else

Purchase rate **per product shown** in `shop.history_sessions` (last 7 days of the log, user history
taken only from `shop.history_events` *before* those 7 days, so there is no leakage):

| The shown product is… | not in `recent_views` | in `recent_views` |
|---|---|---|
| never touched by this shopper | 0.038 % | 0.37 % |
| viewed before (organic history) | 0.032 % | 0.20 % |
| carted before, never bought | 0.54 % | 2.04 % |
| bought before | 1.23 % | 7.51 % |

- A product the shopper **just viewed in this session** converts ~10× better than an unrelated one;
  in slot 1 it reaches 6.3 % (vs 0.45 % for an average slot-1 product).
- A product the shopper **carted but did not buy** converts ~14× better.
- A plain historical *view* carries no signal at all.

## 2. The live simulator has satiation; the historical log does not

Same table on **live** traffic (our fallback feedback: global best sellers shown to 19 k requests):

| The shown product is… | purchases / impressions | rate |
|---|---|---|
| never touched | 42 / 114,153 | 0.037 % |
| carted before, never bought | 20 / 5,259 | 0.38 % |
| **bought before** | **1 / 10,497** | **0.01 %** |
| in `recent_views`, known shopper | 4 / 173 | 2.3 % |
| in `recent_views`, new shopper | 7 / 167 | 4.2 % |

In the log a previous purchase is the best predictor of a new one; live it is the worst. The brief
warns about it ("a shopper who already bought a product tends not to want it again") and the data
confirms it is strong. **Consequence: never recommend something the shopper already bought**, and a
model trained naively on the log would recommend exactly those products. Carousel purchases do not
appear in `shop.events` (1 match out of 159), so our own sales must be tracked from `team_06.feedback`.

## 3. New shoppers are not blind

Under the baseline, new shoppers convert *better* (1.3–1.4 %) than known ones (0.63 %): known shoppers
have already bought the best sellers. And "new" only means "absent from the history": 90 % of the
requests of new shoppers are preceded by live events of that shopper in `shop.events` (carts and
purchases included), so the live stream is their history.

## 4. Context

- Position bias is steep: slot 1 gets ~6× the clicks of slot 10, for every kind of product.
- `home` requests carry no `recent_views`; there, only the shopper's own carted products convert
  meaningfully (0.22 % vs 0.003 % for an untouched product).
- In the log every product shown on a `product`/`category` page is from the category of the last
  view, so the log says nothing about cross-category recommendations: that needs live exploration.
- Same subcategory as the last view: 1.4× over same category only (0.21 % vs 0.13 %).

## 5. The product's own popularity multiplies everything (lesson from v1)

v1 ranked by tier: just viewed > carted > popular fill. Live, over 758 requests, it converted 0.66 %,
no better than the baseline: an obscure product does not sell because it was viewed (0.9 % CTR for
v1's viewed products vs 3.8 % for *best sellers* that had been viewed). The signals are lifts on top of
how attractive the product already is, so the policy became `score = popularity × lifts`.

Live purchase rate per impression of the global best sellers (fallback feedback, products the shopper
had not bought and had not just viewed):

| | not carted | carted, never bought |
|---|---|---|
| other category than the last view | 0.052 % | 0.53 % |
| same category as the last view | 0.267 % | 0.58 % |
| home (no last view) | 0.019 % | 0.18 % |

Category is a ×5 lift; an abandoned cart is ×10 outside the session's category and ×2 inside it.

## 6. Offline validation (`python -m offline.evaluate`)

Held-out last 7 days of the log, policy state built only from earlier events, same code as live.
Test set: 5,294 clicks / 1,351 purchases of products the shopper had not bought before.

| Policy | click hit@10 | click, slot-weighted | purchase hit@10 | purchase, slot-weighted |
|---|---|---|---|---|
| baseline (best sellers) | 30.0 % | 13.3 % | 39.6 % | 19.5 % |
| popularity, minus already bought | 31.7 % | 14.1 % | 42.1 % | 20.7 % |
| + category of the last view (×5) | 67.8 % | 39.4 % | 78.8 % | 48.5 % |
| + subcategory (×1.4) | 68.8 % | 40.4 % | 79.9 % | 49.7 % |
| + abandoned carts | 66.0 % | 35.8 % | 77.8 % | 47.0 % |
| + just viewed ×2 | 66.2 % | 36.2 % | 78.2 % | 47.8 % |
| + just viewed ×3 | 66.0 % | 35.9 % | 77.9 % | 47.3 % |
| + just viewed ×10 | 65.0 % | 32.6 % | 76.9 % | 42.5 % |
| + just viewed ×30 | 64.1 % | 28.8 % | 76.3 % | 37.3 % |

- Category of the last view is the big step: purchases found in our top 10 go from 40 % to 79 %.
- The log **cannot** credit a cross-category recommendation (the old system never showed one), so the
  abandoned-cart lift looks slightly negative offline. Live it is a ×10 effect (table above), which is
  why it is kept: where the log is blind, live feedback decides.
- "Just viewed" is best at ×2–3 and clearly harmful at ×10–30. The live A/B agreed within minutes:

| Live variant | Requests | CTR | Conversion |
|---|---|---|---|
| baseline (starter kit, 11:33–11:41 UTC) | 1,395 | 2.44 % | 0.79 % |
| v1 tiers | 758 | 2.64 % | 0.66 % |
| v2b just viewed ×30 | 336 | 3.57 % | 0.89 % |
| v3b just viewed ×10 | 444 | 3.38 % | 0.90 % |
| v2a just viewed ×10 (older cart rule) | 339 | 7.37 % | 2.36 % |
| v3a just viewed ×3 | 458 | 5.24 % | 2.62 % |

Samples are small (a few purchases per row): treat conversion as indicative, CTR as the steadier signal.
Re-run `queries/variants.sql` for current numbers.

## 7. SQL gotchas found on the way

- `recent_views` must be cast before array functions: `arrayMap(v -> v.product_id::String, recent_views::Array(JSON))`.
- Time filters on Dynamic `ts` need the cast: `ts::DateTime64(3) >= '2026-11-07 00:00:00'`.
- The Query API accepts `"format": "TSVWithNames"`: the full history (2 M sessions + 12 M events)
  exports in under a minute in 24 h / 12 h slices (`python -m offline.pull_data`).
