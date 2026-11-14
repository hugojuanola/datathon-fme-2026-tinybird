# Three peaks, one model: where the 3 / 3 / 2 readings came from, and what can be combined (14 Nov, 21:00 CET)

**In one line**: the readings of about 3 purchases per 100 requests, 3 or more on cold requests and about
2 EUR per request were single quarter-hours of small arms, mostly chance. What is real and can be put in one
set-up: the `v16` ranker for cold requests, the `v9` ranker for warm ones, and price as a tie-breaker (inside
a list the shopper's choice does not depend on price). That gives about 2.2 overall and 2.9 on cold requests.
Three overall is not reachable by combining what we have: it needs warm requests to go from 1.8 to 3.

## 1. Where the three numbers came from

The board per `model_version`, read quarter-hour by quarter-hour since 09:00 UTC (120 arm-readings with at
least 60 requests). The highest:

| Quarter-hour (UTC) | Version | Requests | Conversion | Cold | EUR per request | Reference (conv / cold / EUR) |
|---|---|---|---|---|---|---|
| 15:30 | `v9` | 185 | **2.98** | 3.52 | **2.01** | 2.00 / 2.02 / 0.92 |
| 15:30 | `v8c` | 211 | 2.91 | 4.60 | 1.52 | 2.00 / 2.02 / 0.92 |
| 19:00 | `v23` | 173 | 2.82 | 3.05 | 1.81 | 2.09 / 2.04 / 0.93 |
| 18:45 | `v25` | 122 | 2.81 | **4.64** | **2.74** | 1.96 / 1.83 / 0.88 |
| 19:00 | `v28` | 498 | 2.71 | 3.80 | 1.40 | 2.09 / 2.04 / 0.93 |

The three peaks are not three different models: `v9` showed all three at once, in one quarter-hour, on 185
requests. The same model, measured for longer:

| `v9` | Requests | Conversion | Cold | EUR per request |
|---|---|---|---|---|
| 15:30-15:45 UTC | 185 | 2.98 | 3.52 | 2.01 |
| 15:30-16:00 UTC | 1,007 | 2.55 | 3.11 | 1.32 |
| its first hour (the record in `best_model.md`) | 2,822 | 2.37 | | |
| tonight, as `v21` + `v22`, 17:45-19:20 UTC | 4,146 | 2.08 | 2.50 | 1.07 |

Counts over the 120 readings: none at 3.0 conversion or above, 33 at 3.0 cold or above, 3 at 1.9 EUR or above.

## 2. How much of a quarter-hour reading is the model

The eight overnight arms, six quarter-hours each (17:45-19:15 UTC), on the organisers' expected metric:

| | One arm, from one quarter-hour to the next (sd) | Between the eight arms' averages (sd) | Single readings, lowest to highest |
|---|---|---|---|
| Conversion | 0.35 | 0.05 | 1.29 to 2.82 |
| Cold | 0.74 | 0.25 | 1.40 to 4.64 |
| EUR per request | 0.34 | 0.09 | 0.53 to 2.74 |

The same arm moves seven times more between two quarter-hours than the arms differ from each other. The
quarter-hour decides the reading (which requests fell in the arm), not the version. Revenue is the worst:
the dearest 10 % of the purchases bring 54 % of the revenue, so on realised sales a random 185 requests give
anything from 0.08 to 3.33 EUR per request (5th to 95th percentile), and 4,000 requests still 0.72 to 1.42.

## 3. What is real, by piece

**Cold requests: `v16`.** Pooled over the night so far, 2.89 (`v16`) and 2.90 (`v16w`) against 2.50 (`v9`)
and 2.61 (`v9w`); reference 1.69. About two standard errors (note of 20:30).

**Warm requests: `v9`.** 1.80 against 1.66 for `v16`; reference 2.01. Also about two standard errors.

**Revenue: price is neutral inside a list.** `python realtime_analyisi_leaderboard/price_and_revenue.py
--since "2026-11-14 15:30:00"`, 43,266 requests we served, 3,119 clicks, 962 purchases:

| Price band (EUR) | Share of impressions | Purchases per 1,000 impressions, slots weighted alike | EUR per 1,000 impressions |
|---|---|---|---|
| under 15 | 39.5 % | 2.13 | 17 |
| 15-30 | 31.7 % | 1.97 | 42 |
| 30-60 | 13.3 % | 2.45 | 109 |
| 60-120 | 8.5 % | 2.45 | 219 |
| over 120 | 6.9 % | 3.21 | 856 |

Read alone, this table says dear products sell *more* per impression. That is the mix of requests: we show
dear products mostly in requests that convert anyway. The test that stays inside each list — given that the
shopper clicked or bought one of these ten, is it a dear one more often than its slot predicts? — says no:

| Events | n | Over 60 EUR: actual / predicted by slot | Over 120 EUR: actual / predicted by slot |
|---|---|---|---|
| Clicks | 3,119 | 16.2 % / 17.4 % (-1.7 se) | 8.0 % / 8.6 % (-1.2 se) |
| Purchases | 962 | 17.9 % / 19.2 % (-1.1 se) | 9.5 % / 9.9 % (-0.4 se) |

The same holds for new and known shoppers and for both ranker families. So the rankers are not biased for
or against dear products (nothing to fix for conversion), and a dear product in a slot sells as often as a
cheap one would there. Between two candidates the ranker scores alike, the dearer one brings more revenue
at no cost in purchases.

What limits it is the slot curve. Slot 1 holds 45 % of the purchases (9.87 per 1,000 impressions, against
2.87 in slots 2-3, 1.23 in 4-6 and 0.68 in 7-10), so moving a dearer but less likely product up costs
purchases fast. Today slot 1 holds slightly cheaper products than the rest of the list (mean 36 against 41
EUR): popularity leans cheap.

## 4. The combined set-up

| Piece | Choice | Evidence | Status |
|---|---|---|---|
| Cold requests | ranker `v16` (or `v16w`, level with it) | night arms, cold column | being measured; decide on Sunday with more than 0.15 of lead |
| Warm requests | ranker `v9` | night arms, warm column | same |
| Trend | lift at ^0.75 | level with no lift while no trend runs; the Saturday trends were x8-12 | keep on |
| Price | tie-breaker only: score x (price / median price) ^ a, with a small `a` | inside-list neutrality above | to test offline: largest `a` in {0.05, 0.1, 0.2} that keeps expected purchases within 0.5 % |

The routing `"v16|v9"` uses two models that already exist and a code path that is already live. Expected,
from the two halves measured tonight: 0.375 x 2.90 + 0.625 x 1.80 = **2.21** overall (reference 1.89) and
**2.9** on cold requests (reference 1.69), against 2.08 to 2.14 for the eight arms. Each request is answered
by exactly one ranker, so the halves add up without a new experiment.

Revenue only breaks ties in the final: conversion is 50 points, cold start 10, reliability 10. A price
exponent that costs purchases is a bad trade; one that does not is free.

## 5. What it does not reach

Three purchases per 100 requests overall needs 0.375 x 2.9 + 0.625 x W = 3, so W = 3.06 on warm requests.
We are at 1.80 there and the reference at 2.01. Warm requests are 62 % of the traffic and the only place
where the reference is ahead of us; that is where the next real gain is, not in combining versions. The
candidate lever is in the 20:15 note (inside the subcategories a known shopper buys in, purchases spread far
below the best sellers while our lists follow popularity).

## Checks against the three lenses

- **Generalisation**: the routing is by kind of request, not by shopper or product; `v16` and `v9` carry no
  ids. The price finding is about the simulator's choice rule, which the final keeps.
- **Reference**: its revenue per purchase is 46 EUR, ours 46 to 57 by arm; its lead is on warm requests only.
- **Technique**: ranking by probability x value ^ a is the standard way to trade conversion for revenue in
  a recommender; with the slot curve this steep the exponent has to be small.

## Update, 21:45 CET — `v21` at 3.7 / 6.3 / 1.95 on the board

Javier read `skore_money_v21` at 3.70 conversion, 6.28 cold and 1.95 EUR per request on the board's last
15 minutes. Over 19:25-19:40 UTC the API gives it 3.31 / 5.80 / 2.03 on 141 requests, 52 of them cold.

- **`v21` is not a new model.** It is `v9` everywhere with the trend lift off, on 6 % of the traffic.
  `v22` is the same ranker on 19 %: in the same quarter-hour it reads 2.71 / 4.22 / 1.05 on 508 requests.
- **Longer windows, `v21` against `v22`**: last hour 2.55 and 2.35; last two hours 2.31 and 2.19;
  17:45-19:20 UTC 2.08 and 2.08.
- **Every arm is high in that quarter-hour** (2.19 to 3.55), and so is the reference: 2.19 with 2.39 on cold
  requests, against 1.89 and 1.69 over the night. A trend started at 19:30 UTC: Game Consoles is the top
  organic subcategory from 19:30 on, and the detector logged it at 19:30:41 with lift 3.6.
- **52 cold requests are very few.** One request where the simulator gives a 50 % chance of a purchase adds
  almost a whole point to their mean.

First read of the trend lift during a real trend, 19:25-19:40 UTC: arms without the lift 2.92 on 642
requests, arms with it 2.58 on 2,058. About one standard error; to be read on the whole trend
(19:30-20:15 UTC) with `python scripts/arms.py 19:30 20:15`.
