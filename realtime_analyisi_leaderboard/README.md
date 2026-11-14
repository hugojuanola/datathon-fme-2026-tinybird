# Real-time analysis of the leaderboard and the live model

A watch on how our recommender is doing while it runs: where we stand against the other teams, the reference
and the baseline, and — from our own feedback — which shoppers we convert and which we do not. It is written
for whoever is training or tuning the model: read `latest.md` for the numbers and `notes/` for what they mean.

| File | What |
|---|---|
| [`latest.md`](latest.md) | The last tick: leaderboard top 5, who served our shoppers, conversion by model version and kind of shopper, the known-shopper lever. Regenerated every tick |
| [`history.csv`](history.csv) | One row per tick, to see the trend |
| [`notes/`](notes/) | One dated note per finding worth acting on, with the evidence and what to do |
| [`tick.py`](tick.py) | Produces `latest.md` and a row of `history.csv`. Read-only: leaderboard API + `SELECT`s |

```bash
python realtime_analyisi_leaderboard/tick.py              # last 30 minutes of our feedback
python realtime_analyisi_leaderboard/tick.py --window 60
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

_Updated 14 Nov 2026, 14:15 CET._

- **We lead on conversion**: 1.30 against 1.14 for the best rival (team_09); the reference is at 2.03 and
  the baseline at 0.71, so we are 45% of the way from baseline to reference. Cold conversion 1.81 (reference 1.90).
- **Reliability is fine now**: 99.96% of the last 30 minutes served by us, p95 1.65 s. The leaderboard still
  shows 79% on time because its one-hour window includes the start-up and three restarts.
- **The gap is on known shoppers**: 1.07% (3,756 requests) against 2.01% for new shoppers (1,639), while the
  reference does about as well on both. See [the 14:06 note](notes/2026-11-14_1406_known-shoppers-gap.md).
- **`v4a` vs `v4b`**: 1.47% (39 purchases in 2,661 requests) vs 1.24% (34 in 2,734) in the last 30 minutes —
  inside the noise.

## Notes

| When (CET) | Finding |
|---|---|
| [14 Nov 14:06](notes/2026-11-14_1406_known-shoppers-gap.md) | The gap to the reference is on known shoppers; a purchase history in the product's subcategory multiplies purchases 6–14×; organic events show no satiation, the carousel does |
