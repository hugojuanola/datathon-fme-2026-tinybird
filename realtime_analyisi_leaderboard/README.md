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
| [`queries/`](queries/) | The SQL behind the notes, runnable with `python scripts/rt.py -f <file>` |

Every analysis here is held to three questions: does it generalise to the final (new shoppers, products and
trends)? how does it compare with the reference? is there a better-founded technique for it in the literature?

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

_Updated 14 Nov 2026, 14:30 CET._

- **We lead on conversion**: 1.38 against 1.13 for the best rival (team_09); the reference is at 2.04 and the
  baseline at 0.71, so we are half-way (50%) from baseline to reference. Cold conversion 1.86 (reference 1.88).
- **Why we are far from the reference**: on cold requests we match it; all of the gap (0.65 of 0.66 points)
  is on known shoppers, whose purchases follow their purchase history (63% of their next purchases are in a
  subcategory they have bought in before) while v4 builds the list around the session. See
  [the 14:30 note](notes/2026-11-14_1430_why-far-from-reference.md), which proposes one A/B arm.
- **Incident 14:14–14:22**: 312 of 1,440 requests went unanswered because a heavy local job starved the
  server. Recovered. See [the incident note](notes/2026-11-14_1414_incident-unanswered-requests.md).
- **`v4a` vs `v4b`**: 1.18% vs 1.22% in the last 30 minutes — no difference.

## Notes

| When (CET) | Finding |
|---|---|
| [14 Nov 14:30](notes/2026-11-14_1430_why-far-from-reference.md) | **Why we are far from the reference**: the gap is all on known shoppers; their purchases follow their purchase-history subcategories (63%), not the session's category (21%); arithmetic of what the lever is worth; a proposed A/B arm |
| [14 Nov 14:14](notes/2026-11-14_1414_incident-unanswered-requests.md) | Incident: 22% of requests unanswered for 8 minutes — a heavy local job starved the server. What to change before the final |
| [14 Nov 14:25](notes/2026-11-14_1425_generalisation-reference-techniques.md) | Generalisation: the purchase-history lever also works with live-only history (new shoppers 5.8×), and the stream alone gives a live purchase for 28% of requests by the second hour. The reference beats us only on known shoppers. Techniques ranked by expected return, with sources. Price drops lift purchases ≈26% |
| [14 Nov 14:06](notes/2026-11-14_1406_known-shoppers-gap.md) | The gap to the reference is on known shoppers; a purchase history in the product's subcategory multiplies purchases 6–14×; organic events show no satiation, the carousel does |
