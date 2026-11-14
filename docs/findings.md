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

## 5. SQL gotchas found on the way

- `recent_views` must be cast before array functions: `arrayMap(v -> v.product_id::String, recent_views::Array(JSON))`.
- Time filters on Dynamic `ts` need the cast: `ts::DateTime64(3) >= '2026-11-07 00:00:00'`.
- The Query API accepts `"format": "TSVWithNames"`: the full history (2 M sessions + 12 M events)
  exports in under a minute in 24 h / 12 h slices (`python -m offline.pull_data`).
