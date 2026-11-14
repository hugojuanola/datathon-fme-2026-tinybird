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
