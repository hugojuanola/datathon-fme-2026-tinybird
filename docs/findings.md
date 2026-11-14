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

## 8. Reliability: what starves the serving loop (incident of 14 Nov, 13:14–13:31 UTC)

For three stretches of a few minutes, 25–50 % of the requests went unanswered and p95 latency rose from
1.6 s to 3 s. Nothing was wrong with the recommender: the laptop and its uplink were busy with something else.

| When (UTC) | What else was running | Missing answers |
|---|---|---|
| 13:14–13:19 | a second copy of the server in dry-run: state bootstrap = 16 heavy aggregations over the 12 M-row history, then the model scoring all 5,100 products with every core | 24–96 per minute |
| 13:20–13:22 | a test script doing the same bootstrap | 18–46 per minute |
| 13:26–13:27, 13:30 | writing 550 MB of exports and an 18 MB cache **inside the repo, which lives in OneDrive**: the sync client used ~25 % of the CPU and the whole uplink (~100 KB/s) | 55, 18, 70 per minute |

The live process logged `Read timed out` on both its queries and its inserts: its small HTTP calls were
queuing behind the uploads. What changed, all in the repo:

- **Start-up without heavy queries.** The history is loaded from a local cache built offline
  (`offline/build_cache.py`, 4 s to load); the live stream is replayed from a local journal and caught up
  from `shop.events` in 50,000-row pages. A cold start went from 116 s of heavy SQL to 32 s of light pages.
- **Bulky files out of the synced folder**: `SKORE_DATA_DIR`, `SKORE_LOGS_DIR`.
- **Priorities**: the server raises its own (`reco/priority.py`), offline scripts lower theirs.
- **Hand-over without a gap**: `--standby` loads everything and waits for a `GO` file (7 s gap vs 20–90 s).
- **Answers are inserted by a second thread**, so a slow insert no longer delays the next poll; timeouts cut
  from 3 s to 1.5 s (a call that takes longer is useless anyway). p95 went from 1.65 s to 1.4 s.
- **Stock changes**: they land every 5 minutes on the dot and become queryable ≈0.8 s later. A request in
  that window is held (≤1.6 s) until the new stock list is in, and the catalogue is polled every 0.2 s around
  the mark. Before: 1–3 invalid answers per mark. After: none.

## 9. The learned ranker (`skore_money_v5`)

**What it is.** Two LightGBM models multiplied, `P(click | shown) × P(purchase | click)`, over 32 features
that describe the product (popularity, cart and buy rates, price), how it matches the session (category,
subcategory and brand of the last view, share of recent views in its category, price vs the viewed products)
and how it matches the shopper (share of their views and purchases in the product's category and
subcategory, abandoned cart, price level). No product id, no user id: it has to work on shoppers and products
it has never seen. Served in two stages: the rules retrieve 500 candidates, the model ranks them.

**What it is trained on** (`offline/build_dataset.py`): 3.3 M rows = one per (request, product shown).
2.9 M from the old carousel log (every clicked request + 12 % of the rest, weighted back) and 280 k from our
live feedback (weight ×5: it is the real simulator, and the only place with cross-category impressions).
The store is replayed in time order, so each row only knows what was known at that moment. Rows where the
shopper had already bought the product are dropped: live, those are never shown.

**Validation, always on the future** (`offline/train.py`; the model does not see the slot here):

| Among the 10 products shown, how high does it rank the one that was bought? | as shown | popularity | rules (v4) | model (v5) |
|---|---|---|---|---|
| Log, last 7 days (1,048 purchases): reciprocal rank, slot-debiased | 0.324 | 0.463 | 0.523 | **0.574** |
| Log, last 7 days: bought product in its top 3 | 34.9 % | 61.8 % | 67.0 % | **71.2 %** |
| Live, held-out last quarter (93 purchases): reciprocal rank, slot-debiased | 0.351 | 0.335 | 0.404 | **0.461** |
| Live held-out, new shoppers (44): bought product in its top 3 | 36.7 % | 48.3 % | 51.7 % | **65.1 %** |
| Live held-out, known shoppers (49): bought product in its top 3 | 42.3 % | 36.9 % | 37.9 % | **53.1 %** |

"Slot-debiased" weights each purchase by the inverse of the attention its slot got, so a ranker is not
rewarded for agreeing with the order the products happened to be shown in. The model wins on the log, on
live feedback, and for new and known shoppers separately; the live samples are small, the direction is
the same everywhere.

**Calibration on held-out live feedback** (predicted vs observed purchases per impression): same category
as the last view 0.170 % vs 0.211 %; other category 0.099 % vs 0.100 %; home 0.043 % vs 0.045 %; abandoned
cart 0.222 % vs 0.227 %; new shoppers 0.177 % vs 0.219 %. The model has learned the cross-category
trade-off that the log alone cannot teach.

**What it looks at** (share of the click model's gain): shopper's share of views in the product's category
20 %, shopper's buy rate 16 %, slot 10 %, popularity 10 %, product cart rate 6 %, abandoned cart 4 %.

**Speed.** Ranking 500 retrieved candidates takes 14 ms per request (the whole catalogue: 120 ms) and
returns the same top 10 as ranking everything in 98 % of requests (99.7 % overlap, same first product in
100 %; 299 live requests).

**Train/serve parity.** `featurize()` is the only feature code. A server state built from RawTree was
compared with the state the training set is built from, shopper by shopper: 378 of 400 identical, the
other 22 had new live events since the export.

## 10. Live A/B: the learned ranker against the rules (14 Nov, 13:34–13:57 UTC)

Same traffic, split by request id, realised purchases:

| | Requests | Purchases | Conversion |
|---|---|---|---|
| `skore_money_v4` (rules) | 2,024 | 29 | 1.43 % |
| `skore_money_v5` (ranker) | 2,275 | 56 | **2.46 %** |

2.4 standard errors apart; for known shoppers 2.10 % vs 0.97 % (2.6 standard errors), for new shoppers
3.50 % vs 2.68 % (not conclusive on its own). The organisers' reference was at 2.03–2.06 % in the same hour.
Mechanism (measured by the watch session, `realtime_analyisi_leaderboard/notes/`): v5 puts 62 % of a known
shopper's slots in subcategories they have bought from before (v4: 34 %) and still sells more outside them.
The log-based hit rate of §6 had v5 *below* v4 on product pages (64 % vs 74 %): the log cannot credit a
cross-category recommendation, the live simulator does. v4 was retired at 13:57 UTC.

## 11. Does it hold for shoppers without history? (the final round has "new shoppers")

Live feedback the deployed model had never seen (8,687 requests after its training export), slot hidden,
slot-debiased. "Bought product ranked first / in the top 3" among the 10 shown:

| | Rules | Model |
|---|---|---|
| Known shoppers, real history (51 purchases) | 20 % / 44 % | 24 % / 66 % |
| Known shoppers, history erased | 13 % / 28 % | 11 % / 32 % |
| New shoppers as they are: only today's live events (53 purchases) | 15 % / 47 % | **36 % / 60 %** |
| New shoppers, live events erased too | 13 % / 38 % | 24 % / 45 % |

- For a real new shopper the model is clearly better than the rules, and it still is with nothing known
  about the shopper at all: the product and session features carry over.
- What a new shopper does *during the stream* is worth a lot (36 % vs 24 % ranked first). The state is
  updated from `shop.events` every second, so a shopper who appears in the final has a usable history
  within minutes.
- For known shoppers the history is everything: erase it and the model is no better than popularity.

## 12. Exploration (practice round only)

Since 13:57 UTC, 20 % of the requests (`skore_money_v5_explore`) get 10 products drawn at random from the
model's best 20, in random order. It costs conversion on those requests and buys two things the main arm
cannot give: outcomes for products the model would not have put first (so its mistakes become visible), and
slots that are independent of relevance (so position bias can be separated from quality). The practice
round is not scored: that is when to pay for it. Off before the final.

## 13. Shoppers buy by the attributes in the description (the biggest lever found)

Every description names exactly two of 20 attributes ("organic ingredients", "a luxury feel", "designed for
kids", "great value for money"…) — true for the 5,000 original products and for the 200 added during the
event. Two of the four description templates name them unambiguously ("From X (Sub): A, B." and "Sub by X,
featuring A. Comes with B."); the vocabulary is taken from those and matched in every description
(`reco/features.py`, `attribute_phrases`).

**Test on the 60-day history.** For 20,000 first-time organic purchases in the last week, compare the
product bought with a popularity-matched product of the *same subcategory* that was not bought, and score
both by how well their attributes match the shopper's past. AUC (0.50 = no information):

| Evidence used for the shopper's taste | All | No earlier purchase | 1–2 purchases | 3–9 | 10+ |
|---|---|---|---|---|---|
| attributes of what they bought | 0.687 | 0.500 | 0.611 | 0.658 | 0.717 |
| attributes of what they carted | 0.710 | 0.576 | 0.645 | 0.694 | 0.730 |
| attributes of what they viewed | 0.659 | 0.623 | 0.632 | 0.649 | 0.668 |
| for comparison: item-item co-purchase similarity | 0.629 | | | | |
| for comparison: brands they bought | 0.498 | | | | |
| for comparison: closeness to their usual price | 0.525 | | | | |

- The attributes say more than "who bought X also bought Y", and brand says nothing inside a subcategory.
- Views are enough: a shopper who has never bought anything already has a readable taste (0.62). That is
  what a shopper first seen in the final will have within minutes.
- Two products are co-purchased 14× more than chance inside a subcategory with no shared attribute, 23× with
  one, 30× with two (2.2× / 4.8× / 5.8× across subcategories).
- Attributes also carry popularity: "great value for money" products sell 347 purchases each against ≈100 on
  average — the only popularity hint a brand-new product has (`attr_prior`).

**Confirmed on the live carousel** by the watch session, independently and adjusted for slot
(`realtime_analyisi_leaderboard/notes/2026-11-14_1612_attributes-confirmed-on-carousel.md`): purchases per
impression go from 0.030 % to 0.303 % from the lowest to the highest attribute-affinity band (0.25× to 2.2×
what the same slots sell on average); sharing both attributes with the last viewed product sells 4.2–4.5×
the average. 44 % of the impressions we were giving known shoppers were in the two lowest bands.

**What the system does with it.** Each shopper keeps three attribute profiles (purchases, carts, views),
updated from the live stream. Features: how much more than everybody the shopper goes for the product's two
attributes, per kind of evidence (`u_attr_p`, `u_attr_c`, `u_attr_v`, and the worse of the two attributes);
attributes shared with the last viewed product (`recent_attr`); and `attr_prior`. Retrieval lifts products
by the same match, so a well-matched product from a subcategory the shopper never bought can reach the ranker.

## 14. Rankers v6, v7, v8: held-out comparison

Held-out live feedback (last quarter of our feedback at training time: 12,640 requests, 673 clicks,
197 purchases), slot hidden from the models, slot-debiased (`python -m offline.train NAME` prints this table
for every ranker in `models/`). "Bought product ranked first / in the top 3 among the 10 shown":

| | v5 | v6 | v7 | v8 |
|---|---|---|---|---|
| All requests | 18.0 % / 40.9 % | 19.7 % / 49.3 % | 25.7 % / 52.6 % | **28.3 % / 60.7 %** |
| Known shoppers (99 purchases) | 15.7 % / 40.7 % | 20.3 % / 49.2 % | 29.4 % / 61.8 % | **31.1 % / 72.8 %** |
| New shoppers (98 purchases) | 20.1 % / 41.1 % | 19.2 % / 49.3 % | 22.3 % / 44.2 % | **25.8 % / 49.5 %** |
| Clicks, all requests (reciprocal rank) | 0.311 | 0.337 | 0.389 | **0.411** |

- **v6** = v5 + products added during the event (`is_new_item`, `item_age`, `recent_new`: on our feedback
  they sold 2.5× what v5 predicted, 3.6 % per impression when the shopper had just viewed one), price drops
  (`discount`), age of an abandoned cart (`u_cart_age`), how much of a subcategory the shopper already owns,
  and brand history.
- **v7** = v6 + the attribute features of §13. `u_attr_c` alone is 10 % of the click model's gain, third
  after the shopper's category share and buy rate.
- **v8** = v7 without the two brand-history features, refit on all the data. Removing them made every row
  of the table better: inside a subcategory brand says nothing (§13), so they were only noise to fit.
  A feature that the product id could hide behind is exactly what to avoid for the final's new products.
- Live: v7 from 15:12 UTC, v8 from 15:25 UTC (60 % of the traffic, v5 kept at 30 % as the control). The
  watch session checked the mechanism on v7's lists: 75 % of a known shopper's slots have attribute
  affinity above 1.25 (v5: 42 %), 10 % below 1.0 (v5: 38 %).

**The final-round scenario** (same held-out feedback, shopper features erased; "ranked first / top 3"):

| | Rules | v5 | v7 |
|---|---|---|---|
| Known shoppers, history erased | 15.7 % / 34.9 % | 14.3 % / 43.7 % | 18.4 % / 43.8 % |
| New shoppers as they are | 17.7 % / 41.3 % | 20.1 % / 41.1 % | 22.3 % / 44.2 % |
| New shoppers with at most 10 views so far (25 purchases) | 22.8 % / 50.6 % | 26.4 % / 43.5 % | 30.0 % / 58.8 % |

The ranker is the best of the three with full history, with thin history and with none.

**Retrieval is not a bottleneck.** On 400 live requests, ranking the 1,000 retrieved candidates gives the
same top 10 as ranking all 5,200 products in 99.9 % of positions (same first product in 100 %); 39 ms per
request against 200 ms.

## 15. Judging an A/B: the organisers' own metric, and how noisy it is

The leaderboard API reports, per `model_version` and time window, the **expected** purchases per 100
requests under the hidden model — the number the final is scored on, without the coin flip of realised
purchases (`python scripts/arms.py HH:MM HH:MM`, UTC; it also splits cold and warm requests). Every version
we deploy is an arm with its own `model_version`, split by a hash of the request id, so arms that run over
the same minutes see the same kind of traffic.

**How much is noise.** Requests are very unequal (a `home` page is worth about 0.1 expected purchases per
100, an abandoned cart 10 or more), so even the expected metric needs volume:

| Check | Result |
|---|---|
| Two arms running the *same* code, 16:45–17:12 UTC, about 1,550 requests each | 2.331 vs 2.207 on the expected metric; **15 vs 29 realised purchases** |
| The same arm in consecutive quarters of an hour (about 850 requests) | v9: 2.11 → 2.45 · v9w: 2.45 → 2.22 |

A difference of 0.3 between two arms after 15 minutes means nothing; 0.12 after half an hour is what two
identical arms show. We decide on effects several times that size, or on hours of traffic (the overnight
runs), and never on realised purchases alone.

**What the afternoon of 14 Nov says** (expected purchases per 100 requests; reference 2.06–2.08, baseline
0.60–0.67 over the same hours):

| Version | What it is | Requests | All | Cold | Warm |
|---|---|---|---|---|---|
| v4 | rules only | 2,024 | 1.45 | 2.01 | 1.16 |
| v5 | first learned ranker | 12,910 | 1.81 | 2.57 | 1.41 |
| v6 | + new products, price, cart age | 1,383 | 1.70 | 2.48 | 1.31 |
| v7 | + description attributes (§13) | 1,432 | 2.42 | 2.88 | 2.17 |
| v8 | v7 without brand history | 2,665 | 2.35 | 3.22 | 1.89 |
| v9 | v8 + attribute pair, purchases in the subcategory | 2,822 | 2.37 | 2.84 | 2.11 |
| v9w | v9, live feedback weighted ×20 instead of ×5 | 2,533 | 2.32 | 3.21 | 1.87 |
| v9d | one model for "purchase" instead of click × purchase-given-click | 1,668 | 2.12 | 2.96 | 1.69 |
| exploration arms | top 4 shuffled, 6 drawn from ranks 5–14 | 2,718 | 1.2–2.3 | | |

- The step that matters is **v5 → v7: the attributes of the description** (+0.6, far outside the noise,
  on both kinds of request). It is the largest effect we have measured.
- v7, v8, v9, v9w and v10 are within noise of each other as a whole. What does repeat: weighting our live
  feedback more (v9w) is better on cold requests (3.21 vs 2.84) and worse on warm ones (1.87 vs 2.11) —
  the old carousel's log knows the known shoppers, the live stream is the only place that knows the new
  ones. Hence the routing in `reco/serve.py`: a ranker written `"v9w|v9"` sends cold requests to the first
  model and the rest to the second.
- One model predicting the purchase directly (v9d) is worse than the product of the two models: clicks are
  three times more frequent than purchases and carry most of the learning.
- Exploration costs a quarter to a third of the conversion of the requests it touches (v8 2.35 → 1.76,
  v5 1.81 → 1.21): it stays off in the final.

Against the field in the last hour before this note (17:19 UTC): us 2.18, the next team 1.83, the
reference 2.04; cold 2.76 against 1.73 for the reference.

## 16. The store moves: trends, price changes, new products (`python -m offline.store_moves`)

The brief announces them for the final and the 60-day history has none, so their shape can only be read
from today's organic stream. Every aggregate below is computed in RawTree (per minute or per 10 minutes, by
subcategory, category, brand and product) and the report takes 8 seconds.

**Trends.** One subcategory at a time sells many times its usual share, for 45 minutes, starting at :30 of
every odd UTC hour:

| Subcategory | When (UTC) | Purchases | Views | Usual share of purchases |
|---|---|---|---|---|
| Aquariums | 09:30–10:15 | ×8.7 | ×4.2 | 0.32 % |
| Kettles | 11:30–12:15 | ×11.9 | ×4.2 | 0.99 % |
| Cutting Boards | 13:30–14:15 | ×9.7 | ×3.0 | 0.39 % |
| Bike Helmets | 15:30–16:15 | ×7.8 | ×3.6 | 0.94 % |

- Nothing moves at category or brand level, and no single product does: it is the subcategory.
- Inside it every product rises alike: a product's share of the subcategory during the trend and during the
  rest of the day correlate 0.89–0.95. So one multiplier per subcategory is the right shape.
- It is a step, not a ramp: full strength from the first minute to the last.
- **Our own carousel shows it too**, before any version knew about trends: the products of a trending
  subcategory that happened to be shown were clicked 1.68 % of the time against 0.48 % for everything else,
  and bought 0.67 % against 0.15 % (891 impressions). For Bike Helmets the ranker's predictions were beaten
  by ×1.9 (clicks) and ×2.2 (purchases) during the trend and missed by ×0.6 and ×0.4 the rest of the day.
  A shopper who was looking at something else still bought them at 0.51 % per impression.

**The detector** (`reco.features.Trends`, run by the server every second and by the training replay).
Views are 20 times more numerous than purchases, so they say *when*: a group is trending when its views of
the last 2–3 minutes are at least twice its usual share (with 40 views or more). Purchases say *how much*:
the lift is the ratio of purchases to what the usual share predicts over 5 minutes, shrunk towards what the
views imply (purchases rise like views to the power 1.8) with 3 pseudo-purchases. Replayed minute by minute
on the stream of 14 Nov (488 minutes, 179 groups):

| Trend | Seen after | Dropped after its end | Lift, first 3 minutes | Lift afterwards |
|---|---|---|---|---|
| Aquariums | 3 min | 1 min | 6.3 | 8.9 |
| Kettles | 2 min | 1 min | 7.6 | 12.0 |
| Cutting Boards | 3 min | about 4 min | 5.6 | 7.1 |
| Bike Helmets | 2 min | 2 min | 5.0 | 8.1 |

False alarms: 5 group-minutes out of 87,352, all below ×3 and gone within two minutes. (A first version
that used purchases alone saw the trends as fast but held on 5–9 minutes after they ended and
underestimated them: lifts of 4–8.) The same statistic also watches categories and brands — a trend in the
final could have another shape — and those levels only speak when no subcategory explains the move, because
a trending subcategory drags its category and its brands up with it.

**Price changes.** Promotions of about 19 % on some 600 products, for two hours, then back (10:30–12:30,
13:30–15:30, 16:30–). The discounted products take ×1.2 to ×1.5 of their previous share of purchases in one
batch and no more than before in another (the batches overlap with trends, which blurs it): an elasticity
around 1, a small effect next to a trend. The training table used to stamp the *latest* price on every live
row, so no model could have learned it; the replay now applies each price change at its time
(`offline/build_dataset.py`), and `recommend()` has an optional elasticity that no arm uses yet.

**New products.** 100 at 10:00 and 100 at 14:00 UTC, spread over half the subcategories. They take their
fair share of purchases from the first ten minutes (1.9 % of the catalogue, 2.0–2.8 % of the purchases): to
the shoppers they are ordinary products, so the ranker must not wait for them to accumulate history — which
is what the attribute features and the exposure-corrected popularity are for (§13, §14).
