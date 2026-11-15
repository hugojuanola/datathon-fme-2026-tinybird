# Best model so far

_Updated 15 Nov 2026, 04:12 CET by [`realtime_analyisi_leaderboard/best_model.py`](realtime_analyisi_leaderboard/best_model.py). Numbers are the organisers' own: expected purchases per 100 requests under the hidden model, per `model_version`._

**Record: `skore_money_v9`** — attributes + carts by subcategory; learned from the old log and today's feedback. 2.37 expected purchases per 100 requests on 2,822 requests, against 2.02 for the organisers' reference over the same half hours: **+0.35**.

Tied with it, within what the measurement can tell apart (0.15 points): `skore_money_v36` (+0.42), `skore_money_v22` (+0.40), `skore_money_v23` (+0.39), `skore_money_v27` (+0.39), `skore_money_v9w` (+0.34), `skore_money_v37` (+0.32), `skore_money_v21` (+0.32), `skore_money_v32` (+0.31), `skore_money_v39` (+0.31), `skore_money_v31` (+0.31), `skore_money_v28` (+0.30), `skore_money_v38` (+0.28), `skore_money_v15` (+0.25), `skore_money_v8` (+0.25), `skore_money_v33` (+0.24), `skore_money_v26` (+0.24), `skore_money_v25` (+0.23), `skore_money_v13` (+0.23), `skore_money_v14` (+0.21), `skore_money_v40` (+0.20), `skore_money_v24` (+0.20).

- **Best on cold requests** (new shopper, or a new product among the recent views — what the final is expected to bring): `skore_money_v9w`, 3.21 against the reference's 1.77.
- **Best on the other requests** (known shoppers): `skore_money_v9`, 2.11 against 2.11. On cold requests every version of ours since v7 is 1.0 to 1.5 above the reference; on the other requests the best of ours are level with it. That is the gap still open.
- **Code**: branch `javier`, last commit on `reco/` or `offline/`: `c674dcb — skore_money_v38, v39, v40: new products x1.5 and the organic order read two by two; trending products keep v9's slot (live since 00:46 UTC)`. Model files: `models/`.

**Being measured against the record** (all on the v9 ranker, trend lift at full strength; live since 00:46 UTC on 15 Nov, 25 % each): `skore_money_v31` v9 itself; `v38` v9 with products added during the event × 1.5 for known shoppers; `v39` v9 picks the ten and the organic factor orders them, a trending product keeping the slot v9 gave it; `v40` = `v39` with the × 1.5. Two questions crossed, each read on all the traffic: `python scripts/arms.py 00:50 07:30 | python realtime_analyisi_leaderboard/pool_arms.py "v9's order=31,38" 'organic order=39,40'` and the same with 'as it is=31,39' 'new x1.5=38,40', on Sunday morning; every test of the day, with what it gave and what it cost, is in `realtime_analyisi_leaderboard/experiments.md`. Earlier: `v32` (v9 × organic choosing among the best 100), `v36` (`v32` with the × 1.5) and `v37` (the organic order before the trend fix) ran 22:25–00:46 UTC and never read above v9; `v33` (v9 retrained on all of Saturday) was level with v9 and left at 22:23 UTC; `v34` (no trend lift) and `v35` (lift ^0.5) ran 20:35–21:33 without a trend to measure. Before them, 17:45–20:30 UTC, `v21`–`v28` compared v9, v9w cold + v9 warm, v16 and v16w cold + v16 warm, each with the trend lift off and at ^0.75: v9 everywhere led (+0.38 over the reference on 7,186 requests), v16 lost on warm requests (1.78 against 1.97, 2.7 standard errors) and the lift at ^0.75 changed nothing.

## Putting the record back

To serve the record alone: in `reco/serve.py` set `ARMS = (("skore_money_v9", "model", "v9", {}, 100),)`, commit, then run `powershell -ExecutionPolicy Bypass -File scripts\swap_server.ps1`. The script starts the new server in standby as a process of its own, waits for its self-test (every arm must answer real requests with valid lists) and only then stops the old one; if the new one is not fit, nothing changes. Never start or stop a server any other way.

## Every version we have served

Ranked by the margin over the reference in the half hours each version was live (UTC), the reference weighted by the version's own requests. Exploration arms and versions with fewer than 1,500 requests are listed but cannot hold the record.

| Version | What it is | Live (UTC) | Requests | Conversion | Reference, same half hours | Margin | Cold (margin) | Other requests (margin) | € per request |
|---|---|---|---|---|---|---|---|---|---|
| `skore_money_v36` (tied) | v32 (v9 × organic, trend lift ^1.0) with products added during the event × 1.5 for known shoppers | 21:30–01:00 | 7,047 | 2.41 | 1.99 | **+0.42** | 3.10 (+1.25) | 1.96 (-0.12) | 1.23 |
| `skore_money_v22` (tied) | v9 everywhere, trend lift ^0.75 | 17:30–20:30 | 5,454 | 2.37 | 1.98 | **+0.40** | 2.93 (+1.12) | 2.05 (-0.04) | 1.17 |
| `skore_money_v23` (tied) | routed v9w cold / v9 warm, trend lift off | 18:00–20:30 | 1,637 | 2.39 | 1.99 | **+0.39** | 3.18 (+1.38) | 1.88 (-0.23) | 1.07 |
| `skore_money_v27` (tied) | routed v16w cold / v16 warm, trend lift off | 17:30–20:30 | 1,743 | 2.36 | 1.98 | **+0.39** | 3.17 (+1.35) | 1.88 (-0.20) | 1.15 |
| `skore_money_v12` | variant served 16:29–16:53 UTC next to v11 (see docs/findings.md) | 16:30–17:00 | 838 | 2.36 | 2.00 | **+0.36** | 2.43 (+0.75) | 2.32 (+0.14) | 1.31 |
| `skore_money_v9` **← record** | attributes + carts by subcategory; learned from the old log and today's feedback | 15:30–16:30 | 2,822 | 2.37 | 2.02 | **+0.35** | 2.84 (+0.98) | 2.11 (-0.00) | 1.27 |
| `skore_money_v9w` (tied) | v9 with today's feedback weighted ×20 (best on cold requests) | 16:00–17:00 | 2,533 | 2.32 | 1.99 | **+0.34** | 3.21 (+1.44) | 1.87 (-0.24) | 1.30 |
| `skore_money_v7` | + product attributes from the description (20 phrases, 2 per product) | 15:00–15:30 | 1,432 | 2.42 | 2.09 | **+0.34** | 2.88 (+1.15) | 2.17 (-0.10) | 1.28 |
| `skore_money_v37` (tied) | v9 + trend lift picks the ten, v9 × organic only orders them | 22:00–01:00 | 5,160 | 2.33 | 2.01 | **+0.32** | 2.99 (+1.11) | 1.91 (-0.18) | 1.15 |
| `skore_money_v21` (tied) | v9 everywhere, trend lift off | 17:30–20:30 | 1,733 | 2.30 | 1.98 | **+0.32** | 3.06 (+1.25) | 1.87 (-0.22) | 1.03 |
| `skore_money_v32` (tied) | v9 × organic ^0.5 (a third model: what shoppers go on to buy in the store), trend lift ^1.0 | 20:30–01:00 | 13,672 | 2.31 | 2.00 | **+0.31** | 2.95 (+1.11) | 1.89 (-0.20) | 1.14 |
| `skore_money_v39` (tied) | v9 + trend lift picks the ten, v9 × organic orders them; a trending product keeps v9's slot | 00:30–03:00 | 5,988 | 2.26 | 1.95 | **+0.31** | 2.84 (+1.11) | 1.86 (-0.24) | 1.16 |
| `skore_money_v31` (tied) | v9 everywhere, trend lift at full strength (^1.0) | 20:30–03:00 | 19,572 | 2.29 | 1.98 | **+0.31** | 2.90 (+1.09) | 1.88 (-0.21) | 1.17 |
| `skore_money_v28` (tied) | routed v16w cold / v16 warm, trend lift ^0.75 | 17:30–20:30 | 5,547 | 2.27 | 1.98 | **+0.30** | 3.04 (+1.24) | 1.79 (-0.29) | 1.11 |
| `skore_money_v38` (tied) | v9 + trend lift, products added during the event × 1.5 for known shoppers (no organic model) | 00:30–03:00 | 6,108 | 2.23 | 1.95 | **+0.28** | 2.74 (+1.00) | 1.84 (-0.25) | 1.04 |
| `skore_money_v8c` | variant of v8 (see docs/findings.md) | 15:30–16:00 | 924 | 2.38 | 2.10 | **+0.28** | 3.30 (+1.34) | 1.84 (-0.33) | 1.11 |
| `skore_money_v15` (tied) | v11 + weaker trend lift (no trend ran while it was live) | 17:00–18:00 | 1,764 | 2.28 | 2.04 | **+0.25** | 3.06 (+1.19) | 1.88 (-0.25) | 1.11 |
| `skore_money_v8` (tied) | v7 without the brand features, refit on all the data | 15:00–16:00 | 2,665 | 2.35 | 2.10 | **+0.25** | 3.22 (+1.30) | 1.88 (-0.31) | 1.24 |
| `skore_money_v33` (tied) | v9b = v9's 52 features retrained on all of 14 Nov, trend lift ^1.0 | 20:30–22:30 | 4,050 | 2.22 | 1.98 | **+0.24** | 2.80 (+1.00) | 1.87 (-0.23) | 1.05 |
| `skore_money_v26` (tied) | v16 everywhere, trend lift ^0.75 | 17:30–20:30 | 5,450 | 2.22 | 1.98 | **+0.24** | 3.02 (+1.21) | 1.73 (-0.36) | 1.17 |
| `skore_money_v25` (tied) | v16 everywhere (retrained on all of 14 Nov), trend lift off | 17:30–20:30 | 1,821 | 2.21 | 1.98 | **+0.23** | 2.90 (+1.09) | 1.78 (-0.31) | 1.01 |
| `skore_money_v13` (tied) | routed: v9w for cold requests, v10 for the rest | 16:30–17:30 | 1,726 | 2.36 | 2.12 | **+0.23** | 2.76 (+0.95) | 2.14 (-0.15) | 1.31 |
| `skore_money_v14` (tied) | v11 + trend lift (no trend ran while it was live: same behaviour as v11) | 16:30–18:00 | 3,558 | 2.28 | 2.08 | **+0.21** | 2.98 (+1.14) | 1.89 (-0.32) | 1.00 |
| `skore_money_v40` (tied) | v39 with products added during the event × 1.5 for known shoppers | 00:30–03:00 | 5,978 | 2.15 | 1.95 | **+0.20** | 2.53 (+0.80) | 1.89 (-0.21) | 1.02 |
| `skore_money_v24` (tied) | routed v9w cold / v9 warm, trend lift ^0.75 | 17:30–20:30 | 5,438 | 2.18 | 1.98 | **+0.20** | 2.53 (+0.72) | 1.97 (-0.12) | 1.05 |
| `skore_money_v35` | v9 everywhere, trend lift ^0.5 (dose) | 20:30–21:30 | 1,024 | 2.19 | 2.02 | **+0.17** | 2.51 (+0.69) | 1.97 (-0.18) | 0.91 |
| `skore_money_v9d` | variant of v9 (see docs/findings.md) | 16:00–16:30 | 1,668 | 2.12 | 1.98 | **+0.14** | 2.96 (+1.15) | 1.69 (-0.38) | 0.99 |
| `skore_money_v11` | routed: v9w for cold requests, v9 for the rest | 16:30–18:00 | 4,400 | 2.15 | 2.06 | **+0.08** | 2.91 (+1.10) | 1.68 (-0.52) | 0.86 |
| `skore_money_v34` | v9 everywhere, no trend lift (control for the trends) | 20:30–21:30 | 997 | 2.06 | 2.03 | **+0.04** | 2.96 (+1.14) | 1.50 (-0.64) | 1.14 |
| `v2a` | see docs/findings.md | 12:00–13:00 | 339 | 1.99 | 2.04 | **-0.05** | 2.83 (+0.86) | 1.61 (-0.47) | 0.97 |
| `skore_money_v8_explore` | see docs/findings.md | 15:30–16:00 | 501 | 1.81 | 2.10 | **-0.29** | 1.73 (-0.24) | 1.85 (-0.32) | 1.03 |
| `skore_money_v5` | first learned ranker: P(click) × P(purchase given a click) over the rules' candidates | 13:30–16:00 | 12,910 | 1.81 | 2.13 | **-0.31** | 2.57 (+0.54) | 1.41 (-0.77) | 0.88 |
| `skore_money_v6` | v5 + shopper × brand history, new-product and discount features | 14:30–15:30 | 1,383 | 1.70 | 2.12 | **-0.42** | 2.47 (+0.60) | 1.31 (-0.94) | 0.76 |
| `v4a` | rules: popularity × measured lifts (just-viewed ×3) | 12:30–14:00 | 4,590 | 1.57 | 2.04 | **-0.48** | 2.12 (+0.28) | 1.29 (-0.85) | 0.69 |
| `v3a` | see docs/findings.md | 12:30–13:00 | 563 | 1.50 | 2.07 | **-0.56** | 2.20 (+0.14) | 1.24 (-0.84) | 0.70 |
| `skore_money_v4` | rules: popularity × measured lifts | 13:30–14:00 | 2,024 | 1.45 | 2.06 | **-0.61** | 2.01 (-0.01) | 1.16 (-0.91) | 0.53 |
| `v4b` | rules: popularity × measured lifts (just-viewed ×1.5) | 12:30–14:00 | 4,647 | 1.42 | 2.04 | **-0.62** | 1.73 (-0.11) | 1.27 (-0.87) | 0.61 |
| `v2b` | see docs/findings.md | 12:00–13:00 | 338 | 1.39 | 2.04 | **-0.65** | 2.23 (+0.27) | 0.98 (-1.10) | 0.87 |
| `v3b` | see docs/findings.md | 12:30–13:00 | 558 | 1.17 | 2.07 | **-0.90** | 1.71 (-0.35) | 0.91 (-1.16) | 0.47 |
| `skore_money_v5_explore` | see docs/findings.md | 13:30–15:00 | 1,722 | 1.21 | 2.15 | **-0.94** | 1.80 (-0.29) | 0.88 (-1.30) | 0.76 |
| `baseline` | all-time best sellers (the starter baseline) | 11:30–12:00 | 1,395 | 0.75 | 2.21 | **-1.46** | 1.31 (-0.61) | 0.48 (-1.88) | 0.19 |

## How to read it

- The number is an expectation computed by the organisers from the hidden model, not a count of purchases, so it has no coin flip in it — but it still moves: on 14 Nov two arms running the same code differed by 0.12 over half an hour, and three identical arms read 1.92, 2.40 and 2.59 over a quarter of an hour. A version needs thousands of requests, and a lead of less than about 0.15 is a tie.
- Each version is compared with the reference over its own half hours, because the store is easier in some hours than in others.
- Versions whose only difference is the trend lift behave identically while no trend is running.

## Record

- 14 Nov 2026, 19:00 CET — `skore_money_v9` takes the record: 2.37 expected purchases per 100 requests on 2,822 requests, +0.30 against the reference over the same minutes.
