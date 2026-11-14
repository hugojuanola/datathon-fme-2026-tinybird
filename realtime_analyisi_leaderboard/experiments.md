# Every test we ran: what it gave, what it cost, what we did with it

The ledger of the practice round (Datathon FME 2026, team `team_06`). One row per test: a version served
live, a signal tried on the data, a fix for reliability. For each one the question, the measurement, the
advantage, the disadvantage and the verdict. The first section is rewritten every hour by
[`experiments.py`](experiments.py); the tables below it are edited by hand when a test closes.

Numbers are the organisers' expected purchases per 100 requests unless a row says otherwise; "margin" is
against the organisers' reference recommender over the same minutes; "se" is a standard error taken from
the spread measured between arms that ran the same code (6.5 per request overall, 8.8 on cold requests,
4.75 on warm ones). Times are CET (UTC + 1).

Verdicts: **KEPT** = part of what serves now · **LIVE** = being measured tonight · **DROPPED** = measured,
no gain or worse · **WITHDRAWN** = a claim of ours that did not hold a better test · **NOT USED** = real
but not worth or not possible to deploy · **FIXED** = a fault found and repaired.

## 1. Where we stand now

<!-- live:start -->
_Refreshed 00:13 CET on 15 Nov 2026 (board to 00:10 CET). Expected purchases per 100 requests, the organisers' own number._

### The gap to the next team

| Window | Place | Us | Next team | Gap | Gap on cold requests | Reference | Answered on time |
|---|---|---|---|---|---|---|---|
| 15 min | 1 | 2.475 | team_03 2.369 | +0.106 | +0.193 | 2.127 | 99.9 % |
| 30 min | 1 | 2.358 | team_03 2.274 | +0.084 | +0.118 | 2.019 | 99.9 % |
| 60 min | 1 | 2.311 | team_03 2.220 | +0.091 | +0.104 | 2.013 | 99.8 % |
| 180 min | 1 | 2.240 | team_03 2.166 | +0.074 | +0.068 | 1.974 | 99.9 % |

Official hourly score, hour in progress (previous full hour): team_06 64.9 (63.0), team_03 60.0 (60.3), team_40 56.4 (49.8), team_37 56.3 (38.9), team_22 55.5 (55.2).

### The arms now serving, over the same minutes (since 23:25 CET, when the last one started)

**All minutes** — reference 2.029 (cold 1.890, warm 2.122)

| Arm | What it is | Requests | Overall | Over the reference | Cold | Warm | Against `v31`: overall, cold, warm (standard errors) |
|---|---|---|---|---|---|---|---|
| `v31` | v9 + trend lift (the proven one) | 2,444 | 2.387 | +0.358 | 2.920 | 2.015 |  |
| `v32` | v9 x organic factor | 2,393 | 2.345 | +0.316 | 3.019 | 1.894 | -0.04 (-0.2), +0.10 (+0.2), -0.12 (-0.7) |
| `v36` | v9 x organic, new products x1.5 for known shoppers | 1,677 | 2.257 | +0.228 | 2.847 | 1.851 | -0.13 (-0.6), -0.07 (-0.2), -0.16 (-0.8) |
| `v37` | v9 picks the ten, the organic factor only orders them | 1,571 | 2.278 | +0.249 | 3.058 | 1.796 | -0.11 (-0.5), +0.14 (+0.3), -0.22 (-1.1) |

**Minutes without a trend** — reference 2.029 (cold 1.890, warm 2.122)

| Arm | What it is | Requests | Overall | Over the reference | Cold | Warm | Against `v31`: overall, cold, warm (standard errors) |
|---|---|---|---|---|---|---|---|
| `v31` | v9 + trend lift (the proven one) | 2,444 | 2.387 | +0.358 | 2.920 | 2.015 |  |
| `v32` | v9 x organic factor | 2,393 | 2.345 | +0.316 | 3.019 | 1.894 | -0.04 (-0.2), +0.10 (+0.2), -0.12 (-0.7) |
| `v36` | v9 x organic, new products x1.5 for known shoppers | 1,677 | 2.257 | +0.228 | 2.847 | 1.851 | -0.13 (-0.6), -0.07 (-0.2), -0.16 (-0.8) |
| `v37` | v9 picks the ten, the organic factor only orders them | 1,571 | 2.278 | +0.249 | 3.058 | 1.796 | -0.11 (-0.5), +0.14 (+0.3), -0.22 (-1.1) |

**Minutes of a trend**: nothing yet (a piece needs 15 minutes).

### The same for the arms that were already serving at 22:55 CET, since then

**All minutes** — reference 1.980 (cold 1.869, warm 2.053)

| Arm | What it is | Requests | Overall | Over the reference | Cold | Warm | Against `v31`: overall, cold, warm (standard errors) |
|---|---|---|---|---|---|---|---|
| `v31` | v9 + trend lift (the proven one) | 4,065 | 2.281 | +0.301 | 2.839 | 1.902 |  |
| `v32` | v9 x organic factor | 3,970 | 2.268 | +0.288 | 2.908 | 1.835 | -0.01 (-0.1), +0.07 (+0.2), -0.07 (-0.5) |
| `v36` | v9 x organic, new products x1.5 for known shoppers | 2,749 | 2.216 | +0.236 | 2.849 | 1.809 | -0.06 (-0.4), +0.01 (+0.0), -0.09 (-0.6) |

**Minutes without a trend** — reference 2.007 (cold 1.940, warm 2.051)

| Arm | What it is | Requests | Overall | Over the reference | Cold | Warm | Against `v31`: overall, cold, warm (standard errors) |
|---|---|---|---|---|---|---|---|
| `v31` | v9 + trend lift (the proven one) | 3,013 | 2.360 | +0.353 | 3.024 | 1.894 |  |
| `v32` | v9 x organic factor | 2,913 | 2.275 | +0.268 | 2.918 | 1.845 | -0.09 (-0.5), -0.11 (-0.3), -0.05 (-0.3) |
| `v36` | v9 x organic, new products x1.5 for known shoppers | 2,017 | 2.276 | +0.269 | 2.977 | 1.794 | -0.08 (-0.5), -0.05 (-0.1), -0.10 (-0.6) |

**Minutes of a trend** — reference 1.906 (cold 1.663, warm 2.058)

| Arm | What it is | Requests | Overall | Over the reference | Cold | Warm | Against `v31`: overall, cold, warm (standard errors) |
|---|---|---|---|---|---|---|---|
| `v31` | v9 + trend lift (the proven one) | 1,052 | 2.054 | +0.148 | 2.266 | 1.924 |  |
| `v32` | v9 x organic factor | 1,057 | 2.249 | +0.343 | 2.878 | 1.809 | +0.19 (+0.7), +0.61 (+1.0), -0.12 (-0.4) |
| `v36` | v9 x organic, new products x1.5 for known shoppers | 732 | 2.052 | +0.146 | 2.438 | 1.844 | -0.00 (-0.0), +0.17 (+0.2), -0.08 (-0.3) |

A difference counts from two standard errors and 0.15; a quarter of an hour of a small arm is a lottery.
<!-- live:end -->

## 2. The versions we served

In the order they went live. Detail and evidence: [`best_model.md`](../best_model.md) (every version, its
minutes and its margin) and `docs/findings.md` (§9 to §22).

| Test | When | The question | What came out | Advantage | Disadvantage | Verdict |
|---|---|---|---|---|---|---|
| Starter baseline: all-time best sellers | 12:30-13:00 | Where do we start? | 0.75 against 2.21 for the reference (-1.46) on 1,395 requests | always valid, instant | the same ten products for everybody | KEPT only as the last-resort list when everything else fails |
| Rules: popularity x measured lifts (`v2a` to `v4b`, `skore_money_v4`) | 13:00-15:00 | Do the lifts measured in the history (category of the last view x5, abandoned cart x10, bought in the subcategory x5-10) carry to the live carousel? | 1.42 to 1.57 (-0.48 to -0.62) on about 2,000 to 4,600 requests each | explainable line by line, no training, answers a new shopper or a new product from the first second | the lifts multiply but do not interact; half a point below the reference; nothing on known shoppers | KEPT as the retrieval stage (the 1,000 candidates) and as the fallback if the ranker fails |
| First learned ranker, `skore_money_v5`: P(click) x P(purchase given a click) over the rules' candidates | 14:30-17:00 | Does a model learn the interactions the rules miss? | 1.81 (-0.31) on 12,910 requests; in the A/B against the rules 2.50 % realised against 1.50 % | +0.4 over the rules; known shoppers' lists move into the subcategories they buy in (62 % of impressions against 34 %) | still under the reference on known shoppers | superseded by v7 to v9 |
| Exploration arms (`v5_explore`, `v8_explore`): the top of the list shuffled | 14:30-17:00 | Can we afford unbiased feedback to train and to judge with? | 1.21 and 1.81 on their share of the traffic (-0.94, -0.29); about -0.22 on the team's board while they ran | the only unbiased data of the day; what the held-out tests of the evening stand on | costs conversion on every request it takes | DROPPED for the final: a practice-round tool |
| `v6`: v5 + the brands a shopper bought, new-product and discount features | 15:30-16:30 | Is the brand history (x2.2-2.5 in the raw data) a lever? | 1.70 (-0.42) on 1,383 requests; its lists held no more bought-brand products than v5's | none found | the brand says nothing once the attributes are in; more features, more noise | DROPPED (the brand features left in v8) |
| `v7`: + the attributes named in the description (20 phrases, two per product) | 16:00-16:30 | Shoppers buy by attributes: is that what the reference knows and we do not? | 2.42 (+0.34) on 1,432 requests: from 0.3 under the reference to 0.3 over it | the largest step of the day; works for a product never seen before, because every product has a description | none measured | KEPT |
| `v8`, `v8c`: v7 without the brand, refitted on all the data | 16:00-17:00 | Does the simpler model lose anything? | 2.35 (+0.25) on 2,665; `v8c` +0.28 | fewer features, same level | none | superseded by v9 |
| **`v9`**: attributes + carts by subcategory, learned from the old log and the day's feedback | 16:30-17:30, then as `v21`/`v22` 18:45-21:30 and `v31` since 21:35 | Is this the level we can hold? | 2.37 (+0.35) on 2,822 in its first hour; +0.375 on 7,186 over the evening; first of every comparison it was in | the best proven version; no ids of any kind, so nothing in it is tied to today's shoppers or products; the simplest | under the reference on warm requests (about 2.0 against 2.1); a shade behind on cold requests to versions that lean on the stream | **KEPT: the default for the final** |
| `v9w`: v9 with the day's feedback weighted x20 | 17:00-18:00, then `v23`/`v24` | Does the stream teach more than the old log for cold requests? | first hour +0.34 with 3.21 on cold requests; over the evening 2.66 on cold against 2.96 for v9 (-1.2 se) | none that repeated | the cold gain of the first hour was chance; worse on warm requests | DROPPED |
| `v10`, `v9d`, `v12`, `v13`: variants of v9 | 17:00-18:30 | Small changes of features and weights | +0.14 to +0.36 on 800 to 1,700 requests each: all inside the noise of v9 | none | nothing to choose between them on so few requests | DROPPED |
| Routing by kind of request (`v11`, `v23`/`v24`, `v27`/`v28`): one ranker for cold requests, another for the rest | 17:30-21:30 | Does each kind of request have its own best ranker? | `v11` +0.08 on 4,400; `v9w` cold + `v9` warm +0.232 on 7,218 against +0.375 for v9 everywhere (-1.3 se) | the two halves can be read apart, which is how the warm-ranker result was found | three measurements against the x20 weight; two models to keep in step | DROPPED |
| `v16`, `v16w`: retrained on all of Saturday, 57 features with the popularity rank inside the subcategory and real prices | 18:45-21:30 | Does more of today's data, and the rank inside the subcategory, help? | `v16` +0.235 on 7,268, `v16w` cold + `v16` warm +0.313 on 7,290; on warm requests 1.78 against 1.97 for v9 (2.7 se); level on cold | the newest data | loses where 62 % of the traffic is; offline it had looked level, so the offline judge only screens | DROPPED |
| Trend lift at ^0.75 (`v22`, `v24`, `v26`, `v28` against the odd versions) | 18:45-21:30, one trend inside | Is it worth multiplying a trending subcategory by its lift? | -0.03 (0.4 se) over the evening; +0.03 ± 0.20 inside the Game Consoles trend. Then measured directly by the model session: a trend product sells 8.3 times v9's prediction | follows the store within a minute; in the one large trend our gap to the next team was 0.13 to 0.33 | a lift on a very small subcategory gives nothing; depends on the detector | KEPT, at full strength (^1.0) in every arm since 21:35 |
| `v34` (no lift), `v35` (lift ^0.5) against `v31` (lift ^1.0) | 21:35-22:32 | The dose of the lift | not measured: no trend ran in that hour before the arms were replaced | - | - | closed without an answer; the direct measurement (x8.3) decided |
| `v33` = v9b: v9's features retrained on all of Saturday | 21:35-23:23 | Is v16's deficit the newer data or the extra features? | +0.13 over v9 (0.8 se) before the trend, -0.02 after: level | none | none | DROPPED at 23:23 (level with v9: the deficit of v16 was its extra features) |
| **`v32`**: v9 x an organic factor, a third model of what shoppers go on to buy in the store | since 21:35; counts from 22:55 | Does the store teach something the carousel's own feedback does not? | 2.440 against 2.162 for v9 over 21:35-22:30 (+0.28, +1.9 se), 3.22 against 2.72 on cold requests; then the flaw below; since 23:25, next to the four arms of now, -0.04 against v9 (-0.2 se) on 2,393 requests in 45 minutes | the only candidate left with a sizeable gain; strongest on cold requests | slower (ranking 83 ms against 63, after it was cut to the best 100 candidates at 23:41); had a flaw in trends; three of its ten products come from outside v9's ten and nothing offline can value them; not yet two standard errors | **LIVE**: decided in the morning |
| The organic factor inside a trend | 22:30-22:51 | (found, not planned) | `v32` and `v36` put Face Cream in 57 % of their lists, slot 1 in 14-16 %: 1,820 impressions, 2 clicks, no purchase. The organic model had never seen such products as candidates | - | twenty minutes of half the traffic | FIXED at 22:51 (`level_trending`): after it 0.20 to 0.30 trend products per list in every arm, and they sell like their neighbours |
| `v36`: `v32` with products added during the event x1.5 for known shoppers | since 22:32; counts from 22:55 | New products sell more than v9 expects to known shoppers (observed / predicted purchases 1.37 on held-out lists): does a lift collect it? | too early: -0.13 against v9 (-0.6 se) on 1,677 requests since 23:25 | measured with v9's prediction held equal; keyed on "added during the event", not on today's products | it pushed products in their first 20 minutes, when nobody clicks them, until they were held out at 23:34 (section 3) | **LIVE** |
| `v37`: v9 picks the ten, the organic factor only orders them | since 23:23 | Is the organic gain in the order or in the products it brings in? | offline, on 38,627 held-out lists: reordering v9's ten is worth about +2.5 % purchases (± 1.1) under today's attention curve, +4.7 % under the old log's steeper one; as a choice model the organic factor is the strongest signal found outside v9 (0.59 ± 0.07 on purchases next to v9's own prediction). Live: -0.11 against v9 (-0.5 se) on 1,571 requests in 45 minutes, nothing yet | the ten products are v9's, so the risk is bounded; almost no extra latency (ten rows, where `v32` scores 300); the one use of the organic model that could be valued offline | gives up whatever the outside products bring; the offline gain is small | **LIVE**; preferred over `v32` if both pass |

## 3. Signals and ideas tried on the data

| Idea | How it was tested | What came out | Advantage if used | Disadvantage, or why not | Verdict |
|---|---|---|---|---|---|
| The session: page, recent views, carts | history and live feedback | `home` pages are 20 % of requests and 2 % of purchases; the category of the last view x5; an abandoned cart x10 | the strongest signals there are, and a new shopper has them too | none | KEPT since the first version |
| The slot | history and live feedback | slot 1 gets 6.7 times the clicks of slot 10 and holds 44 % of our purchases; v9 is calibrated by slot | says the whole game is the first product | - | KEPT: the ranker scores every product as if in slot 1 and sorts |
| Satiation | live feedback | a product the shopper already bought sells 0.01-0.03 % of the time on the carousel (not so in the store) | frees slots for products that can sell | - | KEPT as a hard rule |
| The subcategories a shopper has bought in | carousel feedback, slot-adjusted | x6 to x14; holds with the purchases of the day alone (x5.8 new shoppers, x3.5 known) | what closed most of the gap on known shoppers | - | KEPT (in every ranker since v5) |
| Attributes of the description | organic purchases, then the carousel | x10 between low and high affinity for known shoppers; x2.3 and x5.6 when a product shares one or two attributes with the last view | the largest single step (v7); needs no history of the product | - | KEPT |
| Brand history | carousel feedback, then `v6` live | x2.2-2.5 raw, nothing once the attributes are in | - | redundant | DROPPED |
| Special lists for `home` pages; discounting products already shown; products viewed long ago | checks on the feedback | home lists were already history-based; repeated products sell more, not less; viewed-long-ago products sell no better than never-seen ones | - | each rested on a table that did not survive a second look | WITHDRAWN |
| Popularity inside a bought subcategory weighs too much | what known shoppers buy next in the store: their purchases spread to ranks 11-30 while we show the top 3 | became the rank features of `v16`, which lost on warm requests | - | the store's next purchases are not the carousel's sales | DROPPED |
| Price | inside-the-list test; then with v9's prediction held equal on 38,629 lists | inside a list the choice does not depend on price; products on promotion read observed / predicted 1.06 ± 0.14; a price multiplier leaves the purchased product where it was at every strength | would have raised revenue per request for free | revenue only breaks ties; nothing to gain in purchases | DROPPED |
| Co-purchase ("who bought this also bought that"), with the history and with the recent views | slot-only control: x1.19 to x1.28, repeated on two windows. With v9's prediction held equal: x1.04 / x0.97 | v9 already has it through attributes and subcategories; reordering by it loses | the textbook signal, and no team's numbers show it | redundant for this simulator | WITHDRAWN (the first control was not enough: slot dummies are a screen, not a test) |
| Co-purchase with what a new shopper carted or bought today | v9's prediction held equal | x1.21 to x1.34 on purchases (4.4 se) | real | needs the shopper's carts and purchases of the same day, which a two-hour final barely has | NOT USED (written up in findings §21) |
| Products added during the event | v9's prediction held equal | known shoppers buy them 1.59 times v9's prediction (2.8 se); new shoppers as predicted | collects a real under-prediction; generalises to the final's own new products | small share of impressions | LIVE as `v36` |
| A just-added product, first 20 minutes | slots, three batches; then against v9's prediction by the model session | 1 click on 1,188 impressions where 7.2 were expected by slot and about 12 by v9's own prediction; from minute 20 on, x1.3 to x1.6 | free: the slot goes to a product that can be clicked, and the new-product lift no longer pushes dead products | worth about 0.03 for twenty minutes every four hours | KEPT: since 23:34 a product stays out of every arm's lists for its first 20 minutes, like one out of stock. To verify at the batches of 03:00 and 07:00 |
| Region and device | slot-only control | nothing for known shoppers, nothing for the device; for new shoppers x1.05 to x1.12 per sd | a little something for shoppers we know nothing about | small, and not tested against v9's prediction | NOT USED |
| Spreading a list (products of one subcategory take clicks from each other) | v9's prediction held equal, 30,891 lists | first / second / later product of a subcategory: 0.99 / 1.06 / 0.95 on clicks; a penalty on repeats never beats v9's order | - | the simulator adds products up; sorting by score is right | DROPPED |
| Recency of the purchases | v9's prediction held equal | no gradient from last week to two months ago (0.93 to 1.00) | - | nothing to add | DROPPED |
| Waiting a second longer for the shopper's next events | the stream around each request | about 100 events for 5,220 requests | - | nothing to wait for, and it would cost reliability | DROPPED |
| How big a trend is on the carousel | the model session, against v9's prediction for the same impressions | x8.3 on purchases, the same for shoppers looking elsewhere and at every slot | settles the strength of the lift without waiting for many trends | one large trend measured | KEPT (lift ^1.0) |
| What the shopper buys next in the store, as a fast offline judge | findings §19 | it ranked `v16` above `v9` (13.5 % against 13.1 % of next purchases in the list); live, v9 won on warm requests | answers in minutes | not the carousel: it screens ideas, it does not decide | KEPT as a screen only |
| How to judge an arm | arms running the same code | two identical arms differ by 0.12 after half an hour on the expected metric, and by a factor of two on realised purchases; a quarter-hour of a 6 % arm reads anywhere from 1.3 to 2.8 | keeps us from chasing noise: five alarms of the afternoon were this | slow: an answer takes hours | KEPT: the expected metric over hours, two standard errors and 0.15, never realised purchases |
| The store's calendar | `shop.catalog_updates` and the stream | a trend every 2 hours for 45 minutes, a promotion every 3 for 2 hours, 100 new products every 4 | tells which minutes of the final carry what, and lets the arms be read by regime | must not be written into the recommender: the final has new trends | KEPT as a way of reading |

## 4. Reliability

| What happened | When | What it cost | The fix | What the fix gave | Verdict |
|---|---|---|---|---|---|
| OneDrive uploading the Python environment and data files from inside the repository; a second process loading its state; a model scoring with every core | 14:14-14:31 and 14:58-15:01 | a quarter of the answers, three times | environment, data and logs outside the synced folder; offline scripts at low priority; a new version loads in standby | no repeat | FIXED |
| The server's console window closed by hand | 19:53-19:57 | 723 requests, four minutes | a windowless supervisor that restarts the server | nothing to close by mistake; survives the assistant app | FIXED at 20:11 |
| Long assistant sessions uploading megabytes per step over the home connection | afternoon | bursts of late answers; `on_time` 96.4 % against 99.8 % for the others | fewer, shorter steps; no session open during the final | 99.9-100 % since 21:00 | KEPT as a rule for the final |
| Replacing the server | every deploy | 2 to 6 requests per swap | `scripts/swap_server.ps1`: standby, self-test, hand-over | every swap of the evening went through with a handful of requests lost, never a gap | KEPT |
| The answers get slower since the organic model went in | since 21:35 | ranking 63 → 100 ms per request; latency of the answers, half hour by half hour from 21:00 to 23:36: p50 1.17 → 1.33 s, p95 1.78 → 2.31 s, p99 2.16 → 2.91 s; answers over 3 s from 1 to 12 per half hour. Nothing lost yet (`on_time` 99.8-99.9 %). The network is flat (router ping 5 ms, RawTree connect 110 ms): it is the process, and what else runs on the machine | at 23:41 the organic model went from the best 300 candidates to the best 100 (the same list in 115 of 120 requests, the same first product in all of them); no analysis runs on the serving machine for the rest of the night | ranking 100 → 83 ms; p95 back to 1.9-2.0 s; answers over 3 s from 15 to 2-9 per quarter of an hour | **FIXED** for now and watched every 15 minutes (`latency_history.csv`). Latency is the second thing the morning's choice looks at (p95 under 2 s): v9 alone and `v37` are cheap, `v32` and `v36` less so |

## 5. What it adds up to

- The steps that moved the board: the rules (0.75 → 1.45), a learned ranker (→ 1.81), the attributes
  (→ 2.4, from 0.3 under the reference to 0.35 over it). Everything after v9 has been inside ± 0.15 of it.
- Six ideas were closed tonight with v9's own prediction as the control (co-purchase, spreading a list,
  recency, waiting, price, region for known shoppers): for a given shopper and list, v9 has taken what these
  signals give.
- What can still move it: the organic factor (`v32`, `v37`), the new-product lift (`v36`), and how well a
  large trend is followed. The four nearest teams are within 0.05 to 0.08 of us outside a large trend.
- What can lose it: answers. Four minutes without answering cost as much as the whole of today's gap.
