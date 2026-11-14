# Skore Money · real-time recommendations on RawTree

**Datathon FME 2026 · 14–15 November · UPC Barcelona** — team `team_06` (Hugo Juanola, Javier Aranda).

Shoppers arrive at an online store about three times per second. For each one we have 3 seconds to choose
the 10 products they will see; a hidden model decides whether they click and buy. Everything — requests,
answers, feedback, 60 days of history — lives in [RawTree](https://rawtree.com), Tinybird's schema-free
analytics database. Our running system is the submission.

- Challenge page: <https://datathon.rawtree.dev> · Leaderboard: <https://datathon.rawtree.dev/leaderboard>
- Official starter kit: <https://github.com/rawtreedb/datathon-fme-2026>

**Where it stands** (practice round, Sat 14 Nov, 21:00 CET, the organisers' own numbers): first of the
teams on the hourly score, 61.7 against 40.6 for the next one. Over the evening about 2.2 expected
purchases per 100 requests against 1.8 for the next team, 2.0 for the organisers' reference recommender and
0.5 for the best-sellers baseline; on cold requests (new shoppers, new products) 2.8 against 1.7 for the
reference. What is still behind the reference: requests from known shoppers (1.8–2.0 against 2.0–2.2).

## How it works

```
 shop.requests ──► RETRIEVE ───────► RANK ──────────────► STORE MOVES ─────► HARD RULES ─────► team_06.submissions
 3 per second      rules:            two small models:    a subcategory      never bought         10 products,
                   popularity ×      P(click) ×           that is trending   before, in stock     ~1.0 s after the
                   measured lifts    P(purchase | click)  right now gets     right now, 10        request (3 s allowed)
                   → 1,000 products  over ~57 features    its lift           distinct

        ▲ the live state behind every step, rebuilt from the stream every second
 shop.events ──────────► each shopper's running profile (views, carts, purchases, tastes) · popularity · trends
 shop.catalog_updates ─► stock (every 5 minutes) · price changes · new products
 team_06.feedback ─────► what our carousel sold (nobody buys the same product twice) · training data
```

1. **Retrieve.** A product's score is its popularity times lifts we measured one by one: same category as
   the last view ×5, abandoned cart ×10, bought in that subcategory before ×5–10, attributes shared with
   the last view up to ×4.5. The best 1,000 go on (the same top 10 as ranking all 5,200 in 99.9 % of slots).
2. **Rank.** Two gradient-boosted models, multiplied: the chance of a click and the chance that a click ends
   in a purchase. Their features are counts, shares and matches — never a product or shopper id — so they
   work on a shopper or a product they have never seen. A third model can multiply their score: how
   likely this shopper is to go and buy this product in the store anyway, learned from what shoppers bought
   after 127,000 moments like this one (being tested live).
3. **Store moves.** The organic stream shows a trend minutes before our own feedback could: the detector
   reads views and purchases per subcategory every second and multiplies the scores of what is trending by
   how much it is trending. Live, it saw a trend 41 seconds after it started.
4. **Hard rules.** A product the shopper already bought is never shown again (it sells 0.01–0.03 % of the
   time), and one invalid id voids the whole answer, so stock is re-read around every 5-minute mark.

All of it runs in 45–90 ms per request, in one Python process: [`reco/`](reco/).

## What we found, and what each finding was worth

| Finding | Evidence | Section of [`docs/findings.md`](docs/findings.md) |
|---|---|---|
| The shopper's own signals dwarf everything else | An abandoned cart sells 10× an average product; the last view's category 5× | §1 |
| Popularity multiplies every other signal | A first version that filled the list tier by tier converted like the baseline; multiplying fixed it | §5 |
| The live simulator has satiation, the history does not | Already-bought products: 0.01–0.03 % per impression | §2 |
| **Shoppers buy by the attributes named in the description** | 20 phrases, two per product; a shopper's past attributes pick their next purchase inside a subcategory with AUC 0.69. Live: 1.8 → 2.4 purchases per 100 requests, the largest step we measured | §13, §15 |
| New shoppers are not blind | Their first views and carts of the session arrive in `shop.events` before the request; on cold requests we are at 2.76 against 1.73 for the reference | §3, §11 |
| **The store moves: one subcategory at a time sells ×8–12 for 45 minutes** | Five trends on 14 Nov, every product of the subcategory rising alike. Measured in our own carousel on the 9,000 impressions of one of them: ×8.3 on purchases, exactly what the detector estimated from the organic stream (×8.6) | §16 |
| What a shopper buys next is rarely what they are looking at | 10 % of requests are followed within 30 minutes by a purchase in the store: 75 % of them outside the category of the last view, 53 % in a subcategory the shopper had bought in — where it is the best of what they do not own yet, not the best seller | §19 |
| A model that never saw a carousel orders our carousel's purchases as well as ours | Trained only on those next purchases, as a factor on the ranker it moves the purchased product up among the 10 shown (reciprocal rank 0.38 → 0.41) | §20 |
| More weight on today's feedback, routing by kind of request, more features: no | Three ideas that looked right offline or for an hour and did not hold on thousands of live requests; one ranker serves everybody | §17, §20 |
| Nine more signals, each checked against what the ranker already predicts: one survives | Co-purchases, repetition, cart history, ids for brand and subcategory: all within a quarter of the ranker's own prediction. Holding only the slot equal would have "found" four of them. The one that left something: after a click a known shopper buys a product added during the event 37 % of the time, the ranker expected 26 % | §21 |
| A model must not be asked about what it has never seen | The first trend with the organic model live: it filled a sixth of the slots with a trending subcategory nobody clicked (2 clicks in 2,936 impressions). Caught by the watch in 12 minutes, fixed in 21: on trending products the organic model has no say | §21 |
| Price drops and new products are small next to that | A 19 % promotion sells about ×1.2; a new product takes its fair share from its first ten minutes | §16 |

## How we know: offline first, then live

- **Offline.** The training table is built by replaying the store in time order — 12 million organic events
  interleaved with the carousel requests — through the same `featurize()` the server calls, so a row never
  sees its future and training cannot drift from serving. Validation holds out the future: the last week of
  the log and the last quarter of our live feedback ([`offline/`](offline/), findings §6, §9, §14).
- **A fast judge in between.** What shoppers go on to buy after a request is free, unbiased by our own
  lists, and plentiful: [`offline/next_purchase.py`](offline/next_purchase.py) replays the stream and asks
  where each ranker had put that product. It orders the versions as the live metric did; an idea that does
  not move it is not worth an arm (findings §19).
- **Live.** Every version is an arm with its own `model_version`, split by a hash of the request id, and is
  judged on the organisers' own number: expected purchases under the hidden model, per version
  ([`scripts/arms.py`](scripts/arms.py)). We measured how noisy that is — three arms doing exactly the same
  read 1.92, 2.40 and 2.59 in one quarter of an hour — and only act on hours of traffic or on effects well
  beyond the noise (findings §15). When the offline judges and the live arms disagreed (v16 against v9 on
  known shoppers), the live arms decided.

| Version | What changed | Expected purchases per 100 requests |
|---|---|---|
| baseline | all-time best sellers | 0.6 |
| v4 | rules: popularity × lifts | 1.45 |
| v5 | first learned ranker on top of the rules | 1.81 |
| v7–v10 | + description attributes, new products, carts by subcategory | 2.3–2.4 |
| reference | the organisers' recommender | 2.06 |
| v9 + trend lift | + products of a trending subcategory multiplied by the detector's lift | being measured over the night (findings §20) |
| v9 × organic | + what shoppers go on to buy in the store | being measured over the night |
| v9 × organic, new products ×1.5 | + products added during the event lifted for known shoppers | being measured over the night (findings §21) |

## Learning from the stream

| How fast | What |
|---|---|
| Within a second | A shopper's profile after each view, cart and purchase · stock · prices · new products (described by their attributes from the first second) · which subcategory is trending and by how much |
| Within minutes | Popularity of every product, with the exposure a new product really had |
| Within hours | The rankers, retrained on our own feedback (live rows weighted over the old log) · the organic model, on what shoppers bought after our requests · exploration arms during practice, to have unbiased feedback to train and judge with (§12) |

For the final ("new shoppers, new products, new trends") nothing has to be switched on: the features carry
no ids, a profile builds itself from the stream, and the detector does not know the schedule of any trend.

## RawTree at work

- **The hot path** is two statements every 150 ms: read the requests of the last 4 seconds, insert the
  answers in batches (casts on `Dynamic` columns: findings §7, [`docs/rawtree.md`](docs/rawtree.md)).
- **Aggregations stay in the database.** [`offline/store_moves.py`](offline/store_moves.py) joins 12 million
  historical and 2 million live events with the catalogue and groups them per minute and subcategory,
  category and brand in a few seconds; [`queries/`](queries/) holds the health, variant and tier reports.
- **What we served and why** goes to `team_06.scratch` (the arm, the ranker, the reason for each of the 10
  products, what the trend detector saw), so a second session can join it with the feedback in SQL and
  explain an A/B, not just score it ([`realtime_analyisi_leaderboard/`](realtime_analyisi_leaderboard/README.md)).

## Reliability

Nothing waits for a single call: four staggered pollers, four senders, an insert that has not come back in
0.6 s is sent again on another connection. A new version loads in standby, answers real requests in a
self-test, and takes over without a gap ([`scripts/swap_server.ps1`](scripts/swap_server.ps1)). If the ranker fails the rules answer; if the rules fail, the best
sellers in stock. What costs answers is the home connection, not the code: findings §8,
[`scripts/netmon.py`](scripts/netmon.py), [`docs/final-round.md`](docs/final-round.md).

## Repository map

| Path | What |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Entry point for AI agents and newcomers: mission, rules, commands, current state |
| [`best_model.md`](best_model.md) | The best proven version, how to put it back, and the log of improvements |
| [`reco/`](reco/) | The recommender: `serve.py` (live loop), `state.py` (live state), `features.py` (every feature and the trend detector, shared by training and serving), `recommend.py` (retrieve, rank, store moves) |
| [`offline/`](offline/) | Data export, training table by replay, training and validation, start-up cache, `store_moves.py` |
| [`models/`](models/) | The trained rankers (LightGBM text files) |
| [`docs/findings.md`](docs/findings.md) | Every measurement behind the design, in the order we made them |
| [`docs/challenge.md`](docs/challenge.md), [`docs/data.md`](docs/data.md), [`docs/rawtree.md`](docs/rawtree.md) | Rules and scoring · data dictionary · RawTree cheat sheet |
| [`queries/`](queries/), [`scripts/`](scripts/) | Reusable SQL · `rt.py` (SQL from the shell), `arms.py` (A/B on the organisers' metric), `leaderboard.py`, `netmon.py` |
| [`avanced_data_analysis/`](avanced_data_analysis/README.md) | Exploratory analysis: what drives a purchase (figures, clustering, SHAP) |
| [`realtime_analyisi_leaderboard/`](realtime_analyisi_leaderboard/README.md) | Live watch of the leaderboard and of each arm |
| [`starter/`](starter/), [`docs/sources/`](docs/sources/README.md) | Official starter kit and material, unmodified |

## Quick start

```bash
cp .env.example .env     # fill in TEAM_ID and RAWTREE_API_KEY — never commit this file

python3 scripts/rt.py "SELECT count() FROM shop.requests"     # query RawTree
python3 scripts/arms.py                                       # our versions on the organisers' metric
python -m reco.serve --dry                                    # the recommender, printing instead of answering
```

Everything else (retraining, deploying without a gap, the final-round runbook): [`AGENTS.md`](AGENTS.md).

## Key dates (Barcelona time)

- **Sat 10:00 → Sun 10:00** — practice round, public leaderboard, does not count.
- **Sun 10:00 → 12:00** — final round, the only scored window.
- **Sun 14:00** — presentation and demo to the jury.
