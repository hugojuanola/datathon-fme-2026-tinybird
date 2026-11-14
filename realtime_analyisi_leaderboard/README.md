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
python realtime_analyisi_leaderboard/tick.py                                  # last 30 minutes
python realtime_analyisi_leaderboard/tick.py --window 60
python realtime_analyisi_leaderboard/tick.py --since "2026-11-14 13:35:00"     # UTC, e.g. since a deploy
```

Run these with the project's Python environment. On the serving laptop it is
`C:/Users/javil/skore_money/venv/Scripts/python.exe`; it lives outside the repository because the
repository is in a OneDrive folder and syncing an environment saturates the uplink the live server needs.

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

_Updated 14 Nov 2026, 15:45 CET._

- **Leaderboard**: 1.53, rank 2 — team_19 passed us with 1.54; team_09 at 1.42. Reference 2.10, baseline 0.73.
  Cold conversion 2.18, above the reference's 1.96.
- **The model is better than the board shows.** On the requests it serves, `skore_money_v5` converts 1.94%
  (142 purchases in 7,328 requests) and earns more per request than the reference. The board loses about
  0.12 points to unanswered requests (8.3% since 15:06 CET) and about 0.22 to the exploration arm (20% of
  traffic at 0.83%). See [the 15:40 note](notes/2026-11-14_1540_path-to-the-reference.md).
- **What is left to reach the reference is on known shoppers**: the `home` page (0.59% against 1.8–2.0% on
  the other pages, worth ≈0.13), repeat visits (0.95% against 1.89% on a first visit, worth ≈0.11), and
  shoppers with a medium history (no gain from v5).
- **The 15:06 drop eased**: per six minutes 1.15, 1.13, 1.40, 1.56, 1.93, 1.47. The 2.35% of 14:34–15:06 was
  probably a lucky stretch; the average since v5 went live is the better estimate.
- **Reliability**: a new server instance with hedged requests started at 15:35 CET; first minutes clean.
- **Live**: 80% `skore_money_v5`, 20% `skore_money_v5_explore`.

## Notes

| When (CET) | Finding |
|---|---|
| [14 Nov 15:40](notes/2026-11-14_1540_path-to-the-reference.md) | **The path to the reference**: v5 converts 1.94% on what it serves; the board loses ≈0.12 to unanswered requests and ≈0.22 to exploration; the remaining model gap is on known shoppers — `home` page, repeat visits, medium-history shoppers — with a size for each and what to do |
| [14 Nov 15:20](notes/2026-11-14_1520_conversion-drop-after-1406.md) | **v5 converts half as much since 14:06 UTC** (1.22% vs 2.35%) with unchanged lists, order, shoppers and organic stream; what was ruled out, what is left, and the test that separates the two remaining causes. Also: repeat visits convert half as much as first visits |
| [14 Nov 15:00](notes/2026-11-14_1500_v5-ab-result.md) | **A/B result**: the learned ranker converts 2.50% against 1.50% for the rules (2.4 standard errors); the gain is on known shoppers (2.10% vs 0.97%); v5 puts 62% of known-shopper impressions in purchase-history subcategories against 34%. At the reference's level on served requests |
| [14 Nov 14:30](notes/2026-11-14_1430_why-far-from-reference.md) | **Why we are far from the reference**: the gap is all on known shoppers; their purchases follow their purchase-history subcategories (63%), not the session's category (21%); arithmetic of what the lever is worth; a proposed A/B arm |
| [14 Nov 14:14](notes/2026-11-14_1414_incident-unanswered-requests.md) | Incidents: requests unanswered at 14:14–14:31 and 14:58–15:01. Cause: OneDrive uploading the Python environment from inside the repository saturated the uplink; a second process talking to RawTree then tipped the server into timeouts. What to change before the final |
| [14 Nov 14:25](notes/2026-11-14_1425_generalisation-reference-techniques.md) | Generalisation: the purchase-history lever also works with live-only history (new shoppers 5.8×), and the stream alone gives a live purchase for 28% of requests by the second hour. The reference beats us only on known shoppers. Techniques ranked by expected return, with sources. Price drops lift purchases ≈26% |
| [14 Nov 14:06](notes/2026-11-14_1406_known-shoppers-gap.md) | The gap to the reference is on known shoppers; a purchase history in the product's subcategory multiplies purchases 6–14×; organic events show no satiation, the carousel does |
