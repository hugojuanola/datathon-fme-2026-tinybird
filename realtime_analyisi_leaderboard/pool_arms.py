#!/usr/bin/env python3
"""Pool the output of scripts/arms.py by groups of versions: overall, on cold and on warm requests (stdlib only).

    python scripts/arms.py 17:45 20:15 | python realtime_analyisi_leaderboard/pool_arms.py "v9=21,22" "v9w|v9=23,24" "v16=25,26" "v16w|v16=27,28"
    python scripts/arms.py 21:30 22:15 | python realtime_analyisi_leaderboard/pool_arms.py "no lift=34" "lift ^0.5=35" "lift ^1=31"

Each argument is `label=suffixes`: the versions of our team whose `model_version` ends in `v<suffix>`. Prints,
per group, the requests-weighted expected purchases per 100 requests (the organisers' metric) overall, on
cold and on warm requests, the margin over the reference, and how far each group is from the FIRST group in
standard errors.

The standard errors are a yardstick, not a test. They use the spread per request measured on 14 Nov,
17:45-19:15 UTC, between arms that ran the same code (24 pairs of quarter-hours): 6.5 overall, 8.8 on cold
requests, 4.75 on warm ones, in purchases per 100 requests. So the standard error of a difference between
two groups is spread x sqrt(1/n1 + 1/n2). A window with a trend in it is likely to spread more.
"""
from __future__ import annotations

import sys

SPREAD = {"all": 6.5, "cold": 8.8, "warm": 4.75}


def main() -> None:
    groups = [(a.split("=", 1)[0], tuple(a.split("=", 1)[1].split(","))) for a in sys.argv[1:] if "=" in a]
    rows, ref = {}, None
    for line in sys.stdin:
        p = line.split()
        if len(p) >= 5 and p[0] == "reference":
            ref = (float(p[2]), float(p[3]), float(p[4]))
        if len(p) >= 8 and p[0].startswith("team_") and "_v" in p[1]:
            rows[p[1].rsplit("_v", 1)[1]] = (int(p[2]), float(p[3]), float(p[4]), float(p[5]), int(p[6]))
    if ref is None or not rows:
        sys.exit("no arms.py table on standard input")
    print(f"{'group':<22} {'requests':>8} {'overall':>8} {'vs ref':>7} {'cold':>7} {'on':>6} {'warm':>7} {'on':>6}   against the first group, in standard errors")
    print(f"{'reference':<22} {'':>8} {ref[0]:8.3f} {'':>7} {ref[1]:7.3f} {'':>6} {ref[2]:7.3f}")
    first = None
    for label, keys in groups:
        r = [rows[k] for k in keys if k in rows]
        if not r:
            print(f"{label:<22} no such version in the window")
            continue
        n, c = sum(x[0] for x in r), sum(x[4] for x in r)
        value = {"all": sum(x[0] * x[1] for x in r) / n, "cold": sum(x[4] * x[2] for x in r) / max(c, 1),
                 "warm": sum((x[0] - x[4]) * x[3] for x in r) / max(n - c, 1)}
        size = {"all": n, "cold": c, "warm": n - c}
        if first is None:
            first, against = (value, size), ""
        else:
            against = "   " + "  ".join(
                f"{k} {value[k] - first[0][k]:+.2f} ({(value[k] - first[0][k]) / (SPREAD[k] * (1 / max(size[k], 1) + 1 / max(first[1][k], 1)) ** 0.5):+.1f} se)"
                for k in ("all", "cold", "warm"))
        print(f"{label:<22} {n:>8,} {value['all']:8.3f} {value['all'] - ref[0]:+7.3f} {value['cold']:7.3f} {c:>6,} {value['warm']:7.3f} {n - c:>6,}{against}")


if __name__ == "__main__":
    main()
