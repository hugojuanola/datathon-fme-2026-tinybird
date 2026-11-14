#!/usr/bin/env python3
"""What did each arm do with a trending subcategory, and what did it get for it?

    python realtime_analyisi_leaderboard/trend_read.py --sub "Game Consoles" \
        --since "2026-11-14 19:30:00" --until "2026-11-14 20:15:00"                              # UTC
    python realtime_analyisi_leaderboard/trend_read.py --sub "Face Cream" \
        --since "2026-11-14 21:30:00" --until "2026-11-14 22:15:00" \
        --groups "v9=31" "v9 x organic=32" "organic, new x1.5=36" "v9b=33"

For the requests we served in the window and in the 90 minutes before it, per group of arms: how many
products of the trending subcategory went into a list and in which slots, what an impression of the
trending subcategory brought (clicks and purchases per 1,000 impressions, every slot weighing the same)
against an impression of anything else, and the realised purchases per 100 requests split into the two.
Then, inside the lists that hold a trend product, whether it is chosen more than its slot predicts; and
whether the second and third trend product of a list still sell like the first.

`--groups "label=suffix,suffix" ...` names the arms by the end of their version (`31` = `skore_money_v31`).
Without it the split is odd against even versions, which meant lift off against lift on for v21-v28 only.

The organisers' expected metric per arm for the same window: `python scripts/arms.py HH:MM HH:MM`, pooled
with pool_arms.py. Read-only: one query on the team's feedback joined with our submissions. Needs pandas.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))
from ab_mechanism import NEW_PRODUCTS  # noqa: E402
from rt import load_env, query  # noqa: E402

SERVED = """
SELECT f.rid AS rid, f.during AS during, s.mv AS mv, f.shown AS shown, f.clicked AS clicked, f.purchased AS purchased
FROM (SELECT request_id::String AS rid, ts::DateTime64(3) > '{since}' AS during, shown::Array(String) AS shown,
             clicked::String AS clicked, purchased::String AS purchased
      FROM {team}.feedback
      WHERE served_by = 'team' AND ts > '{since}'::DateTime64(3) - INTERVAL {before} MINUTE AND ts <= '{until}') AS f
INNER JOIN (SELECT request_id::String AS rid, any(model_version::String) AS mv FROM {team}.submissions GROUP BY rid) AS s
        ON s.rid = f.rid"""


def arg(name: str, default: str | None = None) -> str:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def groups() -> list[tuple[str, tuple[str, ...]]] | None:
    if "--groups" not in sys.argv:
        return None
    out, i = [], sys.argv.index("--groups") + 1
    while i < len(sys.argv) and not sys.argv[i].startswith("--"):
        label, _, suffixes = sys.argv[i].partition("=")
        out.append((label, tuple(suffixes.split(","))))
        i += 1
    return out


def by_slot(d: pd.DataFrame, value: str) -> float:
    """Per 1,000 impressions, every slot that has impressions weighing the same."""
    return 1000 * float(d.groupby("slot")[value].mean().reindex(range(1, 11)).mean()) if len(d) else float("nan")


def main() -> None:
    sub, since, until = arg("--sub"), arg("--since"), arg("--until")
    load_env()
    req = pd.DataFrame(query(SERVED.format(team=os.environ["TEAM_ID"], since=since, until=until, before=arg("--before", "90")))["data"])
    cache = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data")) / "eda"
    cat = pd.read_parquet(cache / "catalog.parquet", columns=["product_id", "subcategory"])
    new = pd.DataFrame(query(NEW_PRODUCTS)["data"])[["product_id", "subcategory"]]
    subcategory = pd.concat([cat, new], ignore_index=True).drop_duplicates("product_id").set_index("product_id").subcategory
    req["during"] = req.during.astype(bool)
    spec = groups()
    if spec:
        suffix = req.mv.map(lambda v: v.rsplit("_v", 1)[-1])
        req["group"] = suffix.map({s: label for label, suffixes in spec for s in suffixes})
        labels = [label for label, _ in spec]
    else:
        req["group"] = req.mv.map(lambda v: "even versions" if v[-1].isdigit() and int(v[-1]) % 2 == 0 else "odd versions")
        labels = ["odd versions", "even versions"]
    imp = req.explode("shown").rename(columns={"shown": "pid"})
    imp["slot"] = imp.groupby("rid").cumcount() + 1
    imp["trend"] = imp.pid.map(subcategory) == sub
    imp["click"] = (imp.pid == imp.clicked).astype(float)
    imp["buy"] = (imp.pid == imp.purchased).astype(float)
    print(f"subcategory {sub}; trend window {since} to {until} UTC; requests we served: {int(req.during.sum()):,} during, "
          f"{int((~req.during).sum()):,} in the minutes before\n")
    print(f"{'':<30} {'requests':>8} {'trend/list':>10} {'lists with':>10} {'slot 1 is':>9} | per 1,000 impressions, slots alike | {'purchases per 100 requests':>27}")
    print(f"{'':<30} {'':>8} {'':>10} {'one':>10} {'trend':>9} | {'clicks t/other':>16} {'buys t/other':>16} | {'all':>8} {'trend':>8} {'other':>8}")
    for during in (False, True):
        for label in labels:
            r = req[(req.during == during) & (req.group == label)]
            if len(r) < 50:
                continue
            d = imp[imp.rid.isin(r.rid)]
            t, o = d[d.trend], d[~d.trend]
            n = len(r)
            print(f"{('during, ' if during else 'before, ') + label:<30} {n:>8,} {len(t) / n:10.2f} {100 * t.rid.nunique() / n:9.1f}% "
                  f"{100 * (t.slot == 1).sum() / n:8.1f}% | {by_slot(t, 'click'):7.1f} /{by_slot(o, 'click'):6.1f} {by_slot(t, 'buy'):8.2f} /{by_slot(o, 'buy'):5.2f} | "
                  f"{100 * d.buy.sum() / n:8.2f} {100 * t.buy.sum() / n:8.2f} {100 * o.buy.sum() / n:8.2f}   ({int(t.click.sum())} clicks, {int(t.buy.sum())} purchases on trend products)")

    # The table compares products across requests. This stays inside each list: of the clicks (purchases)
    # made in lists that hold a trend product, the share that went to it, against what the slots alone
    # predict. Above the prediction = the trend products sit too low in those lists; below = too high.
    print("\ninside a list that holds a trend product, during the trend: share of the clicks / purchases that went to it, against the slots' prediction")
    live = imp[imp.during]
    for flag, name in (("click", "clicks"), ("buy", "purchases")):
        weight = live.groupby("slot")[flag].mean()
        for label in labels:
            d = live[live.group == label]
            d = d[d.groupby("rid").trend.transform("any") & d.rid.isin(d.loc[d[flag] == 1, "rid"])].copy()
            n = d.rid.nunique()
            if n < 15:
                continue
            d["w"] = d.slot.map(weight)
            d["w"] /= d.groupby("rid").w.transform("sum")
            expected = float((d.w * d.trend).sum() / n)
            actual = float(d.loc[d[flag] == 1, "trend"].mean())
            se = (expected * (1 - expected) / n) ** 0.5
            print(f"   {name + ', ' + label:<34} {n:>5} lists: actual {100 * actual:5.1f}%  by slot {100 * expected:5.1f}%  "
                  f"({(actual - expected) / max(se, 1e-9):+.1f} se)")

    # Does a list fill up with trend products for nothing? The first trend product of a list (by slot), the
    # second, and the rest, against the other products at the same slots (per 1,000 impressions, slots alike).
    print("\nthe first, second and later trend products of a list, during the trend (all arms together):")
    t = live[live.trend].copy()
    t["nth"] = t.groupby("rid").cumcount() + 1
    for label, d in (("first", t[t.nth == 1]), ("second", t[t.nth == 2]), ("third or later", t[t.nth >= 3])):
        if len(d) < 200:
            print(f"   {label:<15} only {len(d)} impressions")
            continue
        other = live[~live.trend & live.slot.isin(d.slot.unique())]
        same = other.groupby("slot")
        wt = d.slot.value_counts(normalize=True)
        ref_click = 1000 * float((same.click.mean() * wt).sum())
        ref_buy = 1000 * float((same.buy.mean() * wt).sum())
        print(f"   {label:<15} {len(d):>6,} impressions, mean slot {d.slot.mean():.1f}: clicks {1000 * d.click.mean():5.1f} per 1,000 (others at those slots "
              f"{ref_click:5.1f}), purchases {1000 * d.buy.mean():5.2f} (others {ref_buy:5.2f}); {int(d.buy.sum())} purchases")


if __name__ == "__main__":
    main()
