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

## Current reading

_Updated 14 Nov 2026, 16:45 CET._

- **In the last 15 minutes we are above the reference**: 2.135 against 2.011 on the official board (expected
  purchases, 2,700 requests, 100% on time). Last 30 minutes: 2.035 against 2.048. Last hour: 2.00 against
  2.14 — 90% of the way, 0.14 missing, and closing as the older minutes roll out.
- **Cold conversion** 2.69 against the reference's 2.00 (hour) — well ahead.
- **Best rival**: team_26 at 1.79 (hour) and 1.82 (15 minutes).
- **Live since 16:25 CET**: `skore_money_v8` 60% (product attributes, no brand features), `skore_money_v5` 30%
  as control, `skore_money_v8_explore` 10%. The arms stay fixed until about 17:25 CET.
- **Still to confirm with our own feedback**: v8 against v5 over the same minutes, known and new shoppers
  separately ([16:25 note](notes/2026-11-14_1625_v7-live-mechanism.md) has the mechanism check).
- **The board can be read for any window** of 15 minutes or more: `tick.py` now reports the last hour and the
  last 15 minutes side by side (`https://datathon.rawtree.dev/api/state?from=<unix>&to=<unix>`).

## Notes

| When (CET) | Finding |
|---|---|
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
