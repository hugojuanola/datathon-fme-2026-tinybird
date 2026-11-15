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
_Refreshed 05:03 CET on 15 Nov 2026 (board to 05:00 CET). Expected purchases per 100 requests, the organisers' own number._

### The gap to the next team

| Window | Place | Us | Next team | Gap | Gap on cold requests | Reference | Answered on time |
|---|---|---|---|---|---|---|---|
| 15 min | 1 | 2.241 | team_14 2.126 | +0.115 | +0.203 | 1.832 | 100.0 % |
| 30 min | 1 | 2.362 | team_14 2.253 | +0.109 | +0.164 | 1.944 | 100.0 % |
| 60 min | 1 | 2.258 | team_37 2.152 | +0.106 | +0.146 | 1.912 | 99.7 % |
| 180 min | 1 | 2.257 | team_03 2.176 | +0.081 | +0.117 | 1.944 | 99.9 % |

Official hourly score, hour in progress (previous full hour): team_06 67.0 (63.9), team_03 59.2 (60.0), team_26 59.2 (57.4), team_37 58.0 (60.1), team_33 57.4 (57.6).

### The arms now serving, over the same minutes (since 01:50 CET, when the last one started)

**All minutes** — reference 1.935 (cold 1.679, warm 2.118)

| Arm | What it is | Requests | Overall | Over the reference | Cold | Warm | Against `v31`: overall, cold, warm (standard errors) |
|---|---|---|---|---|---|---|---|
| `v31` | v9 + trend lift (the proven one) | 8,508 | 2.298 | +0.363 | 2.900 | 1.867 |  |
| `v38` | v9 with products added during the event x1.5 for known shoppers | 8,637 | 2.247 | +0.312 | 2.740 | 1.889 | -0.05 (-0.5), -0.16 (-0.8), +0.02 (+0.2) |
| `v39` | v9 picks the ten, the organic factor orders them (a trending product keeps v9's slot) | 8,551 | 2.274 | +0.339 | 2.820 | 1.885 | -0.02 (-0.2), -0.08 (-0.4), +0.02 (+0.2) |
| `v40` | v39 with new products x1.5 for known shoppers | 8,467 | 2.165 | +0.229 | 2.537 | 1.908 | -0.13 (-1.3), -0.36 (-1.7), +0.04 (+0.4) |

- Pooled, the organic order (v39 + v40) against v9's order (v31 + v38): all -0.053 (-0.7 se), cold -0.138 (-0.9 se), warm +0.018 (+0.3 se); EUR per request 1.110 against 1.112; 17,018 against 17,145 requests.
- Pooled, new products x1.5 (v38 + v40) against none (v31 + v39): all -0.080 (-1.1 se), cold -0.219 (-1.5 se), warm +0.022 (+0.3 se); EUR per request 1.057 against 1.165; 17,104 against 17,059 requests.

**Minutes without a trend** — reference 1.927 (cold 1.684, warm 2.103)

| Arm | What it is | Requests | Overall | Over the reference | Cold | Warm | Against `v31`: overall, cold, warm (standard errors) |
|---|---|---|---|---|---|---|---|
| `v31` | v9 + trend lift (the proven one) | 5,125 | 2.224 | +0.296 | 2.608 | 1.945 |  |
| `v38` | v9 with products added during the event x1.5 for known shoppers | 5,267 | 2.162 | +0.235 | 2.635 | 1.820 | -0.06 (-0.5), +0.03 (+0.1), -0.13 (-1.0) |
| `v39` | v9 picks the ten, the organic factor orders them (a trending product keeps v9's slot) | 5,143 | 2.285 | +0.358 | 2.905 | 1.836 | +0.06 (+0.5), +0.30 (+1.1), -0.11 (-0.9) |
| `v40` | v39 with new products x1.5 for known shoppers | 5,129 | 2.045 | +0.118 | 2.396 | 1.790 | -0.18 (-1.4), -0.21 (-0.8), -0.16 (-1.3) |

- Pooled, the organic order (v39 + v40) against v9's order (v31 + v38): all -0.028 (-0.3 se), cold +0.029 (+0.2 se), warm -0.069 (-0.8 se); EUR per request 1.074 against 1.012; 10,272 against 10,392 requests.
- Pooled, new products x1.5 (v38 + v40) against none (v31 + v39): all -0.150 (-1.7 se), cold -0.239 (-1.3 se), warm -0.085 (-1.0 se); EUR per request 0.932 against 1.155; 10,396 against 10,268 requests.

**Minutes of a trend** — reference 1.948 (cold 1.671, warm 2.140)

| Arm | What it is | Requests | Overall | Over the reference | Cold | Warm | Against `v31`: overall, cold, warm (standard errors) |
|---|---|---|---|---|---|---|---|
| `v31` | v9 + trend lift (the proven one) | 3,383 | 2.411 | +0.463 | 3.350 | 1.749 |  |
| `v38` | v9 with products added during the event x1.5 for known shoppers | 3,370 | 2.380 | +0.432 | 2.902 | 1.998 | -0.03 (-0.2), -0.45 (-1.4), +0.25 (+1.6) |
| `v39` | v9 picks the ten, the organic factor orders them (a trending product keeps v9's slot) | 3,408 | 2.258 | +0.310 | 2.689 | 1.958 | -0.15 (-1.0), -0.66 (-2.0), +0.21 (+1.4) |
| `v40` | v39 with new products x1.5 for known shoppers | 3,338 | 2.349 | +0.401 | 2.769 | 2.080 | -0.06 (-0.4), -0.58 (-1.7), +0.33 (+2.2) |

- Pooled, the organic order (v39 + v40) against v9's order (v31 + v38): all -0.092 (-0.8 se), cold -0.396 (-1.7 se), warm +0.147 (+1.4 se); EUR per request 1.163 against 1.266; 6,746 against 6,753 requests.
- Pooled, new products x1.5 (v38 + v40) against none (v31 + v39): all +0.030 (+0.3 se), cold -0.181 (-0.8 se), warm +0.185 (+1.7 se); EUR per request 1.249 against 1.180; 6,708 against 6,791 requests.

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
| **`v32`**: v9 x an organic factor, a third model of what shoppers go on to buy in the store | since 21:35; counts from 22:55 | Does the store teach something the carousel's own feedback does not? | 2.440 against 2.162 for v9 over 21:35-22:30 (+0.28, +1.9 se), 3.22 against 2.72 on cold requests; then the flaw below; since 23:25, next to the four arms of now (read at 01:15): -0.10 against v9 (-0.8 se) on 5,875 requests in 110 minutes; inside the Vitamins trend -0.17 (-0.9 se); on warm requests -0.20 (-1.8 se) | the only candidate left with a sizeable gain; strongest on cold requests | slower (ranking 83 ms against 63, after it was cut to the best 100 candidates at 23:41); had a flaw in trends; three of its ten products come from outside v9's ten and nothing offline can value them; not yet two standard errors | **DROPPED** at 01:46: over 23:25-01:45 it read 2.304 against 2.409 for v9 on 7,484 requests (-1.0 se), never above v9 in four hours, 20 ms slower per answer, and 1.12 EUR per request against 1.36. What is kept of it is the order (`v39`) |
| The organic factor inside a trend | 22:30-22:51 | (found, not planned) | `v32` and `v36` put Face Cream in 57 % of their lists, slot 1 in 14-16 %: 1,820 impressions, 2 clicks, no purchase. The organic model had never seen such products as candidates | - | twenty minutes of half the traffic | FIXED at 22:51 (`level_trending`): after it 0.20 to 0.30 trend products per list in every arm, and they sell like their neighbours. Tightened at 01:46 (`hold_trending`): a trending product keeps the slot v9 gave it, after the Vitamins trend showed the organic arms still letting other products pass it. Held in the two trends since (Leashes, Sneakers): the four arms show a trend alike, and a replay of 300 requests by the model session gives every trending product the same slot with and without the organic order |
| `v36`: `v32` with products added during the event x1.5 for known shoppers | since 22:32; counts from 22:55 | New products sell more than v9 expects to known shoppers (observed / predicted purchases 1.37 on held-out lists): does a lift collect it? | read at 01:15: +0.05 against v9 (+0.4 se) on 4,039 requests in 110 minutes; inside the Vitamins trend +0.18 (+0.9 se). Nothing yet | measured with v9's prediction held equal; keyed on "added during the event", not on today's products | it pushed products in their first 20 minutes, when nobody clicks them, until they were held out at 23:34 (section 3) | closed at 01:46 with `v32`: +0.05 over v9 (+0.5 se) on 5,118 requests, and +0.16 over `v32` (+1.3 se), the only live sign for the lift. It continues without the organic model as `v38`, and with the organic order as `v40` |
| `v37`: v9 picks the ten, the organic factor only orders them | since 23:23 | Is the organic gain in the order or in the products it brings in? | offline, on 38,627 held-out lists: reordering v9's ten is worth about +2.5 % purchases (± 1.1) under today's attention curve, +4.7 % under the old log's steeper one; as a choice model the organic factor is the strongest signal found outside v9 (0.59 ± 0.07 on purchases next to v9's own prediction). Live, read at 01:15: -0.12 against v9 (-0.9 se) on 3,986 requests in 110 minutes; inside the Vitamins trend -0.28 (-1.3 se); on warm requests -0.20 (-1.6 se). Nothing yet, and no sign of the offline gain | the ten products are v9's, so the risk is bounded; almost no extra latency (ten rows, where `v32` scores 300); the one use of the organic model that could be valued offline | gives up whatever the outside products bring; the offline gain is small | closed at 01:46: -0.09 against v9 (-0.7 se) on 5,054 requests; inside the Vitamins trend it put the trending product first less often than v9 (18.5 % of lists against 21.9 %). It continues as `v39` with that fixed |
| `v39`: v9 picks the ten, the organic factor orders them, and a trending product keeps the slot v9 gave it | since 01:46 | Is the organic order worth it once it cannot move a trending product? | read at 05:03, pooled with `v40` against `v31` + `v38` on 17,018 requests against 17,145 (190 minutes, 75 of them inside a trend: Leashes and most of Sneakers): -0.05 overall (-0.7 se), -0.14 on cold requests (-0.9 se), +0.02 on warm ones; in the minutes of a trend -0.09 (-0.8 se), without one -0.03 (-0.3 se); `v39` against `v31` directly -0.02 (-0.2 se); 1.11 EUR per request on both sides. Level, a little under | the ten are v9's; ten rows for the organic model; inside a trend the placement is v9's | an offline gain of about +2.5 % only; the three organic arms before it sold 1.12 to 1.28 EUR per request against 1.36 for v9 | **LIVE** |
| `v38`: v9 with products added during the event x1.5 for known shoppers, no organic model | since 01:46 | Is the new-product lift worth it on its own? | read at 05:03, pooled with `v40` against `v31` + `v39` on 17,104 requests against 17,059: -0.08 overall (-1.1 se); +0.02 on warm requests (+0.3 se), where the lift acts, and -0.22 on cold ones (-1.5 se), where it mostly does not (a new shopper gets the same list on both sides, so that figure is how much cold swings by itself); in the minutes of a trend +0.03 (+0.3 se), without one -0.15 (-1.7 se); 1.06 EUR per request against 1.17. Nothing | measured against v9's prediction (x1.59 for known shoppers); costs nothing to run | a small share of the impressions, so a small effect to detect | **LIVE** until the morning, and **out of the final**: decided at 04:50 on 15 Nov, since it can no longer reach two standard errors above by 08:30 |
| `v40`: `v39` with the new-product lift | since 01:46 | The two together | read at 05:03: 2.165 against 2.298 for `v31` on 8,467 requests (-1.3 se), and -0.11 against the other three together (-1.3 se), the lowest of the four; it stays to cross the two questions and would be taken out at two standard errors below the others | the two questions are crossed, so each is read on all the traffic | - | **LIVE** |

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
| Co-purchase with what a new shopper carted or bought today | v9's prediction held equal | x1.21 to x1.34 on purchases (4.4 se) | real | needs the shopper's carts and purchases of the same day: in a two-hour event a fifth of the new shoppers' requests have them. Sized by the model session on the held-out lists: +0.15 % to +0.6 % of all purchases, for about two hours of work in the serving path | NOT USED (findings §21 and §23); the humans' call in the morning, not recommended |
| Products added during the event | v9's prediction held equal | known shoppers buy them 1.59 times v9's prediction (2.8 se); new shoppers as predicted | collects a real under-prediction; generalises to the final's own new products | small share of impressions | LIVE as `v38` and `v40` (first as `v36`, with the organic model) |
| A just-added product, first 20 minutes | slots, three batches; then against v9's prediction by the model session | 1 click on 1,188 impressions where 7.2 were expected by slot and about 12 by v9's own prediction; from minute 20 on, x1.3 to x1.6 | free: the slot goes to a product that can be clicked, and the new-product lift no longer pushes dead products | worth about 0.03 for twenty minutes every four hours | KEPT: since 23:34 a product stays out of every arm's lists for its first 20 minutes, like one out of stock. Checked at the batch of 03:00 CET on 15 Nov: the 100 products arrived on the dot, none was in the 3,600 lists of their first twenty minutes, and from the twentieth minute they were in 19 % of the lists (16 % in `v31` and `v39`, 21 and 23 % in the two arms with the new-product lift) |
| Region and device | slot-only control | nothing for known shoppers, nothing for the device; for new shoppers x1.05 to x1.12 per sd | a little something for shoppers we know nothing about | small, and not tested against v9's prediction | NOT USED |
| Spreading a list (products of one subcategory take clicks from each other) | v9's prediction held equal, 30,891 lists | first / second / later product of a subcategory: 0.99 / 1.06 / 0.95 on clicks; a penalty on repeats never beats v9's order | - | the simulator adds products up; sorting by score is right | DROPPED |
| Recency of the purchases | v9's prediction held equal | no gradient from last week to two months ago (0.93 to 1.00) | - | nothing to add | DROPPED |
| Waiting a second longer for the shopper's next events | the stream around each request | about 100 events for 5,220 requests | - | nothing to wait for, and it would cost reliability | DROPPED |
| How big a trend is on the carousel | the model session, against v9's prediction for the same impressions | x8.3 on purchases, the same for shoppers looking elsewhere and at every slot | settles the strength of the lift without waiting for many trends; in the next large trend (Vitamins, 00:30-01:15) the four arms showed it alike (1.5 to 1.8 products per list) and our gap to the next team was +0.10 to +0.19, against +0.06 to +0.09 in the hours without one; in the one after (Leashes, 02:30-03:15 on 15 Nov, x10 on purchases in the store) the arms showed it alike again (2.1 to 2.2 per list, slot 1 in 20 to 22 % of the lists) and the gap was only +0.06 (+0.02 in the 45 minutes before); in Sneakers (04:30-05:15, x14.8 in the store) it was +0.13 (+0.06 before). In both, the teams that answer every request rose by 0.04 to 0.15 inside the trend and we by 0.14 to 0.19: the lift is worth 0.08 to 0.09 while a trend runs | one large trend measured against v9's prediction; in Leashes the trending products sold 0.45 of what their slot neighbours sold across lists, though inside a list they took the share of the clicks their slots predict (44.1 % against 42.5 %; Vitamins 50.6 % against 54.3 %): slot for slot they do as well as the shopper's own best products, and the gap across lists is which requests they are (lists fill with trending products where the shopper's own signals are weak). Sneakers read 1.01 of the slots' prediction on 224 lists, 1.03 on 463 lists over the two trends: no case for a weaker lift (under 0.8 would have been one) | KEPT (lift ^1.0) |
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
| The laptop lost its link to the router for 11.5 seconds (the router ping and the connection to RawTree both failing in the log of `scripts/netmon.py`; the only such episode in the 10.6 hours the monitor has logged). Wi-Fi at 5 GHz with full signal, and Windows logged no disconnection: the radio stayed associated and nothing crossed it | 04:16:42-04:16:53 on 15 Nov | 34 requests left unanswered (request times 04:16:41.8 to 04:16:52.7): `on_time` 98.7 % for that quarter of an hour, 99.9 % over three hours. Every other team stayed at 100 %, so it was ours and not the platform | none in the code: the server caught each failure (3 inserts, 4 polls, the refreshes) and went on answering by itself, 1.9 s after the link came back. A request has 3 seconds, so 31 of the 34 were out of reach whatever the loop does; the other 3 would need every poll and insert to connect differently, not worth changing the night before (findings §24) | - | **OPEN for the final: the network cable.** The laptop has a wired port, unused; a connection stays on the adapter it was opened on, so the cable goes in before the swap that sets the final's version (`scripts/link.ps1` says which link the server uses). One such gap in the final's two hours is 0.16 % of its requests |

## 5. What it adds up to

- The steps that moved the board: the rules (0.75 → 1.45), a learned ranker (→ 1.81), the attributes
  (→ 2.4, from 0.3 under the reference to 0.35 over it). Everything after v9 has been inside ± 0.15 of it.
- Six ideas were closed tonight with v9's own prediction as the control (co-purchase, spreading a list,
  recency, waiting, price, region for known shoppers): for a given shopper and list, v9 has taken what these
  signals give.
- What can still move it: the organic order (`v39`, `v40`), the new-product lift (`v38`, `v40`), and how
  well a large trend is followed. By 02:00 CET on 15 Nov the nearest teams (team_17, team_14, team_03,
  team_42, team_37) have reached us outside a trend: the quarter-hour gap to the best of them was +0.03 to
  +0.13 until midnight, +0.10 to +0.21 inside the Vitamins trend, and -0.02 to +0.02 in the half hour after
  it. Their rankers read like ours (cold 3.1 to 3.2, warm 1.8 to 2.0). What we still have over them is the
  trend, 45 minutes in every 120; and in the Leashes trend (02:30-03:15 CET), as large in the store as
  Game Consoles, even that narrowed: we read 2.34 inside it against 2.29 and 2.28 for team_14 and team_03
  (+0.06, where the two large trends before gave +0.10 to +0.33; two teams over 45 minutes differ by 0.10
  by chance). In Sneakers (04:30-05:15) it was +0.13 again, against +0.06 in the 45 minutes before it.
- What can lose it: answers. Four minutes without answering cost as much as the whole of today's gap.
- How the version for the final is chosen (`docs/final-round.md`, set at 02:20 CET on 15 Nov). One night
  is worth about ± 2.1 % on each of the two questions the arms ask: it can show harm, it cannot confirm a
  gain of +2.5 %. So the night is only asked whether it contradicts the held-out lists. The organic order
  (+2.5 % ± 1.1 on those lists) goes into the final if its side (`v39` + `v40`) is not below the other
  (`v31` + `v38`) over the whole night, nor more than one standard error below in the minutes of a trend.
  The new-product lift (+0.6 % ± 0.5) only if its side (`v38` + `v40`) is two standard errors above the
  other by itself. Otherwise `v31`, the version every other arm is one step from. Latency is the second
  axis: p95 under 2 s.
- Where that choice stands at 05:19 CET, 205 minutes and two whole trends into the night's read: the
  organic order -0.07 (-1.0 se) over the whole night and -0.13 (-1.3 se) in the minutes of a trend
  (Leashes -0.11, Sneakers -0.15); `v39` against `v31` directly, -0.04 and -0.18. Both conditions of the
  rule fail as it stands, so it gives `v31`. The new-product lift is out of the final (it reads -0.07 and
  could no longer reach two standard errors above by 08:30; the model session, 04:50). Two trends and
  three hours of reading are still to come; p95 has been 1.77 to 1.90 s all night.
