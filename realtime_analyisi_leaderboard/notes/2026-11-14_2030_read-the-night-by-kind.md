# Read the night by kind of request, not by arm (14 Nov, 20:30 CET)

**In one line**: after 95 minutes the eight overnight arms are level overall, but underneath `v16` leads on
cold requests and `v9` on warm ones. The best set-up for the final may be the cross of the two, which is
not one of the eight arms and needs no new experiment. Not significant yet: the night decides.

## The numbers

`python scripts/arms.py 17:45 19:20` (UTC, the organisers' expected purchases per 100 requests). Overall,
pooling the arm without the trend lift with the one that has it (no trend ran, so they are the same code):

| Ranker set-up | Arms | Requests | Overall | Over the reference (1.886) |
|---|---|---|---|---|
| v9 everywhere | v21 + v22 | 4,146 | 2.083 | +0.20 |
| v9w cold, v9 warm | v23 + v24 | 4,038 | 2.077 | +0.19 |
| v16 everywhere | v25 + v26 | 4,055 | 2.108 | +0.22 |
| v16w cold, v16 warm | v27 + v28 | 4,123 | 2.138 | +0.25 |

Nothing to choose from: the spread is 0.06 and two arms running the same code differ by more than that.
The same requests split by kind, pooling every arm that uses the same ranker for that kind:

| Kind | Ranker | Arms | Requests | Expected purchases per 100 | Reference |
|---|---|---|---|---|---|
| cold | v9 | v21, v22 | 1,544 | 2.50 | 1.69 |
| cold | v9w | v23, v24 | 1,534 | 2.61 | 1.69 |
| cold | **v16** | v25, v26 | 1,492 | **2.89** | 1.69 |
| cold | **v16w** | v27, v28 | 1,573 | **2.90** | 1.69 |
| warm | **v9** | v21 to v24 | 5,106 | **1.80** | 2.01 |
| warm | v16 | v25 to v28 | 5,113 | 1.66 | 2.01 |

## Why the two halves can be chosen separately

A request is answered by exactly one ranker, picked by its kind. An arm's number is therefore
`cold share x (its cold ranker on cold requests) + warm share x (its warm ranker on warm requests)`, with
nothing shared between the halves. `v16 cold | v9 warm` was never served as an arm, yet both of its halves
are being measured tonight.

If the differences hold, the cross is worth 0.375 x 2.90 + 0.625 x 1.80 = **2.21**, against 2.08 to 2.14
for the eight arms now: about +0.1 overall, and the cold-start points (10 of the 70) get the better half.

## How much to trust it now

Not yet. Small arms that share a ranker scatter by about 0.3 on cold requests (`v23` 3.16 against `v24`
2.43, same ranker, 370 and 1,160 cold requests). By that yardstick each of the two differences is roughly
two standard errors: a question, not a finding. By Sunday morning the sample is eight times larger.

Also visible here: the weight given to live feedback (`v9w` against `v9`, `v16w` against `v16`) moves cold
requests little or nothing; what moved them is retraining on all of Saturday (`v16`). And every arm is
**below the reference on warm requests** (1.66 to 1.84 against 2.01) while far above it on cold ones. Warm
requests are where the remaining margin is; the 20:15 note has the candidate lever.

## For Sunday morning

1. `python scripts/arms.py 17:45 07:30`.
2. Pool the `cold` column by cold ranker (v21+v22, v23+v24, v25+v26, v27+v28, weighted by `cold req`) and
   the `warm` column by warm ranker (v21 to v24, v25 to v28, weighted by requests minus `cold req`).
3. Take the best ranker of each kind if it leads by more than 0.15; otherwise keep what is running.

Generalisation: `v16` uses no ids and was trained on the same day's stream, so its lead on cold requests
should carry to the final if the final's new shoppers arrive as today's did, with a few views already in
`shop.events`. It is still one day's evidence.

## Update, 22:00 CET — the experiment is closed (17:45-20:30 UTC), and where the rivals are

The model session replaced `v21`-`v28` at 20:32-20:35 UTC (the swap cost 4 requests). Final numbers,
`python scripts/arms.py 17:45 20:30 | python realtime_analyisi_leaderboard/pool_arms.py ...`; standard
errors from the spread measured between arms that ran the same code (6.5 per request overall, 8.8 on cold
requests, 4.75 on warm ones):

| Set-up | Requests | Overall | Over the reference (1.981) | Cold (on) | Warm (on) |
|---|---|---|---|---|---|
| v9 everywhere (v21 + v22) | 7,186 | **2.356** | +0.375 | 2.957 (2,660) | **2.003** (4,526) |
| v9w cold, v9 warm (v23 + v24) | 7,218 | 2.213 | +0.232 | 2.660 (2,779) | 1.933 (4,439) |
| v16 everywhere (v25 + v26) | 7,268 | 2.216 | +0.235 | 2.988 (2,774) | 1.740 (4,494) |
| v16w cold, v16 warm (v27 + v28) | 7,290 | 2.294 | +0.313 | **3.070** (2,788) | 1.812 (4,502) |

- **Warm, by ranker**: `v9` 1.968 on 8,965 requests, `v16` 1.776 on 8,996: 0.19, 2.7 standard errors. It
  read 3.2 a quarter of an hour earlier; a real lead, not a large one. The reference is at 2.09.
- **Cold, by ranker**: `v16w` 3.07, `v16` 2.99, `v9` 2.96, `v9w` 2.66. The first three are level; `v9w`
  trails `v16w` by 1.7 standard errors. The live-feedback weight x20 did not pay on cold requests.
- **Trend lift at ^0.75**: 2.261 with it on 21,884 requests, 2.295 without on 7,078: -0.03, 0.4 standard
  errors, one trend inside the window.
- **Overall**: no set-up is more than 1.3 standard errors from `v9` everywhere, which is first. What came
  next (`v31`-`v35`) is built on `v9` only.

**The rivals have caught up.** Whole teams, conversion / cold / on time, by half hour (UTC):

| Window | Reference | team_06 | team_14 | team_03 | team_22 | team_42 |
|---|---|---|---|---|---|---|
| 19:00-19:30 | 2.12 | 2.34 / 3.04 / 99.8 | 1.16 / 1.61 / 47.6 | 1.72 / 2.24 / 86.0 | 1.81 / 2.47 / 99.5 | 2.08 / 2.67 / 99.9 |
| 19:30-20:00 | 2.20 | 2.70 / 3.55 / 100 | 2.18 / 2.90 / 100 | 2.38 / 3.25 / 99.9 | 2.22 / 3.00 / 95.9 | 2.27 / 2.99 / 99.8 |
| 20:00-20:30 | 1.96 | 2.28 / 2.84 / 100 | 2.20 / 2.73 / 100 | 2.13 / 2.70 / 100 | 2.06 / 2.62 / 100 | 2.06 / 2.52 / 100 |
| 20:30-20:55 | 2.03 | 2.33 / 3.07 / 99.8 | 2.28 / 2.96 / 100 | 2.28 / 3.02 / 100 | 2.20 / 2.95 / 100 | 2.20 / 2.81 / 100 |

Until 19:30 UTC the next team was 0.25 or more behind and several were losing answers; since then four
teams answer everything and sit within 0.05 to 0.13 of us. Their versions over 19:55-20:55 UTC read like
ours: about 2.9 on cold requests and 1.7 to 1.9 on warm ones (team_14 `v7-hummingbird` 2.27 = 2.90 / 1.87;
team_03 2.22 = 2.86 / 1.81; team_22 2.20 = 2.94 / 1.73; team_42's best arm 2.45 = 3.28 / 1.92 on 3,305
requests). Nobody beats the reference on warm requests (2.15 in that hour): that is the one place left
where a team can pull away, and it is 62 % of the traffic.
