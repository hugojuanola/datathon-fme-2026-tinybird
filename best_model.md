# Best model so far

_Updated 14 Nov 2026, 19:00 CET by [`realtime_analyisi_leaderboard/best_model.py`](realtime_analyisi_leaderboard/best_model.py). Numbers are the organisers' own: expected purchases per 100 requests under the hidden model, per `model_version`._

**Record: `skore_money_v9`** — attributes + carts by subcategory; learned from the old log and today's feedback. 2.37 expected purchases per 100 requests on 2,822 requests, against 2.07 for the organisers' reference over the same minutes: **+0.30**.

Tied with it, within what the measurement can tell apart (0.15 points): `skore_money_v13` (+0.29), `skore_money_v9w` (+0.28), `skore_money_v15` (+0.26), `skore_money_v8` (+0.26), `skore_money_v14` (+0.24).

- **Best on cold requests** (new shopper, or a new product among the recent views — what the final is expected to bring): `skore_money_v9w`, 3.35 against the reference's 1.87.
- **Best on the other requests** (known shoppers): `skore_money_v9`, 2.11 against 2.17.
- **Code**: branch `javier`, last commit on `reco/` or `offline/`: `e4c8a45 — skore_money_v21-v28: the overnight experiment (four ranker set-ups x trend lift off / on)`. Model files: `models/`.

## Every version we have served

Ranked by the margin over the reference in the minutes each version was live (UTC). Exploration arms and versions with fewer than 1,500 requests are listed but cannot hold the record.

| Version | What it is | Live (UTC) | Requests | Conversion | Reference, same minutes | Margin | Cold (margin) | Other requests (margin) | € per request |
|---|---|---|---|---|---|---|---|---|---|
| `skore_money_v7` | + product attributes from the description (20 phrases, 2 per product) | 15:10–15:30 | 1,432 | 2.42 | 2.06 | **+0.37** | 2.88 (+1.08) | 2.17 (-0.03) | 1.28 |
| `skore_money_v9` **← record** | attributes + carts by subcategory; learned from the old log and today's feedback | 15:40–16:30 | 2,822 | 2.37 | 2.07 | **+0.30** | 2.84 (+0.96) | 2.11 (-0.06) | 1.27 |
| `skore_money_v13` (tied) | routed: v9w for cold requests, v10 for the rest | 16:40–17:15 | 1,724 | 2.35 | 2.06 | **+0.29** | 2.75 (+0.98) | 2.14 (-0.08) | 1.31 |
| `skore_money_v9w` (tied) | v9 with today's feedback weighted ×20 (best on cold requests) | 15:55–16:45 | 2,613 | 2.36 | 2.08 | **+0.28** | 3.35 (+1.49) | 1.84 (-0.35) | 1.31 |
| `skore_money_v15` (tied) | v11 + weaker trend lift (no trend ran while it was live) | 17:15–17:45 | 1,764 | 2.28 | 2.02 | **+0.26** | 3.06 (+1.09) | 1.88 (-0.18) | 1.11 |
| `skore_money_v8` (tied) | v7 without the brand features, refit on all the data | 15:25–16:00 | 2,665 | 2.35 | 2.09 | **+0.26** | 3.22 (+1.27) | 1.88 (-0.28) | 1.24 |
| `skore_money_v14` (tied) | v11 + trend lift (no trend ran while it was live: same behaviour as v11) | 16:40–17:45 | 3,558 | 2.28 | 2.04 | **+0.24** | 2.98 (+1.13) | 1.89 (-0.26) | 1.00 |
| `skore_money_v11` | routed: v9w for cold requests, v9 for the rest | 16:25–17:45 | 4,457 | 2.15 | 2.07 | **+0.08** | 2.92 (+1.09) | 1.68 (-0.52) | 0.87 |
| `skore_money_v9d` | see docs/findings.md | 15:55–16:30 | 1,753 | 2.15 | 2.07 | **+0.08** | 3.01 (+1.08) | 1.71 (-0.44) | 0.98 |
| `v2a` | see docs/findings.md | 12:20–12:35 | 339 | 1.99 | 1.99 | **+0.00** | 2.83 (+0.84) | 1.61 (-0.38) | 0.97 |
| `skore_money_v5` | first learned ranker: P(click) × P(purchase | click) over the rules' candidates | 13:30–15:45 | 12,910 | 1.81 | 2.10 | **-0.29** | 2.57 (+0.58) | 1.41 (-0.75) | 0.88 |
| `v4a` | rules: popularity × measured lifts (just-viewed ×3) | 12:40–13:35 | 4,590 | 1.57 | 2.02 | **-0.46** | 2.12 (+0.28) | 1.29 (-0.82) | 0.69 |
| `skore_money_v6` | v5 + shopper × brand history, new-product and discount features | 14:45–15:00 | 406 | 1.63 | 2.21 | **-0.58** | 2.91 (+0.65) | 0.90 (-1.28) | 0.64 |
| `v3a` | see docs/findings.md | 12:25–12:40 | 563 | 1.50 | 2.09 | **-0.58** | 2.20 (+0.17) | 1.24 (-0.87) | 0.70 |
| `v2b` | see docs/findings.md | 12:20–12:35 | 338 | 1.39 | 1.99 | **-0.60** | 2.23 (+0.24) | 0.98 (-1.01) | 0.87 |
| `v4b` | rules: popularity × measured lifts (just-viewed ×1.5) | 12:40–13:35 | 4,647 | 1.42 | 2.02 | **-0.60** | 1.73 (-0.11) | 1.27 (-0.84) | 0.61 |
| `skore_money_v4` | rules: popularity × measured lifts | 13:30–14:00 | 2,024 | 1.45 | 2.06 | **-0.61** | 2.01 (-0.01) | 1.16 (-0.91) | 0.53 |
| `v3b` | see docs/findings.md | 12:25–12:40 | 558 | 1.17 | 2.09 | **-0.92** | 1.71 (-0.32) | 0.91 (-1.20) | 0.47 |
| `skore_money_v5_explore` | see docs/findings.md | 13:55–15:00 | 1,722 | 1.21 | 2.14 | **-0.93** | 1.80 (-0.31) | 0.88 (-1.27) | 0.76 |
| `baseline` | all-time best sellers (the starter baseline) | 11:30–11:45 | 1,395 | 0.75 | 2.33 | **-1.58** | 1.31 (-0.64) | 0.48 (-2.03) | 0.19 |

## How to read it

- The number is an expectation computed by the organisers from the hidden model, not a count of purchases, so it has no coin flip in it — but it still moves: on 14 Nov two arms running the same code differed by 0.12 over half an hour, and three identical arms read 1.92, 2.40 and 2.59 over a quarter of an hour. A version needs thousands of requests, and a lead of less than about 0.15 is a tie.
- Each version is compared with the reference over its own minutes, because the store is easier in some hours than in others.
- Versions whose only difference is the trend lift behave identically while no trend is running.

## Record

- 14 Nov 2026, 19:00 CET — `skore_money_v9` takes the record: 2.37 expected purchases per 100 requests on 2,822 requests, +0.30 against the reference over the same minutes.
