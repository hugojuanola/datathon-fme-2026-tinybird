# The trend lift, read on a real trend; and the warm ranker (14 Nov, 21:30 CET)

**In one line**: on the first trend with the lift live (Game Consoles, 19:30-20:15 UTC) the lift at ^0.75
neither helped nor hurt: 2.60 expected purchases per 100 requests with it, 2.63 without (+0.03 ± 0.20 once
the arms' earlier difference is taken out). The trend products it adds do sell, and the products they push
down lose as much. The same window settled something else: on warm requests `v9` beats `v16`.

## The trend

Organic purchases in Game Consoles went from about 10 to about 100 per five minutes at 19:30:00 UTC, stayed
there (11 % of all purchases) and fell back to 4 at 20:15:00. The detector logged it 41 seconds in, at lift
3.6, and let go a minute and a half after the end. It is the first trend since 15:30 UTC and it kept the
earlier pattern: half past an odd UTC hour, 45 minutes.

## What the lift did

`python realtime_analyisi_leaderboard/trend_read.py --sub "Game Consoles" --since "2026-11-14 19:30:00"
--until "2026-11-14 20:15:00"` (our feedback, realised) and `python scripts/arms.py 19:30 20:15` (expected).
Odd versions have no lift, even versions have it.

| During the trend | Requests | Trend products per list | Lists with one | Purchases per 1,000 impressions, slots alike: trend / other | Realised purchases per 100 requests: all = trend + other | Expected per 100 |
|---|---|---|---|---|---|---|
| No lift (v21, v23, v25, v27) | 1,979 | 0.17 | 11.6 % | 15.79 / 2.98 | 3.18 = 0.25 + 2.93 | 2.632 |
| Lift ^0.75 (v22, v24, v26, v28) | 6,121 | 1.37 | 49.8 % | 4.89 / 2.28 | 2.70 = 0.77 + 1.93 | 2.602 |

In the 105 minutes before the trend both groups ran the same code and showed 0.13 Game Consoles products per
list; the expected metric read 2.186 and 2.122. So the lift's effect on the organisers' number is
(2.602 - 2.632) - (2.122 - 2.186) = **+0.03, with a standard error of about 0.20**. The reference read 2.14.

Three things are measured, and they fit together:

1. **A trend product is wanted.** Inside the lists that hold one, it takes 50.4 % of the clicks where its
   slots predict 32.4 % (224 lists, +5.8 se) and 61.8 % of the purchases where they predict 39.7 % (76
   lists, +3.9 se). In the arms without the lift, the few the ranker picked on its own took 41 % of the
   clicks against 21 % predicted.
2. **The lift delivers them.** Half the lists get one, a third of those in slots 1-3, and they bring +0.52
   purchases per 100 requests (0.77 against 0.25).
3. **The total does not move.** Whatever enters a list pushes the ranker's own candidates down, and slot 1
   alone holds 45 % of our purchases. On the expected metric the others lose what the trend products gain.

So ^0.75 is harmless and, on one trend, worth nothing. This does not say whether more lift or less would be
better: point 1 says the trend products still sit too low, point 3 says moving them up is paid for by the
others. Only arms at different strengths, or a lift that never takes slot 1, can separate the two.

**What to do**: nothing on this evidence. If the two-hour pattern holds there are trends at 21:30, 23:30,
01:30, 03:30, 05:30 and 07:30 UTC; each adds about 8,100 requests, and by Sunday morning the comparison
with and without the lift has a standard error near 0.08. Optional, and only with Javier's go-ahead for a
swap tonight: give half of the even arms a second strength (for instance ^1.5) so the night also measures
the dose.

## The warm ranker: `v9`

`python scripts/arms.py 17:45 20:15`, pooled by the ranker that answers each kind of request:

| Warm requests | Ranker | Requests | Expected purchases per 100 | Reference |
|---|---|---|---|---|
| The night so far | **v9** (v21 to v24) | 8,162 | **1.99** | 2.09 |
| The night so far | v16 (v25 to v28) | 8,151 | 1.76 | 2.09 |
| Trend window only | **v9** | 2,480 | **2.39** | 2.19 |
| Trend window only | v16 | 2,488 | 1.84 | 2.19 |
| Outside the trend | v9 | 5,682 | 1.82 | |
| Outside the trend | v16 | 5,663 | 1.72 | |

A lead of 0.24 on 8,150 requests each is about three standard errors (the spread between arms running the same code is 4.75 per warm request, measured in `pool_arms.py`), in the same direction in and out of
the trend, and with all four `v9` arms at or above 1.99 in the trend window against 1.68 to 2.21 for the
`v16` arms. This passes the bar set in the 20:30 note (more than 0.15 and two standard errors): **warm
requests go to `v9`**. Most of the lead was made during the trend, which is also when the final's points
are made: `v9` was above the reference there (2.39 against 2.19), `v16` well below.

Cold requests are not settled: `v9` 2.97, `v9w` 2.63, `v16` 3.07, `v16w` 3.14 on about 2,500 each
(reference 1.82). The lead of `v16` over `v9` seen at 95 minutes is gone; `v9w` trails `v16w` by 0.51, about
two standard errors.

For the final's single arm, as it stands: `v9` for warm requests; for cold ones `v9`, `v16` or `v16w`,
level so far, and not `v9w`. `v9` everywhere (`v21` / `v22`) is the simplest set-up that satisfies both and
leads the night overall (+0.39 over the reference on 6,551 requests).

## Lenses

- **Generalisation**: the lift is keyed on a subcategory selling above its usual share, whatever it is; the
  final's trends are new ones and the detector does not know the schedule. One trend is one sample.
- **Reference**: in the trend window it read 2.14 overall; we read 2.61 across all arms.
- **Technique**: a boost that reorders a slate has a displacement cost whenever the top slot dominates;
  the usual remedies are to cap the boosted items per slate or to protect the first slot.

## Update, 22:45 CET — Face Cream (21:30 UTC): a trend in views, not in purchases (first 12 minutes)

All arms now carry the lift at full strength (`v31` v9, `v32` v9 x organic, `v33` v9b, `v36` = `v32` with
new products x1.5). The second trend of the evening is not like the first.

| Organic stream, per 5 minutes | Before | During | Ratio |
|---|---|---|---|
| Face Cream views | 35-70 | 274-292 | x5.5 |
| Face Cream carts | 2-4 | 20 | x7 |
| Face Cream purchases | 2-3 | 6-7 | x2.5 (0.8 % of all purchases) |
| Game Consoles purchases (19:30 UTC) | 10 | 100 | x10 (11 % of all purchases) |

The detector reports a lift of 11.1 for Face Cream: it is carried by views and carts on a very small base.

On our carousel, 21:30-21:42 UTC: 1,820 Face Cream impressions, **2 clicks, 0 purchases**. Other products
at the same slots get about 11 clicks and 2 to 3 purchases on that many impressions.

| Arm | Face Cream products per list | Lists with one | Lists with one in slot 1 | Impressions / clicks / purchases |
|---|---|---|---|---|
| `v31` (v9) | 0.25 | 17 % | 1.1 % | 130 / 0 / 0 |
| `v33` (v9b) | 0.27 | 17 % | 1.5 % | 108 / 1 / 0 |
| `v32` (v9 x organic) | 1.74 | 57 % | 13.6 % | 964 / 1 / 0 |
| `v36` (organic, new x1.5) | 1.82 | 57 % | 16.0 % | 618 / 0 / 0 |

v9 multiplied by the lift still leaves these products out of most lists, because it rates them far below
the tenth candidate for most shoppers; the clicks agree with it. The organic factor sees the same spike of
views as the detector and fills more than half of the lists. Sent to the model session at 21:45 UTC with
the suggestion that the lift follow the purchase ratio, with a floor on the number of purchases. The whole
window per arm, with the organisers' metric, follows when the trend ends.

## Correction, 23:00 CET — Face Cream was a real trend; the flaw was in the organic factor, and it is fixed

Two things in the section above were wrong or incomplete, both set right by the model session.

- **It is a trend in purchases too.** My x2.5 compared the trend with the half hour before it, when Face
  Cream was already selling 3.5 times its usual share. Against the day (96 purchases in the 12 hours
  before, 0.67 per five minutes) it is x11 to x12, as the detector said; views x5.5, carts x17. It is a very
  small subcategory: x11 of very little.
- **The cause was the organic model, not the detector.** It learned which product a shopper buys next among
  the candidates the rules retrieve on an ordinary day. Face Cream products were candidates only because the
  lift put them there, so its answer for them meant nothing, and it sent them to the top. Reproduced offline
  on 120 requests with a made-up x10: v9 with the lift 0.24 trending products per list, v9 x organic with the
  lift 3.05 (slot 1 in 24 % of lists), v9 x organic without a trend 0.02.

What stands from the section above is what the carousel showed: 1,820 impressions, 2 clicks, no purchase,
with `v32` and `v36` filling more than half of their lists. That is what made it worth acting on before the
trend ended.

**The fix**, live since 21:51:01 UTC (`reco.recommend.level_trending`, commit 938b995): while a trend runs,
a trending product takes the organic factor of the products v9 scores about as high, so the organic model
has no say on it and it keeps the place v9 x lift gives it. Live after the fix: `v31` 0.21 trending products
per list, `v32` 0.24, `v33` 0.20, `v36` 0.08, none in slot 1. Before: `v32` 2.24 per list (slot 1 in 19 %).

For the reads from here on: `v32` and `v36` count from 21:52 UTC; their 21:30-21:51 window is the flaw, not
the organic factor. In every trend, the first thing to look at is the number of trending products per list
by arm: the arms should be within a factor of two of each other.
