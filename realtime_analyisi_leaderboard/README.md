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

_Updated 14 Nov 2026, 15:02 CET._

- **The learned ranker won the A/B.** 13:34–13:57 UTC: `skore_money_v5` 2.50% (58 purchases in 2,322
  requests) against `skore_money_v4` 1.50% (29 in 1,936), 2.4 standard errors apart. The gain is on known
  shoppers: 2.10% against 0.97% (2.6 standard errors). New shoppers 3.50% against 2.68%, not conclusive.
  See [the 15:00 note](notes/2026-11-14_1500_v5-ab-result.md).
- **All traffic is on v5 since 14:57 CET**, with a small exploration arm (`skore_money_v5_explore`).
- **Against the reference**: v5 is at its level on the requests it served (2.50 ± 0.64 against 2.06). The
  leaderboard shows 1.50 (rank 1; best rival team_09 at 1.27) because its one-hour window is still mostly v4;
  cold conversion 2.01 against the reference's 1.85.
- **Reliability is the open problem**: a second stall at 14:58–15:01 CET lost 172 requests; other teams were
  unaffected, so it is local. `on_time` on the leaderboard is 93.5%. See
  [the incident note](notes/2026-11-14_1414_incident-unanswered-requests.md).
- **Next to watch**: v5 on new shoppers (the final brings new shoppers), and whether the leaderboard climbs
  towards 2 over the next hour.

## Notes

| When (CET) | Finding |
|---|---|
| [14 Nov 15:00](notes/2026-11-14_1500_v5-ab-result.md) | **A/B result**: the learned ranker converts 2.50% against 1.50% for the rules (2.4 standard errors); the gain is on known shoppers (2.10% vs 0.97%); v5 puts 62% of known-shopper impressions in purchase-history subcategories against 34%. At the reference's level on served requests |
| [14 Nov 14:30](notes/2026-11-14_1430_why-far-from-reference.md) | **Why we are far from the reference**: the gap is all on known shoppers; their purchases follow their purchase-history subcategories (63%), not the session's category (21%); arithmetic of what the lever is worth; a proposed A/B arm |
| [14 Nov 14:14](notes/2026-11-14_1414_incident-unanswered-requests.md) | Incidents: requests unanswered at 14:14–14:31 (heavy local job + OneDrive upload) and again at 14:58–15:01 (cause not established; local, other teams unaffected). What to change before the final |
| [14 Nov 14:25](notes/2026-11-14_1425_generalisation-reference-techniques.md) | Generalisation: the purchase-history lever also works with live-only history (new shoppers 5.8×), and the stream alone gives a live purchase for 28% of requests by the second hour. The reference beats us only on known shoppers. Techniques ranked by expected return, with sources. Price drops lift purchases ≈26% |
| [14 Nov 14:06](notes/2026-11-14_1406_known-shoppers-gap.md) | The gap to the reference is on known shoppers; a purchase history in the product's subcategory multiplies purchases 6–14×; organic events show no satiation, the carousel does |
