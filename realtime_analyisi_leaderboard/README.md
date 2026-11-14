# Real-time analysis of the leaderboard and the live model

A watch on how our recommender is doing while it runs: where we stand against the other teams, the reference
and the baseline, and — from our own feedback — which shoppers we convert and which we do not. It is written
for whoever is training or tuning the model: read `latest.md` for the numbers and `notes/` for what they mean.

| File | What |
|---|---|
| [`latest.md`](latest.md) | The last tick: leaderboard top 5, who served our shoppers, conversion by model version and kind of shopper, the known-shopper lever. Regenerated every tick |
| [`history.csv`](history.csv) | One row per tick, to see the trend |
| [`notes/`](notes/) | One dated note per finding worth acting on, with the evidence and what to do |
| [`ab_mechanism.py`](ab_mechanism.py) | Reads an A/B: conversion per arm for new and known shoppers, and whether each arm pulls the measured levers (attribute affinity, attributes shared with the last view, bought subcategory). `--brand` adds the brand-versus-attributes table |
| [`best_model.py`](best_model.py) | Keeps the record of the best model: writes [`../best_model.md`](../best_model.md) with every version we served, its expected conversion and its margin over the reference in the same minutes |
| [`next_purchase.py`](next_purchase.py) | What shoppers buy organically right after we answer them, whether it was in our 10, and what pointed at the purchases we missed |
| [`price_and_revenue.py`](price_and_revenue.py) | What price does to a sale on our carousel: purchases and revenue per impression by price band and by slot, and whether a dear product is chosen less than its slot predicts inside a list |
| [`trend_read.py`](trend_read.py) | Reads a trend: how many products of the trending subcategory the arms with and without the trend lift put in their lists, in which slots, and what an impression of it brought against an impression of anything else |
| [`pool_arms.py`](pool_arms.py) | Pools the table of `scripts/arms.py` by groups of versions, overall and on cold and warm requests, with a standard error taken from the spread measured between arms that ran the same code |
| [`signal_scan.py`](signal_scan.py) | Which signals the lists leave unused: a conditional logit, inside each clicked list, of the chosen product on its slot and on properties of the product for that shopper (co-purchase with the history and with the recent views, attributes, new product, price...) |
| [`tick.py`](tick.py) | Produces `latest.md` and a row of `history.csv`. Read-only and light: leaderboard API + three `SELECT`s on the last minutes of the live tables; the 60-day purchase history comes from a local cache, not from a scan |
| [`queries/`](queries/) | The SQL behind the notes, runnable with `python scripts/rt.py -f <file>` |

Every analysis here is held to three questions: does it generalise to the final (new shoppers, products and
trends)? how does it compare with the reference? is there a better-founded technique for it in the literature?

```bash
python realtime_analyisi_leaderboard/tick.py                                  # last 30 minutes
python realtime_analyisi_leaderboard/tick.py --window 60
python realtime_analyisi_leaderboard/tick.py --since "2026-11-14 13:35:00"     # UTC, e.g. since a deploy
```

Run these with the project's Python environment. On the serving laptop it is
`C:/Users/javil/skore_money/venv/Scripts/python.exe`; it lives outside the repository because the
repository is in a OneDrive folder and syncing an environment saturates the uplink the live server needs.

## How to read a tick

- **`conv_15m`, `ref_conv_15m`, `missing_to_ref_15m`** — the same official board over the last 15 minutes
  instead of the last hour: where we are now, without the hour's inertia. Noisier (2,700 requests).
- **`pct_of_way_to_ref`** — how far our conversion is between the baseline (0) and the organisers' reference
  (100). The real score uses the unpublished oracle instead of the reference, so this is an upper bound on it.
- **`new_conv_pct` / `known_conv_pct`** — realised conversion of the requests *we* served, split by
  `is_new_user`. Realised purchases are noisy: with ≈1,700 new and ≈3,700 known requests in 30 minutes, one
  standard error is about 0.33 and 0.17 points. A difference smaller than twice that is not a difference.
- **`lever_impr_share_pct`** — of the impressions we gave known shoppers (products they had not bought), the
  share in a subcategory where they have bought before; `lever_buy_pct` and `no_lever_buy_pct` are the
  purchases per impression inside and outside it. If a new model uses the shopper's history, the share goes up.
- **`on_time`** on the leaderboard covers the last hour, so it takes an hour to forget a restart.
- **How much to trust a difference between two arms.** Realised purchases are a coin flip per request. On 14
  Nov, 17:53–18:11 CET, two arms that were the *same code path* (the trend detector never fired) showed 7
  against 19 purchases on about 790 known-shopper requests each — 2.4 "standard errors" — while the organisers'
  expected metric had them level (2.33 against 2.21). With several arms, two kinds of shopper and a look
  every few minutes, a difference of 2 to 2.5 standard errors on realised purchases turns up by chance all
  the time. Treat it as a question, not a finding: act only on 3 standard errors or more, on a difference
  that repeats in a second, separate window, or on the expected metric of the official board.

## Current reading

_Generated by the watch from the tick of 14 Nov 2026, 22:28 CET. Findings are in the notes below._

- **Margin to the reference, last hour**: 2.270 against 2.012 — **+0.257** (118% of the way from baseline to reference).
- **Margin to the reference, last 15 minutes**: 2.199 against 1.918 — **+0.281**.
- **Trend of the hourly board** (UTC, us / reference): 17:41 2.25 / 2.09 → 18:27 2.06 / 1.85 → 19:01 1.96 / 1.85 → 19:22 2.08 / 1.96 → 19:46 2.25 / 2.07 → 20:17 2.53 / 2.14 → 20:54 2.35 / 2.01 → 21:28 2.27 / 2.01.
- **Cold conversion**: 2.93 against 1.83. **Best rival**: team_03 at 2.22. **On time** (board, last hour): 99.9%. **Model on the board**: `skore_money_v31`.
- **Our own feedback, since 2026-11-14 20:35:00 UTC**: 99.9% of requests answered by us, p95 1895 ms; new shoppers 3.39% (2888 requests), known shoppers 1.68% (6725).
- **Architecture and model in the repository**: last commit on `reco/`, `offline/` or the findings: `268d959 — Organic factor asked only about the best 300 candidates (live 21:44 CET, same arms); findings 16 and 20, state (21:46)`. Everything there is committed; all of it is pushed.
- Per-arm numbers of this tick: [`latest.md`](latest.md). Every earlier tick: [`history.csv`](history.csv).

## Notes

| When (CET) | Finding |
|---|---|
| [14 Nov 23:00](notes/2026-11-14_2300_unused-signals.md) | **Three signals our lists do not use**: inside a list, the chosen product is more often than its slot explains one co-purchased with the shopper's history (x1.24 purchases per sd, known shoppers), one co-purchased with the recent views (x1.28, new shoppers) and one added during the event (x2 or more). The ranker has no collaborative feature. Holds on clicks, on purchases and in slots 3-10. How to use it: a multiplier arm tonight, features in the next retrain |
| [14 Nov 21:30](notes/2026-11-14_2215_trend-lift-first-read.md) | **The trend lift on a real trend, and the warm ranker**: Game Consoles sold ten times its usual from 19:30 to 20:15 UTC; the lift put a trend product in half the lists and they sold, but the total did not move (2.60 with the lift, 2.63 without; +0.03 ± 0.20): what the trend products gain the pushed-down products lose. Settled in the same window: on warm requests `v9` beats `v16`, 1.99 against 1.76 on 8,150 requests each (about three standard errors). Cold requests still level |
| [14 Nov 21:00](notes/2026-11-14_2100_three-peaks-one-model.md) | **Three peaks, one model**: the readings of about 3 conversion, 3+ cold and 2 EUR per request were single quarter-hours of small arms (the same arm moves seven times more between two quarter-hours than the arms differ). What is real and can be combined: `v16` for cold requests, `v9` for warm ones, price as a tie-breaker (inside a list the choice does not depend on price). About 2.2 overall and 2.9 cold; 3 overall needs warm requests at 3 |
| [14 Nov 20:30](notes/2026-11-14_2030_read-the-night-by-kind.md) | **Read the night by kind of request, not by arm**: after 95 minutes the eight arms are level overall (+0.19 to +0.25 over the reference), but v16 leads on cold requests (2.89 against 2.50) and v9 on warm ones (1.80 against 1.66); the best set-up for the final may be the cross, which needs no new experiment. Roughly two standard errors each: the night decides. Every arm is below the reference on warm requests |
| [14 Nov 20:15](notes/2026-11-14_2015_what-known-shoppers-buy-next.md) | **What known shoppers buy next**: we now show 12.5% of their next purchases (8.7% with the rules); inside the subcategories they buy in, purchases are spread far below the best sellers while our lists follow popularity; a third of the misses had both signals. Hypothesis to test offline: popularity should weigh less inside a bought subcategory |
| [14 Nov 17:10](notes/2026-11-14_1710_passed-the-reference.md) | **Above the reference on the hourly board**: 2.199 against 2.102; last 15 minutes 2.529 against 2.263. Conversion per arm since 16:41 CET (2.56% all together). Reliability: the remaining source of lost requests is the assistant sessions' own uploads — what to do for the final |
| [14 Nov 16:55](notes/2026-11-14_1655_at-the-reference-and-ab-verdict.md) | **At the reference**: 0.036 missing on the hourly board, above it over the last 15 minutes twice running. A/B verdict: the attribute models gain on new shoppers and are level with v5 on known ones; why (the products added at the margin sell less; lists leave the shopper's subcategories) |
| [14 Nov 16:25](notes/2026-11-14_1625_v7-live-mechanism.md) | **v7 is live and pulls the attribute lever** (low-affinity impressions 38% → 10%, attribute-sharing with the last view doubled); conversion not readable after ten minutes; v6 replaced; brand history is not a stand-in for attributes but adds nothing to the model |
| [14 Nov 16:12](notes/2026-11-14_1612_attributes-confirmed-on-carousel.md) | **Attributes confirmed on the live carousel**, adjusted for slot: 10× between low and high attribute affinity for known shoppers, inside and outside their subcategories; 2.3× / 5.6× for new shoppers when the product shares 1 / 2 attributes with the last view; 44% of known-shopper impressions are in the low band; worth roughly +0.45 overall |
| [14 Nov 16:05](notes/2026-11-14_1605_v6-first-read.md) | **v6 first read**: behind v5 on known shoppers and ahead on new ones after six minutes (too early); its lists do not contain more bought-brand products than v5's, so the brand lever is not being tested yet; the brand effect holds with purchase count fixed (2–2.7× for shoppers with 1–19 purchases) |
| [14 Nov 15:40](notes/2026-11-14_1540_path-to-the-reference.md) | **The path to the reference**: v5 converts 1.94% on what it serves; the board loses ≈0.12 to unanswered requests and ≈0.22 to exploration; the remaining model gap is on known shoppers. New lever: the brands a shopper has bought (2.2–2.5×, not in the model). Checked and withdrawn: `home` page, impression discounting |
| [14 Nov 15:20](notes/2026-11-14_1520_conversion-drop-after-1406.md) | **v5 converts half as much since 14:06 UTC** (1.22% vs 2.35%) with unchanged lists, order, shoppers and organic stream; what was ruled out, what is left, and the test that separates the two remaining causes. Also: repeat visits convert half as much as first visits |
| [14 Nov 15:00](notes/2026-11-14_1500_v5-ab-result.md) | **A/B result**: the learned ranker converts 2.50% against 1.50% for the rules (2.4 standard errors); the gain is on known shoppers (2.10% vs 0.97%); v5 puts 62% of known-shopper impressions in purchase-history subcategories against 34%. At the reference's level on served requests |
| [14 Nov 14:30](notes/2026-11-14_1430_why-far-from-reference.md) | **Why we are far from the reference**: the gap is all on known shoppers; their purchases follow their purchase-history subcategories (63%), not the session's category (21%); arithmetic of what the lever is worth; a proposed A/B arm |
| [14 Nov 14:14](notes/2026-11-14_1414_incident-unanswered-requests.md) | Incidents: requests unanswered at 14:14–14:31 and 14:58–15:01. Cause: OneDrive uploading the Python environment from inside the repository saturated the uplink; a second process talking to RawTree then tipped the server into timeouts. What to change before the final |
| [14 Nov 14:25](notes/2026-11-14_1425_generalisation-reference-techniques.md) | Generalisation: the purchase-history lever also works with live-only history (new shoppers 5.8×), and the stream alone gives a live purchase for 28% of requests by the second hour. The reference beats us only on known shoppers. Techniques ranked by expected return, with sources. Price drops lift purchases ≈26% |
| [14 Nov 14:06](notes/2026-11-14_1406_known-shoppers-gap.md) | The gap to the reference is on known shoppers; a purchase history in the product's subcategory multiplies purchases 6–14×; organic events show no satiation, the carousel does |
