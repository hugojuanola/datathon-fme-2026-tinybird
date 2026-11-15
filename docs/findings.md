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

False alarms: 5 group-minutes out of 87,352, all below ×3 and gone within two minutes. Replayed again
**every second**, as the server really runs it, from the server's own journal of the stream (9.5 hours,
`python -m offline.store_moves seconds`): each trend is seen 49–120 seconds after it starts and dropped one
to three minutes after it ends; purchases alone at ×2.5 fired on noise for 174 seconds of the day (three
short ones showed up live at 18:20 UTC: purchases come in baskets), so that path now needs ×4 with 12
purchases and the false alarms are 19 seconds in 9.5 hours. (A first version
that used purchases alone saw the trends as fast but held on 5–9 minutes after they ended and
underestimated them: lifts of 4–8.) The same statistic also watches categories and brands — a trend in the
final could have another shape — and those levels only speak when no subcategory explains the move, because
a trending subcategory drags its category and its brands up with it.

**Measured live: a trending product sells ×8.3 in our carousel.** The first trend with the detector in
production was Game Consoles, 19:30–20:15 UTC. The server announced it **41 seconds** after it started and
let it go 90 seconds after it ended; its lift went from 3.6 to about 10 in ten minutes (median 8.6). The
arms that lifted the subcategory showed 9,074 of its impressions. Against what v9 — which knows nothing
about trends — predicted for those same impressions, at the slot they were in:

| | Observed | v9 expected | Ratio (95 %) |
|---|---|---|---|
| Clicks | 129 | 32.6 | ×3.96 (3.3–4.7) |
| Purchases | 52 | 6.2 | **×8.33 (6.3–11.0)** |
| Same products, not trending (3,876 impressions v9 had not seen) | 6 purchases | 6.8 | ×0.88 |

The ratio is the same for shoppers who were looking at something else (×8.4) and in every slot band from
1 to 6. So what the organic stream says is what the carousel does, one to one, and the detector's own
estimate is the right multiplier: the lift is applied in full (exponent 1). The arms of that evening used
exponent 0.75 (about ×5) and, as an A/B over one trend, read +0.03 ± 0.20 against no lift — a single
45-minute trend cannot resolve it; the 9,000 impressions can. One thing that looks like cannibalisation and
is not: lists that fill up with trend products sell nothing else, but those are the weak requests (home
pages, no signals). Across versions the click rate of a list follows its quality (best sellers 2.4 %, rules
4.8 %, v5 5.9 %, v9 7.4 %) while purchases per click stay at 30–33 %: clicks are not a fixed budget.

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

## 17. The night of 14 Nov: one experiment for two questions

By the evening no ranker of the attribute family (v7 to v16) had separated from another at the precision a
few hours give. The clearest warning came at 17:25–17:40 UTC: three arms that were behaving identically (no
trend was running, so the two "trend" arms did nothing different from the control) read **1.92, 2.40 and
2.59** on the expected metric with about 900 requests each. A quarter of an hour with three arms decides
nothing; a night with about 100,000 requests does.

| Ranker set-up | Lift off (6 % each) | Lift ^ 0.75 (19 % each) |
|---|---|---|
| `v9` for every request | `skore_money_v21` | `skore_money_v22` |
| `v9w` for cold requests, `v9` for the rest | `skore_money_v23` | `skore_money_v24` |
| `v16` for every request | `skore_money_v25` | `skore_money_v26` |
| `v16w` for cold requests, `v16` for the rest | `skore_money_v27` | `skore_money_v28` |

- **Which rankers** is read from all the traffic, pooling the two columns (they only differ while a trend is
  running): new against old is (v25 + v26 + v27 + v28) against (v21 + v22 + v23 + v24), routed against single
  is the second and fourth rows against the first and third. About 25,000 requests per set-up by the morning:
  differences of 3–4 % become visible.
- **The trend lift** is read from the minutes a trend is running: even against odd versions.
- Three quarters of every set-up already apply the lift, because it is our best guess if nobody is there to
  choose before the final: the organic stream says purchases ×8–12, our carousel said ×2–5 on the few
  hundred impressions it had (§16), and a lift of ×5–6 (the detector's ×8–12 to the power 0.75) is close to
  right across that range.
- Read it with `python scripts/arms.py 17:45 07:30` (UTC); the final is served by a single arm
  ([`docs/final-round.md`](final-round.md)).

**`v16` / `v16w`** (`python -m offline.train v16`, `python -m offline.train v16w 20`): all of the day's
feedback up to 17:35 UTC (770,204 live rows on top of the log), the 57 features, live rows with the price
the shopper really saw and the detector's reading at that moment. Held-out live feedback (last quarter:
19,279 requests, 439 purchases), bought product ranked first / in the top 3 among the 10 shown, for the
fits that had not seen that quarter:

| | v9 | v16 (live ×5) | v16w (live ×20) |
|---|---|---|---|
| All requests | 20.5 % / 48.0 % | **22.2 % / 49.1 %** | 21.3 % / 47.3 % |
| Known shoppers (258 purchases) | 22.4 % / 47.7 % | **24.2 % / 47.7 %** | 22.4 % / 46.3 % |
| New shoppers (181 purchases) | 18.0 % / 48.4 % | 19.5 % / **50.9 %** | **19.8 %** / 48.7 % |

Small steps, all inside the noise of 439 purchases — which is why they go to the live test instead of
straight to the final. Two things this table taught us on the way:

- Weighting live rows ×20 does **not** help new shoppers offline (19.8 % vs 19.5 %), while live it looked
  better on cold requests (3.21 vs 2.84, §15). Neither is conclusive: routing is in the experiment as a
  question, not as a fact.
- A ranker refitted on all the data looks far better on the same held-out quarter than its own validation
  fit (v16 on new shoppers: 32.0 % ranked first against 19.5 %): the table is only meaningful for fits that
  did not see the period, and rankers trained at different hours cannot be compared on it.

**Checked and ruled out the same evening** (each a few seconds of SQL or of local feedback):

- *Is a product's popularity today different from its 60-day history, beyond the trends?* No: the ratio of
  today's share to the historical share in the first and in the second half of the day correlate 0.10
  (purchases, 331 products) and 0.05 (views, 4,785 products). The history is the right prior; nothing to
  gain from a "popular this hour" feature.
- *Are abandoned carts ranked well?* For known shoppers they are a third of the impressions and 57 % of the
  purchases. The ranker's predictions match what happened by age of the cart, by slot, by category of the
  session and by attribute affinity (observed over predicted between 0.85 and 1.1 everywhere), and the
  carted product that gets bought is in slot 1 almost half of the time.
- *Does the request say more than we use?* No: page, device, region, recent views, new-shopper flag. All used.

## 18. Reliability, second look (14 Nov, evening)

On the hourly board our share of answers on time was 96–99 % against 99.8 % for the best teams. The losses
come in bursts of one to four minutes in which every call to RawTree (polls, inserts, catalogue and event
refresh) slows from 0.2 s to more than 1 s or times out together, while ranking keeps its 45 ms: it is the
path to RawTree, not our process. What we checked:

| Suspect | Test | Verdict |
|---|---|---|
| Our own analysis jobs on the laptop | Ran a heavy one (12 M-row read, model scoring) on purpose for 45 s | No effect: polls 213–221 ms, no failures. The machine has 16 threads and 14 GB free |
| Uploads (git push of several MB, assistant steps) | Pushed 5 MB during a quiet minute | No effect |
| RawTree rate limits | 10,000 queries/s per database, we send about 15 | Not it |
| The 5-minute stock mark | Bursts at 16:05 and 16:25 UTC sit on marks, the one at 16:47–16:51 does not | Not the cause; requests right after a mark wait at most 1.6 s for the new stock |
| The Wi-Fi link | `scripts/netmon.py`: ping to the router 11–27 ms on average with spikes of 100–360 ms in *good* minutes (a wired link gives about 1 ms) | The weakest part of the path, and the one we can change: a cable for the final |

The monitor keeps logging one line per second, so the next burst will show whether the router stopped
answering (Wi-Fi) or only RawTree did (the line or the internet).

**The worst loss of the day had nothing to do with the network.** At 18:53:15 UTC the console window the
server was running in was closed by mistake. Nobody answered for four minutes (723 requests; on-time 73 %
in that quarter of an hour, third on the board for that window) until it was started again. The connection
monitor, in a sibling window, wrote its last line the same second. Since 19:11 UTC the server has **no
window**: `scripts/swap_server.ps1` starts `pythonw -m reco.supervise` through Windows itself, so it is not
a child of any terminal or assistant session; the supervisor runs the server hidden, restarts it two
seconds after any exit, and the server ignores Ctrl+C. Since then: 99.8 % answered, no restart in the log.

## 19. A faster judge: what the shopper goes on to buy (`python -m offline.next_purchase`)

A live A/B needs hours to separate two rankers (§15), and our own feedback only says how the 10 products
we showed did. The organic stream answers a sharper question for free: **10 % of our requests are followed,
within half an hour, by a purchase of the same shopper somewhere in the store** (5,635 requests in five and
a half hours). A ranker that understands the shopper should have had that product in its list. No ranker
chose what was bought, so the comparison is fair, and it rests on thousands of purchases. The stream is
replayed in time order and, at each of those requests, every ranker in `models/` orders the same 1,000
candidates.

Share of the next purchases (products not bought before) that were in the ranker's first 10 — 2,384
purchases after requests of 13:14–18:44 UTC, one standard error about 0.7 points:

| | rules | v5 | v8 | v9 | v9w (live ×20) | v10 | v16 | v16w (live ×20) |
|---|---|---|---|---|---|---|---|---|
| All shoppers | 7.5 % | 10.1 % | 12.8 % | 12.5 % | 11.5 % | 12.4 % | 12.7 % | 12.2 % |
| Known shoppers (1,819) | 6.8 % | 9.9 % | 12.9 % | 12.1 % | 11.6 % | 12.1 % | 12.5 % | 12.2 % |
| New shoppers (565) | 9.6 % | 10.8 % | 12.7 % | 13.5 % | 11.2 % | 13.5 % | 13.3 % | 12.0 % |

- It orders the versions as the live metric did (rules 1.45 → v5 1.81 → the attribute family 2.3–2.4), so
  it is a usable first filter: an idea that does not move it is not worth an arm.
- Weighting live feedback ×20 does not help anybody on this measure either, new shoppers least of all.
  With §17 that makes three measurements against routing by kind of request: one ranker for everyone.
- It is not the organisers' metric: a shopper who goes and buys something was looking for it, and a
  carousel also has to tempt the one who was not.

**Where those purchases are** (v16; "retrieved" = among the 1,000 candidates the rules hand to the ranker):

| The product bought next… | Share of the purchases | In our 10 | Retrieved |
|---|---|---|---|
| was in an abandoned cart | 12 % | 43 % | 99 % |
| is in a subcategory the shopper had bought in | 53 % | 17 % | 96 % |
| is in the category of the last view | 25 % | 19 % | 98 % |
| is in a subcategory the shopper had never bought in | 47 % | 8 % | 72 % |
| had been viewed in the session (`recent_views`) | 0.6 % | 67 % | 100 % |
| is a product added during the event | 7 % | 32 % | 92 % |

Three quarters of what a shopper buys next is outside the category they are looking at, and almost never
something they have just viewed: the session says where they are, their history says what they buy.

**What is left of a subcategory.** Two thirds of a known shopper's next purchases fall in a subcategory
they already bought in, where they own 5 products on average (and never buy one twice). Where the product
stands by popularity:

| Popularity rank… | 1st | 2–3 | 4–10 | 11–30 | 31+ |
|---|---|---|---|---|---|
| among all the products of the subcategory | 7.5 % | 12.4 % | 25.9 % | 34.5 % | 19.7 % |
| among those the shopper has not bought yet | 12.0 % | 14.1 % | 27.9 % | 30.6 % | 15.4 % |

For shoppers who own 11 or more products of the subcategory, the purchase is in its overall top 10 in 25 %
of the cases — and in the top 10 of what is left for them in 50 %. Our rankers knew only the first row
(popularity against the whole subcategory) and found 39 % of the purchases at ranks 1–3 but 7 % of those at
ranks 11–30. Hence two features, `rank_left` and `pop_vs_left` (`reco/features.py`): how many better
sellers of the subcategory the shopper has not bought yet, and the product's popularity against the best of
those.

**Checked on the way, and ruled out:**

- *The shopper's price tier inside a subcategory.* It is a stable trait (a purchase and the mean of the
  earlier ones correlate 0.49; the two halves of a shopper's history 0.87; against 0.26 for the absolute
  price we use), yet it does not pick the product: popularity alone orders the products of a subcategory with
  AUC 0.839, popularity plus distance to the shopper's tier 0.841.
- *Miscalibration between kinds of product.* On three hours v9 had not seen, observed over predicted
  purchases are 0.89 for abandoned carts, 0.91 for bought subcategories, 1.04 for the category of the last
  view; nothing to correct by hand.
- *Where the value of a list is.* The top fifth of our impressions by score holds 89 % of the purchases,
  the bottom three fifths 1 %: the first slots decide.


## 20. A third model: what the store itself teaches (`offline/organic.py`), and the arms of the night

The two carousel models learn from what a carousel showed. The purchases of §19 are a different teacher:
the product the shopper was really after, whoever showed it. `offline/organic.py` trains a model for "this
shopper is about to buy this product" on three kinds of moment, each followed within 30 minutes by a
purchase of the same shopper: requests of the live stream (7,441), requests of the old carousel (14,930),
and 104,951 moments inside the purchase sessions of the 60-day history written as the request they would
have been (the shopper has just viewed a product, or has just arrived). 153,580 purchases; for each moment,
the product bought against 30 products the rules retrieved and the shopper did not buy.

On its own it is a poor ranker of 1,000 candidates (8 % of next purchases in its top 10; v9 13 %). As a
factor on top of v9 — score = P(click) × P(purchase | click) × organic — it adds on both offline judges, on
hours neither model had seen:

| | v9 | v9 × organic ^ 0.5 | v9 × organic ^ 1 | organic alone |
|---|---|---|---|---|
| Our carousel's held-out purchases (904): reciprocal rank among the 10 shown | 0.384 | 0.398 | **0.406** | 0.406 |
| … ranked first | 17.8 % | 19.8 % | **20.4 %** | 21.3 % |
| Our carousel's held-out clicks (2,865): reciprocal rank | 0.323 | 0.336 | **0.340** | 0.351 |
| Next purchases in the store (2,100): in the top 10 | 13.2 % | 14.0 % | 13.7 % | 8.2 % |
| … weighted by the attention of the slot | 5.8 % | 6.2 % | **6.5 %** | 3.7 % |

A model that never saw a carousel orders our carousel's purchases as well as v9 does: shoppers buy from a
carousel what they were going to buy anyway. Without the history's sessions (25,000 purchases instead of
153,000) the same model added nothing on the carousel's purchases: here more data did matter. It changes
3 of the 10 products of a list on average. It costs 115 ms on 1,000 candidates, so it is asked only about
the best 300 of the carousel models (identical lists on 250 requests; 34 ms).

**What did not survive the evening:**

- `v16` (all of Saturday's feedback, more features) against `v9` on warm requests, live: 1.76 against 1.99
  on 8,150 requests each, 3.2 standard errors. Both offline judges had them level or v16 slightly ahead.
  Offline numbers screen ideas; the live arms decide.
- Weighting live feedback ×20 for cold requests (v9w, v16w): no gain on any of three measurements.
- `rank_left` / `pop_vs_left` (§19) in the carousel models: 0.1–0.5 % of their gain and no change on either
  judge (`v17`). The organic model does use them (2.5 % of its gain), so they stay as features.

**Live since 20:32 UTC**, one ranker for every request:

| Arm | Traffic | What |
|---|---|---|
| `skore_money_v31` | 30 % | v9 + trend lift (full) — the version to beat |
| `skore_money_v32` | 30 % | v9 × organic + trend lift |
| `skore_money_v33` | 20 % | v9b (v9's features retrained on all of Saturday) + trend lift |
| `skore_money_v34` | 10 % | v9, no lift |
| `skore_money_v35` | 10 % | v9, lift ^ 0.5 |

Outside a trend v31, v34 and v35 are the same ranker: pooled (50 %) against v32 and v33 they answer
"does the organic factor help live?" and "does retraining v9 on more data help or hurt?". While a trend
runs, v31 / v34 / v35 give the dose of the lift.

## 21. What v9 already knows: ten checks against its own predictions, and the one that left something

On the evening of 14 Nov the next team was within 0.05 purchases per 100 requests, so we went looking for
signals the ranker does not use. One method for all of them, and it is the lesson of the section: **hold
what the ranker already predicts equal.** The lists are those of 17:00–20:20 UTC, which v9 had not seen
(30,893 lists, 308,928 impressions, 2,312 clicks, 724 purchases). For every impression v9 gives the
probability of a click and of a purchase at the slot where it was shown; a group of impressions where
observed / predicted stands apart from the rest holds information v9 does not use. For a continuous
property: a conditional logit of which of the ten was chosen, with log(v9's prediction) next to it (its
coefficient comes out at 0.9: the order inside a list is about right).

Holding only the slot equal is not enough. That way the attribute affinity of §13 — a feature v9 has had
all day — "explains" ×1.28 on clicks and ×1.57 on purchases; with v9's prediction held equal it is ×1.05
(+2.0 standard errors) and ×1.00 (+0.1), as it should be for something the ranker already uses.

| Signal v9 does not have | Against v9's own prediction | Verdict |
|---|---|---|
| "Shoppers who bought this also bought that": cosine between the buyers of two products in the 60 days, summed over what the shopper bought | Per standard deviation inside the list. Known shoppers: clicks ×1.04 (+1.5 se), purchases ×0.97 (−0.5 se); reordering the ten by it lowers the reciprocal rank of the purchase (0.381 → 0.363); next purchases in the store (§19) in the top 10: 13.6 % → 13.6 %. New shoppers (what they bought today): ×1.16 (+3.3 se) and ×1.23 (+2.8 se) | For a known shopper, 60 days of shares by subcategory, brand and attribute already carry it. For a new one they do not |
| The same, summed over the abandoned cart | Known shoppers ×1.07 (+2.6 se) and ×0.99 (−0.2 se). New shoppers ×1.21 (+4.5 se) and ×1.34 (+4.4 se) | The strongest of the three, for new shoppers only |
| The same, summed over the recent views | Known shoppers ×1.01 and ×0.98. New shoppers ×1.13 (+2.9 se) and ×1.06 (+0.9 se) | On clicks, for new shoppers |
| The product was already shown to this shopper today (34 % of impressions, 46 % in slots 1–2) | Purchases observed / predicted: first time 0.95, second 1.00, third 0.90. From the third time on: clicks 0.79 ± 0.05, purchases 0.85 ± 0.10 | A mild fatigue, on clicks |
| Abandoned cart: how many times the shopper carted the product | Once 0.80 ± 0.06, twice 1.03 ± 0.15, three times or more 1.25 ± 0.26 | Real: a product carted once is worth a fifth less than v9 thinks |
| Abandoned cart: views of the product after carting it | None 0.86, one 1.04, two or more 0.42 ± 0.29 (2 purchases) | Already predicted, through the age of the cart |
| The shopper had looked at the product in the 60 days and never carted it | 0.75 ± 0.10 | A look that did not end in a cart is a mild "no" |
| Product of the request's recent views (2.5 per list; 12 % of them are in our ten) | 1.11 ± 0.14; the ones v9 scores low and were shown anyway: 4 purchases for 5.8 predicted | v9 is right to leave most of them out |
| Product added during the event | 1.29 ± 0.12, against 0.91 ± 0.04 for the original catalogue | **v9 is short: below** |
| Product on promotion at the time of the impression (7.5 % of impressions, at 0.83 of the catalogue price; v9's `discount` was trained on a table that stamped the last price on every row) | 1.06 ± 0.14 against 0.94 ± 0.03 at catalogue price (60 purchases). A multiplier (price / catalogue price) ^ −1.6, the elasticity of the organic stream (§16): reciprocal rank of the purchase 0.384 → 0.384 on v9, 0.406 → 0.406 on v9 × organic; the organic factor already leans ×1.08 towards promoted products | Nothing to add |
| An id for the category, the subcategory or the brand (v9 has none, by design) | Observed / predicted per group, learned before 17:00 UTC and compared with after (trending subcategories left out during their trend): the two halves of the day agree with a correlation of +0.38 (10 categories), −0.11 (87 subcategories), +0.20 (80 brands). Multiplying v9 by the morning's ratios leaves the evening's reciprocal rank where it was (0.393 → 0.393 by subcategory, 0.388 by brand) | Nothing stable to learn: what looks like a category effect in one window is gone in the next |

Everything is within a quarter of what v9 predicts. Collaborative filtering helps exactly where the
ranker has little to go on: a new shopper's handful of events is too few for shares, and what others bought
together with their cart says more. It is not deployed: it feeds on what the shopper carted and bought
earlier in the day (56 % of today's lists for new shoppers had a purchase behind them), and the final lasts
two hours. A count must stop at the request, too: counted over the
whole day, "views after carting" looked like a ×10 signal (a shopper who did not buy from our list goes on
looking at the product afterwards); counted up to the request it is what v9 already predicts.

**Products added during the event.** After a click, a known shopper buys one of them 36.6 % of the time and
a product of the original catalogue 25.4 %; v9 expected 25.5 % and 26.9 %. New shoppers buy both alike
(42 % and 40 %), and v9 knows it. It does not fade with the product's age (4 to 8 hours old: 1.30; older:
1.28). v9 was trained when 200 such products had sold little; v9b, which has seen these hours, expects 33 %
— but brings everything else it relearned with it. The smallest change that fixes it: the score of a product
added during the event is multiplied by 1.5 (the ratio of the two calibrations for known shoppers, 1.37 /
0.90) when the shopper is a known one (`fresh` in `reco.recommend`). On held-out lists (since 16:14 UTC,
904 purchases, 121 of a new product), where the purchased product would be among the ten shown —
reciprocal rank, and how often first:

| | v9 | v9, new ×1.5 | v9 × organic | v9 × organic, new ×1.5 |
|---|---|---|---|---|
| All requests | 0.384 · 17.8 % | 0.387 · 18.4 % | 0.406 · 20.4 % | **0.409 · 20.8 %** |
| Known shoppers | 0.387 · 19.0 % | 0.393 · 20.0 % | 0.407 · 20.7 % | **0.413 · 21.3 %** |

×1.3 gives 0.409 and ×2 gives 0.412 on the last column; applied to new shoppers as well it loses (0.404 →
0.399), as the calibration said. A small step, and the ten shown cannot say what the lift brings into the
list from outside: on 276 requests of known shoppers it changes 0.42 of the ten products and takes the
products added during the event from 0.85 to 1.27 per list.

**Live since 21:32 UTC** (v31, v32 and v33 answer the same requests as before, by the same hash):

| Arm | Traffic | What |
|---|---|---|
| `skore_money_v31` | 30 % | v9 + trend lift — the version to beat |
| `skore_money_v32` | 30 % | v9 × organic + trend lift |
| `skore_money_v33` | 20 % | v9b + trend lift |
| `skore_money_v36` | 20 % | v9 × organic + trend lift + new products ×1.5 for known shoppers: every piece with evidence, as one candidate |

v34 (no lift) and v35 (lift ^ 0.5) were closed: the dose of the lift was settled per impression (×8.3
measured, ×8.6 estimated, §16), and two arms of 10 % could not have told it apart in a night.

**A model must not be asked about what it has never seen: the organic factor during a trend.** At 21:30 UTC
Face Cream started trending: a small subcategory (22 products, 0.07 % of the store's purchases; during the
trend 7–8 purchases per 5 minutes against 0.7, the detector said ×9–12). It was the first trend with the
organic factor live, and the second session's watch caught it within 12 minutes:

| 21:30–21:51 UTC | Face Cream products per list | in slot 1 | their impressions | clicks | purchases |
|---|---|---|---|---|---|
| v31, v33 (carousel models × lift) | 0.20 | 1 % of lists | 358 | 0 | 0 |
| v32, v36 (× organic factor) | 1.63 – 1.79 | 13 – 15 % of lists | 2,936 | 2 | 0 |

The other products of those same lists were clicked 0.8 % of the time (3.2 % in slot 1): the organic arms were
giving a sixth of their slots to products nobody clicked, and their lists with three or more of them sold
0.44 per 100 against 2.95 for their lists with none. For Game Consoles (11 % of the store's purchases while
it trended) the carousel models had shown 1.2–1.4 trending products per list and they sold ×8.3: the lift is
right, and it limits itself — eight times a tiny probability is still tiny, and v9 leaves those products
out. The organic model is what broke. It learned which product a shopper goes on to buy *among the
candidates the rules retrieve on an ordinary day*; Face Cream products are candidates only because the lift
puts them there, and on products it was never asked about its answer means nothing. Reproduced offline on
120 of the day's requests with a made-up ×10 on Face Cream: 0.24 trending products per list for v9 + lift,
3.05 for v9 × organic + lift, 0.02 for v9 × organic without the trend.

The fix (`reco.recommend.level_trending`, live at 21:51 UTC, 21 minutes after the trend began): while a
trend runs, a trending product takes the organic factor of the products the carousel models score about as
high — the median of the ten ranked just above it and the ten just below, among those not trending — so
the organic model has no say on it and it keeps the place the carousel models and the lift give it. Offline
the same test gives 0.17 per list; live, after the swap, 0.24 (v32) and 0.08 (v36) against 0.21 (v31) and
0.20 (v33), none in slot 1. A big trend is still used: with a made-up ×8.8 on Game Consoles, 2.1 products
per list against 2.5 for v9 + lift. For the night's reading the organic arms count from 21:52 UTC.

Two things to keep from it. A model is only as good as the candidates it was trained on, and a multiplier
that changes the candidates changes the question. And an arm must be watched in every regime it will meet:
the organic arm had been ahead for an hour (+0.30, 1.9 standard errors) on minutes without a trend.

## 22. The organic model as a second stage: it orders the ten better than the models that picked them

The numbers of §20 already said it and we had read past it: on the ten products of a list, the organic
model **alone** puts the purchased one first more often (21.3 %) than v9 (17.8 %) or v9 × organic (20.4 %).
A model that never saw a carousel orders v9's ten better than v9 does. After §21 that is worth more than it
looked: the full organic arm (v32) applies the factor to the best 300 candidates and so changes 3 of the 10
products of a list, and nothing offline can say what the three newcomers are worth — they were never shown.
Reordering the ten is exactly what the held-out lists measure, and it cannot bring a product in.

In purchases, with a position-based estimate (a purchase made in slot k counts attention(new slot) /
attention(k); attention per slot from the old carousel's log: 1.00, 0.56, 0.41, 0.32, 0.26, 0.23, 0.21, 0.18,
0.16, 0.15; the order actually shown scores exactly the purchases counted). Held-out lists since 16:14 UTC,
neither model had seen them: 38,627 lists, 2,864 clicks, 904 purchases.

| The ten shown, ordered by | Clicks | Purchases | Known shoppers | New shoppers |
|---|---|---|---|---|
| v9 | 2,870 | 893 | 523 | 370 |
| v9 × organic ^ 0.5 | +3.4 % | +3.0 % | +2.1 % | +4.3 % |
| **v9 × organic** | +4.5 % | **+4.7 %** (pair by pair: +41.6 ± 14.2 purchases, 2.9 standard errors) | +4.3 % | +5.1 % |
| v9 × organic ^ 2 | +5.1 % | +5.0 % (± 2.1) | +5.7 % | +3.9 % |
| organic alone | +6.9 % | +4.7 % (± 3.0) | +5.8 % | +3.1 % |

**How much depends on how fast attention falls down the list**, and that is not known exactly. With the
old log's curve the reorder is worth +4.7 %. With the curve v9's own click model implies when the same
product is moved down the list (1.00, 0.68, 0.48, 0.40, 0.37, 0.34, 0.32, 0.30, 0.29, 0.29 — flatter: the old
carousel also put its better products first, so its raw clicks per slot overstate the fall) it is +2.5 % ±
1.1; with a curve steeper than the log's, +11 %. Positive under all of them, and power 1 is the robust dose:
"organic alone" goes from −0.9 % to +24 % with the curve, power 2 from +1.8 % to +15 %. The second session
measured today's curve on the same lists, v9's score held equal: 1.00, 0.60, 0.48, 0.45, 0.42, 0.36, 0.33,
0.33, 0.28, 0.27 from clicks — v9's curve, not the old log's (slots 2–10 get 1.4 times the attention the
old log gives them). So the honest reading is the lower one, about +2.5 %.

The same lists as a choice — which of the ten was chosen, given log(v9's prediction at its slot) and
log(organic factor) — give the organic factor a coefficient of 0.34 ± 0.04 on clicks and 0.59 ± 0.07 on
purchases, next to 0.81 and 0.82 for v9: 9 and 8 standard errors, by far the strongest information outside
v9 found all day (the best of §21 was 4.5). The fitted power on top of v9 is 0.4 for clicks and 0.7 for
purchases; power 1, as in v32, is within what the estimates above can tell apart. A flat-ish attention curve
also says that which ten are shown matters about as much as their order: that is v32's bet, and v37 against
v32 is the test.

The arm is one parameter (`pool` in `reco.recommend`: how many of the carousel models' best candidates the organic factor
may reorder; 10 = they pick the ten). On 150 of the day's requests it shows the same ten products as v9 in
all 150 lists, a different first product in 33 %, and costs 2 ms more than v9 (the organic model scores 10
rows instead of 300: 51 ms per list against 49, and 95 for v32).

**Live since 22:23 UTC:**

| Arm | Traffic | What | Question |
|---|---|---|---|
| `skore_money_v31` | 30 % | v9 + trend lift | the version to beat |
| `skore_money_v37` | 20 % | v9 + lift picks the ten, v9 × organic orders them | against v31: the order alone, the same ten products |
| `skore_money_v32` | 30 % | v9 × organic over the best 300, + lift | against v37: what the organic factor brings in from outside the ten |
| `skore_money_v36` | 20 % | v32 + products added during the event ×1.5 for known shoppers | against v32: the lift for new products (§21) |

v37 took the place of v33 (v9b, v9's features retrained on all of Saturday): over its first hour it was level
with v9 (2.18 against 2.17 on 1,800 requests), as both offline judges had said. More of the same day's
feedback neither helped nor hurt.

**The cost in time.** With the organic model on the best 300 candidates of half the traffic, ranking took
100 ms per request instead of 63 and p95 of the answers went from 1.8 to 2.1 s over the evening (p99 2.9 s;
the two assistant sessions working on the same laptop added to it). On 120 requests the best 100 candidates
give the same list as the best 300 in 115 and the same first three products in 119, in 68 ms instead of
108: v32 and v36 ask about 100 since 22:41 UTC. v37 asks about ten and costs nothing — against v32 it
shares the first product in 98 % of lists and the first three in 89 %; what differs is the lower slots.

**A product just added waits 20 minutes** (`NEW_PRODUCT_WAIT`, every arm, live since 22:34 UTC). Found by
the second session reading clicks by slot: in the store a new product sells from its first minute, in the
carousel it is not clicked for its first twenty. Four batches (14:00, 18:00 and 22:00 UTC served from their
first minute): 1 click in 1,954 impressions where the ranker expected 12; from 20 to 40 minutes 9 clicks for
7 expected, later 1.2 to 1.6 times the other products at the same slots. The lists carried one in 11 % of
cases (23 % with the lift for new products), around slot 5. Worth little — a couple of purchases per batch
— and free: until it is 20 minutes old a product is treated like one out of stock. Tested on the day's
requests around the 18:00 batch: none of its products in 200 lists before 18:20, in 59 of 200 after 18:25.

Left for a retrain, not for tonight: an abandoned cart carted once is worth a fifth less than v9 thinks
(§21). Scoring it ×0.8 would move the reciprocal rank of the purchase from 0.384 to 0.390, but the live
state does not count carts per product, and a counter added to the state the night before the final is a
risk the gain does not pay for.

## 23. First read of the night: the organic order during a trend, and the arms as two questions crossed

**The read, 22:25 to 00:40 UTC** (`scripts/arms.py`, the organisers' metric; standard errors as in §15):

| Arm | Requests | Purchases / 100 requests | Cold | Warm | EUR / request |
|---|---|---|---|---|---|
| `v31` v9 + lift | 7,272 | 2.389 | 2.970 | 1.986 | 1.342 |
| `v37` v9 × organic orders v9's ten | 4,843 | 2.345 | 3.029 | 1.906 | 1.174 |
| `v32` v9 × organic over the best 100 | 7,229 | 2.301 | 3.015 | 1.824 | 1.122 |
| `v36` v32 + new products ×1.5 | 4,937 | 2.446 | 3.096 | 2.011 | 1.258 |

The three organic arms together read 2.356 against 2.389 for v31: level (−0.4 standard errors). Outside the
trend they are level one by one (105 minutes: 2.268, 2.272, 2.243, 2.284 in the order of the table). Inside
it they are not.

**The Vitamins trend, 23:30 to 00:15 UTC** (read by the second session): the largest of the day, ×7.8 the
subcategory's usual share and 11 % of all the store's purchases while it lasted (about 105 purchases per 5
minutes against 13 usual); the detector was on it from 23:30:43 to 00:16:47 UTC. All four arms showed the same
number of trending products (1.6 to 2.0 per list: the flaw of §21 is gone), but not in the same place:

| Arm | Lists with a trending product in slot 1 | Its share of the clicks in the lists that hold one | The share its slots predict | Purchases / 100 requests in the trend |
|---|---|---|---|---|
| `v31` | 21.9 % | 50.6 % | 54.3 % (−0.7 se: placed right) | 2.702 |
| `v37` | 18.5 % | 51.6 % | 37.9 % (+2.3 se) | 2.427 (−1.3 se against v31) |
| `v32` | 15.6 % | 54.3 % | 44.1 % (+1.7 se) | 2.532 (−0.9 se) |
| `v36` | 16.1 % | 50.9 % | 45.4 % | 2.880 (+0.9 se) |

In the organic arms the trending product sat lower than the clicks it drew: on warm requests v32 read 0.41
below v31 (−2.3 se) and v37 0.32 below (−1.6 se). One trend, so not a result by itself — but the cause is
in the code, not in the noise. §21 had given a trending product a neutral organic factor (the median of
the products ranked next to it), on the grounds that the organic model has never been asked about one. **A
neutral factor is not a neutral rank**: the other products still move on their own factors, and the ones
that come out first are the ones with the highest factor, so a product with a middling one loses the first
slots to them. Replayed on 200 of the day's requests with a made-up trend of the same size:

| Trending product in slot 1 | v9 + lift | Organic order, neutral factor (until 00:46 UTC) | Organic order, rank held (since) |
|---|---|---|---|
| organic factor orders the ten | 26.5 % of lists | 15.0 % | 26.5 % |
| organic factor over the best 100 | 26.5 % | 13.0 % | 26.5 % |

So the rule is now the one §21 meant (`hold_trending` in `reco/recommend.py`): **a trending product keeps
the rank v9 and the lift give it, and the organic factor orders only the other products among the slots
left.** v9 + lift places a trending product right (table above, and ×8.3 measured against ×8.6 estimated in
§16), and that is all we know about it. In the replay every trending product is in v9's slot in 200 of 200
lists; outside a trend nothing changes.

**The money per request is not the organic factor preferring cheap products.** The three organic arms earned
1.12 to 1.26 EUR per request against 1.34. From the per-answer log of the same hours, the product each arm
put first cost 36.4 (v31), 38.0 (v37), 35.1 (v32) and 36.9 EUR (v36), ± 0.8 to 0.9, and the ten together 40.2,
40.0, 38.2 and 39.2: the same shelf. Whatever the gap is, it is not the price of what is shown; it stays on
the list of things to read in the morning, because money is the tie-breaker.

**The arms since 00:46 UTC: two questions crossed**, 25 % of the traffic each.

| | v9's order | v9 × organic orders v9's ten |
|---|---|---|
| **as it is** | `skore_money_v31` | `skore_money_v39` |
| **products added during the event ×1.5 for known shoppers** | `skore_money_v38` | `skore_money_v40` |

Each question is read on all the traffic, half on each side, instead of a fifth against a third: "the
organic order" is (v39 + v40) against (v31 + v38), "new ×1.5" is (v38 + v40) against (v31 + v39). What was
closed, and why:

- **The organic factor choosing among the best 100** (v32, v36). In four hours it never read above v31
  (2.301 against 2.389 since 22:25 UTC, −0.8 se), it costs 20 ms per answer, and it is the one variant
  nothing offline can vouch for: the products it brings into a list were never shown. The order of v9's
  ten is the part that was measured (§22), so that is the part that stays in the experiment.
- **v36 as the only arm with the ×1.5.** v36 against v32 (+0.145, +1.2 se) is the one live sign for the
  ×1.5 of §21, and it was tied to an arm we are closing. It now has two arms without the organic model.

**What a night can tell.** From 00:46 to 07:30 UTC each side of a question gets about 36,000 requests: a
standard error of 0.05 purchases per 100 requests on the difference, so 2 standard errors are 0.10, about
4 % of what we sell. The offline estimates are below that (+2.5 % for the organic order; less for the ×1.5,
which touches few lists). The night can therefore show harm, and it can show a gain larger than we expect;
it cannot confirm a gain of 2.5 %. The rule for the final stays the one of the proven version: v31 serves
it unless a side is 2 standard errors above over the whole night and not below in trend minutes
([`docs/final-round.md`](final-round.md)).

**What each change is worth, on the same scale.** The three candidates that passed the control of §21 (v9's
own prediction held equal), sized the same way: v9 picks the ten, the candidate orders them, purchases
counted with the position-based estimate of §22 under the attention curve v9 implies (in brackets, under
the one measured on today's lists). Held-out lists since 17:00 UTC: 30,891 lists, 724 purchases.

| The ten ordered by | Lists it can change | Purchases in those lists | Purchases overall |
|---|---|---|---|
| v9 × organic (§22, lists since 16:14 UTC) | all | | **+2.5 % ± 1.1** |
| v9, products added during the event ×1.5 for known shoppers | 52 % of known shoppers' lists | +1.9 % ± 1.4 (+1.3 ± 1.4) | +0.6 % ± 0.5 (+0.5 ± 0.5) |
| v9 × e^(0.2 z), z = co-purchase with the shopper's abandoned carts, new shoppers only | 63 % of new shoppers' lists | +1.6 % ± 1.4 (+2.6 ± 1.4) | +0.6 % ± 0.5 (+1.0 ± 0.5) |

The third is the one signal of §21 that is not in any arm, raised again by the second session when the
teams behind us drew level outside trends (01:10 UTC: first by 0.08 on the hour, by 0.005 on the half
hour). It stays out, for what it is worth and for what it needs:

- It is worth what the ×1.5 is worth, a quarter of the organic order, and only when the shopper has had
  the time to fill a cart. The 63 % above are shoppers 7 to 11 hours into the event. In the first two
  hours of Saturday (measured by the second session on `shop.requests` against the shopper's earlier
  `add_to_cart` events) 6 %, 17 %, 26 % and 32 % of the new shoppers' requests, by half hour, came after a
  cart: a fifth. If the final starts from nothing that is about +0.15 % of the purchases; if its stream
  carries on from the practice round, the +0.6 %.
- For known shoppers it loses purchases (−1.2 % ± 1.1 at the same dose, −4.4 % ± 1.7 at e^(0.5 z)): v9
  already reads their carts better than a co-purchase count does. It would have to be switched by the kind
  of shopper.
- It needs "bought by the same shoppers" for every pair of products: 5,000 × 5,000 numbers from the 60-day
  history in the server's state, keyed on product ids, so empty for every product added during the event —
  the one kind of thing the rest of the system avoids (features are counts, shares and matches, never
  an id), added to the serving path the night before the final.

**Putting the two estimates of a change together.** A night cannot confirm +2.5 % (above), and held-out
lists cannot see what a live list does to the next request. Each is one estimate with its error, so they
are combined, each weighted by its precision (1 / error²), and a change goes into the final when (a) the
night does not contradict it — its side is not below the other over the whole night, nor more than one
standard error below in the minutes with a trend — and (b) the combined estimate is 2 standard errors
above zero. With a night worth ± 2.1 % on each question, that reads:

| Change | Held-out lists | Goes into the final if the night reads |
|---|---|---|
| the organic order (v39) | +2.5 % ± 1.1 | at or above the other side: then the two together are +2.0 % ± 1.0 or better |
| new products ×1.5 (v38) | +0.6 % ± 0.5 | 2 standard errors above the other side by itself: the held-out lists alone do not carry it |

A reading "at or above" is a weak test — with no effect at all it comes out half of the time — so it is
never the evidence: the held-out lists are, and the night is asked only whether it contradicts them. If
the humans prefer the proven version whatever the reading, that is v31, and nothing is lost that we had.

**The next trend, with the rank held (Leashes, 01:30 to 02:15 UTC; read by the second session).** As large
as the largest of Saturday: the subcategory went from 1.1 % to 11.4 % of the store's purchases (×10.3). The
organic arms now place the trending product where v9 does: in slot 1 in 20.9 % of their lists against
21.9 % (in Vitamins 18.5 % against 21.9 %). Inside the trend the organic order read −0.11 (−0.7 se) and new
×1.5 +0.15 (+1.0 se); over the night so far (00:50 to 02:15 UTC, 7,600 requests on each side) −0.07 (−0.7
se) and 0.00. Nothing either way yet. Two things to keep:

- **The dose of the lift is right at the margin.** Half of the lists held a trending product, 4.3 of them
  on average, and those lists sold less than the others (1.75 purchases per 100 against 2.82 in v31). That
  is which requests they are, not what the lift did to them. Inside those lists the trending products took
  44.1 % of the clicks where their slots predict 42.5 % (Vitamins: 50.6 % against 54.3 %): slot for slot
  they did as well as the shopper's own best candidates, which v9 ranks above the ones the trending
  products pushed out. Were the lift twice too strong, they would take about 27 %. The lists that fill
  with trending products are the ones of shoppers with weak signals of their own, where every product
  draws three quarters of the clicks its slot usually gets. What would reopen it: that share falling
  clearly under the slot prediction in another trend (the case for lift ^ 0.5, which ran as v35).
- **The trend is no longer ours alone.** Inside it we read 2.340 against 2.285 and 2.280 for the next two
  teams (team_14, team_03; every request counted, the ones a team did not answer included): +0.055, against
  +0.017 in the 45 minutes before, where Game Consoles and Vitamins had given +0.10 to +0.33. Every team
  rises inside a trend (a ranker that reads the recent views picks it up by itself); we rise more.
  (team_14 read 1.77 before this trend because it answered about half of the requests, between two
  versions, not because its ranker was worse.) Two teams differ by 0.10 over 45 minutes by chance, so it
  is one reading, but outside trends the nearest teams are level with us since about 01:00 UTC.

**The third trend of the night (Sneakers, 03:30 to 04:15 UTC; read by the second session).** From 0.42 %
to 6.24 % of the store's purchases (×14.8), found 57 seconds in.

- **The dose, again on the prediction.** Inside the lists that hold a trending product it took 31.2 % of
  the clicks where its slots predict 31.0 %: 1.01 (Leashes 1.04, Vitamins 0.93). The exponent stays at 1.
- **What the lift is worth on the board: about 0.08 while a trend runs.** We rose by 0.14 inside the trend
  (2.212 to 2.357) and the teams that answer every request by 0.04 to 0.08; in Leashes 0.19 against 0.06
  to 0.15. The gap to the next team went from +0.06 before to +0.13 inside (Leashes: +0.02 to +0.055).
- **The organic order in the minutes with a trend** (Leashes and Sneakers, 8,100 requests on each side):
  −0.13 (−1.3 se), with cold −0.44 and warm +0.11; over the whole night to 04:15 UTC −0.07 (−1.0 se). As it
  stands the rule gives v31. How much chance there is in a cold reading over 90 minutes: v31 and v38 give
  a new shopper the very same list and read 3.34 and 2.88.
- **The organic arms showed a trending product in slot 1 a little less often in both trends** (18.8 %
  against 20.0 %, and 20.9 % against 21.9 %). It is not the code. The two rankers' carousel models are
  the same files; a replay of 300 of the day's requests with a made-up Sneakers trend leaves every
  trending product in its slot in 300 of 300 lists; and comparing lists that hold the same number of
  trending products the difference over the two trends is −1.1 points (−1.3 se). The number of trending
  products per list, which no ordering can change, differs as much between arms (1.39 to 1.50): it is who
  fell in each arm.

**How the two questions ended (05:33 UTC).** On the window in which the four arms ran side by side
(00:45 to 05:30 UTC), the organisers' metric:

| Arm | Requests | Purchases per 100 | Cold | Warm | EUR per request | Against v31 |
|---|---|---|---|---|---|---|
| v31: v9 + trend lift | 12,742 | 2.299 | 2.915 | 1.851 | 1.121 | |
| v38: new products ×1.5 | 12,937 | 2.238 | 2.733 | 1.874 | 1.108 | −0.06 (−0.8 se) |
| v39: the organic order | 12,718 | 2.199 | 2.701 | 1.837 | 1.154 | −0.10 (−1.2 se) |
| v40: both | 12,729 | 2.144 | 2.622 | 1.810 | 1.055 | −0.15 (−1.9 se) |

As two questions, half of the traffic on each side: the organic order −0.10 (−1.7 se; cold −0.16, warm
−0.04) on 25,447 requests against 25,679; new products ×1.5 −0.06 (−1.0 se; cold −0.13, warm 0.00) on
25,666 against 25,460. Neither could reach its bar by the morning any more: to be level over the night the
organic order would have had to read +0.21 over the two hours left (+2.5 se: under 1 % if it does nothing,
about 3 % if it is worth the +2.5 % of the held-out lists), and new ×1.5 needed +2 se by itself. At
05:25 UTC the second session raised the alarm agreed with Javier beforehand: twice running we were not first
on the 30-minute board (team_03 2.240, team_14 2.235, us 2.226). The best version of each of the three
nearest teams read 2.26 to 2.33, which is what v31 reads, and half of our traffic was on the side that read
2.06 in that half hour. The answer was the one written down in advance: the traffic to our best arm by the
longest clean window. No arm was kept for a comparison, because no question was left that the remaining
hours could answer. **v31 alone since 05:33:51 UTC**; six answers were lost in the handover. It is also the
version for the final.

**What the night says about the held-out estimate.** The organic order was worth +2.5 % ± 1.1 on held-out
lists (§22) and read −4.3 % ± 2.5 live: 2.5 standard errors apart. Judging a new order on lists that were
logged under another one assumes that a product keeps its appeal whatever sits around it, and that the
attention curve of our click model is the simulator's; the live arms test the thing itself. The estimate
was good for choosing what to try and wrong about the size, and when the two disagree the live arms
decide, as they did for v16 against v9 (§15). It is why the night was only asked whether it contradicted
the held-out lists. It did.

**A trend too small for the detector (Watches, 05:30 UTC).** The subcategory was 0.07 % of the store's views
and 0.03 % of its purchases, six products that sell; inside the trend 0.54 % and 0.74 % (views ×7.4,
purchases ×31 to ×40). That is about 19 views a minute, and the detector asks for 40 in its view window,
which is two whole minutes plus the one in progress. Right after each minute mark the window is back to two
minutes, holds fewer than 40, and the trend goes off until the new minute fills: 37 s, 3 s and 33 s in its
first six minutes. Replayed second by second on the whole stream (4.5 million views and purchases, the ten
trends the store has had): the detector stayed on 100 % of the time after finding the trend in six of them,
98 to 99 % in two, 93.7 % in Cutting Boards and 57 % in the first twelve minutes of Watches. It found the
six larger ones 50 to 61 s in and the four smaller ones 121 to 143 s in. Holding a trend for 60 s after the
last second it passed the gates would give 100 % in nine and 87.5 % in Watches, and would keep the lift on
a minute longer after every trend ends. Not deployed: a trend on 0.7 % of the store's purchases moves a
fraction of a purchase in a final, the gain averaged over the ten trends is about 4 % of a trend's lift,
and it is a change to the detector three hours before the final. If the final brings small trends, it is
one constant and a dozen lines in `reco/features.py`. A swap in the middle of this trend lost nothing: the
new server had found Watches from the journal before it took over.

## 24. Reliability, third look: twelve seconds without Wi-Fi (15 Nov, 03:16 UTC)

The one burst of lost answers of the night: 34 requests in a row (ts 03:16:41.8 to 03:16:52.7; a feedback
row is stamped 4.2 s after its request, so they show in the feedback of 03:16:46 to 03:16:57) came back
`missing`. Every other team answered 100 % of those minutes: it was ours. The monitor
(`scripts/netmon.py`, one line per second), the server's log and the list of what it ranked, side by
side, on RawTree's clock (the laptop's runs 0.4 s ahead, measured):

| UTC | The link, seen by the monitor | The server |
|---|---|---|
| 03:16:37.5 | ping to the router 26–40 ms (usually 4–5) | answering as usual |
| 03:16:40.5 | a new connection to RawTree fails (2 s) | still answering on the connections it has; the last request it ranks has ts 03:16:41.700 |
| 03:16:42 | silent | the four polls on their way time out after 2.5 s, three inserts after 2 s, every refresh after 5 s |
| 03:16:43.5 | the router does not answer pings | `no poll came back for 2 s`, six times |
| 03:16:53.5 | a connection gets through, after waiting 6.8 s; clean from here | |
| 03:16:55.4 | | the first poll comes back, 10.6 s after it was sent: the requests of the last 2.8 s are ranked in one go |
| 03:16:56.3 | | their answers land: 3.6 s after the oldest (too late), 3.2 s after the next (taken), in time for the rest |
| 03:16:59.5 | ping 127–247 ms for five seconds, nothing lost | answers take 1.3–2.1 s for five seconds, then 1.0–1.4 s again |

**What a different loop would have saved: about three requests of the 34.** With the link silent for 11.5 s,
some 31 were out of reach for any loop: a request has to be read, ranked and answered within 3 s of its ts.
The server's first poll came back 1.9 s after the monitor's first good connection instead of the 0.6 s a
fresh connection and a query take. The poll that came back had lasted 10.6 s with a time limit of 2.5 s:
the limit covers connecting and each read, not looking the host's address up, which a new connection does
first (the record is short-lived: it read 12 s and 1 s of life left when we looked) and which waits on
Windows' own retries, seconds apart. Three requests are 0.014 % of a final. Closing that gap means changing
how every poll and every insert connects, the night before, with no way to rehearse a real outage on the
machine that is serving. **The loop stays as it is.** It did what it is built for: no thread died, nothing
was restarted (the supervisor only starts a server that has exited: a restart, a minute or two of loading,
would have cost more than the drop), and the answers resumed by themselves.

**What it was.** Windows logged nothing in those minutes: no disconnection, no roaming, no new address
(WLAN-AutoConfig, System, DHCP and network-status logs all empty). The link was 5 GHz, channel 48 (not a
radar channel), 802.11ac at 867 Mbps, signal 88 %; the laptop was on mains, the adapter set to maximum
performance, no sleep, no restart pending. So the radio stayed associated and nothing crossed it for twelve
seconds: the router or the air, not a setting on the laptop. In the 10.6 hours the monitor has logged
(Saturday 16:57 UTC to Sunday 03:37 UTC) it is the only outage; three single pings lost on Saturday evening
cost nothing. Since Saturday 20:00 UTC, 89 of 83,320 requests went unanswered (99.89 % answered): these 34
are the largest single piece.

**For the final.** One such drop in the two hours is 0.16 % of the answers, and from one event in 10.6
hours the chance of one is about one in six: small in expectation. What a cable removes is the tail, a
drop that lasts a minute. The laptop has a wired port (gigabit), unused so far. Two things to know:

- **A connection stays on the adapter it was opened on.** The server holds twelve connections to RawTree,
  all through the Wi-Fi (`scripts/link.ps1` shows them). With a cable plugged in, Windows sends new
  connections through it by itself, but the server opens new ones only when it has to. So the cable goes in
  *before* the swap that sets the final's version, and `scripts/link.ps1` confirms it afterwards.
- **The Wi-Fi stays on, as the spare.** If the cable fails, the server's connections fail with it and are
  opened again over the Wi-Fi within seconds.
