#!/usr/bin/env python3
"""Did lifting a trending subcategory pay? Arms with the trend lift against arms without it, during a trend.

    python realtime_analyisi_leaderboard/trend_read.py --sub "Game Consoles" \
        --since "2026-11-14 19:30:00" --until "2026-11-14 20:15:00"                  # UTC

For the requests we served in the window and in the 90 minutes before it: how many products of the trending
subcategory each group of arms put in its lists and in which slots, and what an impression of the trending
subcategory brought (clicks and purchases per 1,000 impressions, every slot weighing the same) against an
impression of anything else. Arms are split by the parity of the version number, as in the overnight
experiment v21-v28: odd = no trend lift, even = lift.

The organisers' expected metric per arm for the same window: `python scripts/arms.py HH:MM HH:MM`.
Read-only: one query on the team's feedback joined with our submissions. Needs pandas (project environment).
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
    req["lift"] = req.mv.map(lambda v: v[-1].isdigit() and int(v[-1]) % 2 == 0)
    imp = req.explode("shown").rename(columns={"shown": "pid"})
    imp["slot"] = imp.groupby("rid").cumcount() + 1
    imp["trend"] = imp.pid.map(subcategory) == sub
    imp["click"] = (imp.pid == imp.clicked).astype(float)
    imp["buy"] = (imp.pid == imp.purchased).astype(float)
    print(f"subcategory {sub}; trend window {since} to {until} UTC; requests we served: {int(req.during.sum()):,} during, "
          f"{int((~req.during).sum()):,} in the minutes before\n")
    print(f"{'':<26} {'requests':>8} {'trend/list':>10} {'lists with':>10} {'in slots':>8} | per 1,000 impressions, slots alike | {'purchases per 100 requests':>27}")
    print(f"{'':<26} {'':>8} {'':>10} {'one':>10} {'1-3':>8} | {'clicks t/other':>16} {'buys t/other':>16} | {'all':>8} {'trend':>8} {'other':>8}")
    for during in (False, True):
        for lift in (False, True):
            r = req[(req.during == during) & (req.lift == lift)]
            d = imp[imp.rid.isin(r.rid)]
            if not len(r):
                continue
            t, o = d[d.trend], d[~d.trend]
            n = len(r)
            label = ("during" if during else "before") + (", lift (even)" if lift else ", no lift (odd)")
            print(f"{label:<26} {n:>8,} {len(t) / n:10.2f} {100 * t.rid.nunique() / n:9.1f}% {100 * (t.slot <= 3).mean() if len(t) else 0:7.1f}% | "
                  f"{by_slot(t, 'click'):7.1f} /{by_slot(o, 'click'):6.1f} {by_slot(t, 'buy'):8.2f} /{by_slot(o, 'buy'):5.2f} | "
                  f"{100 * d.buy.sum() / n:8.2f} {100 * t.buy.sum() / n:8.2f} {100 * o.buy.sum() / n:8.2f}   ({int(t.click.sum())} clicks, {int(t.buy.sum())} purchases on trend products)")


if __name__ == "__main__":
    main()
