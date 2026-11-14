# 14 Nov, 17:10 CET — above the reference on the hourly board

## How much is missing: nothing — we are ahead

Official board (expected purchases per 100 requests), 17:06 CET:

| Window | team_06 | Reference | Difference | Cold: us / reference | On time | Best rival |
|---|---|---|---|---|---|---|
| Last hour | **2.199** | 2.102 | **+0.097** | 2.88 / 1.90 | 99.7% | team_26 1.89 |
| Last 15 minutes | **2.529** | 2.263 | **+0.266** | 3.35 / 2.05 | 100% | team_26 2.06 |

The trend on the hourly board: 1.53 (15:37) → 1.68 (16:01) → 1.80 (16:22) → 2.00 (16:42) → 2.03 (16:52) →
**2.20 (17:06)**, while the reference stayed between 2.06 and 2.17. The 15-minute board has been above the
reference three readings in a row (+0.12, +0.13, +0.27). Revenue per request 1.10 € against 0.91 €.

## What is live and how it converts (our own feedback, since 16:41 CET)

| Arm | Period (CET) | Known shoppers | New shoppers | All |
|---|---|---|---|---|
| `skore_money_v8` | 16:41–16:58 | 2.13% (15 / 703) | 3.77% (10 / 265) | 2.58% (25 / 968) |
| `skore_money_v8c` | 16:41–16:58 | 1.88% (12 / 638) | 3.15% (9 / 286) | 2.27% (21 / 924) |
| `skore_money_v9` | 16:41–17:06 | 1.91% (19 / 994) | 3.89% (16 / 411) | 2.49% (35 / 1,405) |
| `skore_money_v9d` | 16:58–17:06 | 2.88% (9 / 312) | 4.83% (7 / 145) | 3.50% (16 / 457) |
| `skore_money_v9w` | 16:58–17:06 | 1.34% (4 / 298) | 6.06% (8 / 132) | 2.79% (12 / 430) |
| exploration | 16:41–16:58 | 2.97% (6 / 202) | 0 / 97 | 2.01% (6 / 299) |

All arms together: 2.56% (115 purchases in 4,487 requests). No variant is distinguishable from another yet
(two standard errors are about ±1 point per arm); the family as a whole is clearly above where v5 was
(1.7–1.9%). Known shoppers are at about 2% in every arm that has run for more than a few minutes, up from
1.5% an hour ago — the stretch since 16:41 is a good one for everybody, so part of this is the period.

Lists are unchanged in kind: 9–12% of known-shopper impressions with low attribute affinity, 54–57% in a
bought subcategory.

## Reliability: one thing to fix before the final

Since 16:41 CET 33 of 4,461 requests went unanswered (0.7%), and the server's last minute shows 4 failed
polls, 4 failed inserts and one poll that took 10.6 s. The laptop's upload is free of calls, browser and
OneDrive now; what is left is the assistant sessions. This watch session is by now a very long conversation,
and each step it takes uploads all of it — megabytes — which is the kind of burst measured at 15:30 (300–800
KB/s for several seconds). A tick of this watch costs a handful of such bursts.

For the final (Sunday 10:00–12:00 CET) the watch should not run from a long session on the serving laptop:
either a fresh, short session, or another machine, or no watch at all during the two hours — `tick.py` and
`ab_mechanism.py` can be run by hand from any machine with the key.

## What this means

- The goal "reach the reference" is met on the board in practice conditions, with exploration still on at
  about 10% of traffic.
- The lead is largest on cold requests (2.88 against 1.90), which is where the final will be decided if it
  brings mostly new shoppers.
- Still unpublished: the oracle. The reference is not the ceiling; there is no measure yet of how far above
  it the best possible list is.
