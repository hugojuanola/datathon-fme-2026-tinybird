# Real-time analysis of the leaderboard and the live model

A watch on how our recommender is doing while it runs: where we stand against the other teams, the reference
and the baseline, and — from our own feedback — which shoppers we convert and which we do not. It is written
for whoever is training or tuning the model: read `latest.md` for the numbers and `notes/` for what they mean.

| File | What |
|---|---|
| [`latest.md`](latest.md) | The last tick: leaderboard top 5, who served our shoppers, conversion by model version and kind of shopper, the known-shopper lever. Regenerated every tick |
| [`history.csv`](history.csv) | One row per tick, to see the trend |
| [`notes/`](notes/) | One dated note per finding worth acting on, with the evidence and what to do |
| [`tick.py`](tick.py) | Produces `latest.md` and a row of `history.csv`. Read-only and light: leaderboard API + three `SELECT`s on the last minutes of the live tables; the 60-day purchase history comes from a local cache, not from a scan |
| [`queries/`](queries/) | The SQL behind the notes, runnable with `python scripts/rt.py -f <file>` |

Every analysis here is held to three questions: does it generalise to the final (new shoppers, products and
trends)? how does it compare with the reference? is there a better-founded technique for it in the literature?

```bash
.venv/Scripts/python.exe realtime_analyisi_leaderboard/tick.py                                  # last 30 minutes
.venv/Scripts/python.exe realtime_analyisi_leaderboard/tick.py --window 60
.venv/Scripts/python.exe realtime_analyisi_leaderboard/tick.py --since "2026-11-14 13:35:00"     # UTC, e.g. since a deploy
```

## How to read a tick

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

_Updated 14 Nov 2026, 14:45 CET._

- **`skore_money_v5` (learned ranker) is live since 14:35 CET, A/B against `skore_money_v4` (the rules).**
  First seven minutes, so a direction and not a result: known shoppers 2.39% with v5 (11 purchases in 461
  requests) against 1.35% with v4 (6 in 443); new shoppers 2.97% (6 in 202) against 2.62% (5 in 191).
- **The mechanism is doing what the analysis asked for**, and this part is already solid (4,600 impressions per
  arm): v5 puts 62% of its known-shopper impressions in subcategories where the shopper has bought before;
  v4 puts 34%. Those impressions sell at about 0.3% each, the others at under 0.1%.
- **Leaderboard**: conversion 1.47 against 1.21 for the best rival (team_09); reference 2.03, baseline 0.70 —
  58% of the way from baseline to reference. Cold conversion 1.92, above the reference's 1.82.
- **Reliability**: back to normal after the 14:14–14:31 stall (p95 1.67 s); the leaderboard's hourly
  `on_time` is 95% and will keep recovering. The switch to v5 cost 38 unanswered requests.
- **When to read the A/B**: with about 1,800 known-shopper requests per arm every 30 minutes, a difference
  like 1.4% vs 2.4% needs roughly one hour (until about 15:35 CET) to be outside the noise.

## Notes

| When (CET) | Finding |
|---|---|
| [14 Nov 14:30](notes/2026-11-14_1430_why-far-from-reference.md) | **Why we are far from the reference**: the gap is all on known shoppers; their purchases follow their purchase-history subcategories (63%), not the session's category (21%); arithmetic of what the lever is worth; a proposed A/B arm |
| [14 Nov 14:14](notes/2026-11-14_1414_incident-unanswered-requests.md) | Incident: 22% of requests unanswered for 8 minutes — a heavy local job starved the server. What to change before the final |
| [14 Nov 14:25](notes/2026-11-14_1425_generalisation-reference-techniques.md) | Generalisation: the purchase-history lever also works with live-only history (new shoppers 5.8×), and the stream alone gives a live purchase for 28% of requests by the second hour. The reference beats us only on known shoppers. Techniques ranked by expected return, with sources. Price drops lift purchases ≈26% |
| [14 Nov 14:06](notes/2026-11-14_1406_known-shoppers-gap.md) | The gap to the reference is on known shoppers; a purchase history in the product's subcategory multiplies purchases 6–14×; organic events show no satiation, the carousel does |
