#!/usr/bin/env python3
"""Does it matter WHEN a shopper bought in a subcategory? Tested with the ranker's own prediction held equal.

    python realtime_analyisi_leaderboard/recency_check.py

The ranker describes a known shopper by counts and shares over the 60 days of history: how much of what
they bought is in the product's subcategory, how many purchases. Nothing in it says when. If a purchase of
last week says more (or less) than one of two months ago, the products of recently bought subcategories are
worth more (or less) than their score, and the order inside a list is wrong for known shoppers, which is
where every team is below the reference.

The data: the model session's table of lists v9 was not trained on (14 Nov, 17:00-20:20 UTC), with v9's
predicted click and purchase probability for every product shown ($SKORE_DATA_DIR/cf_carousel.parquet), the
shopper of each list from the local feedback export, and the purchase history with dates from the cache in
$SKORE_DATA_DIR/eda. For each product shown to a shopper with a history: days since their last purchase in
its subcategory, how many purchases they made there, and when the first of them was.

Reads: observed against predicted clicks and purchases by those bands, and a conditional logit inside each
clicked (bought) list on the slot, log of v9's prediction and the bands.

Read-only and light: local files only, no model is run. Needs pandas.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from list_effects import logit, ratio_table  # noqa: E402

END = pd.Timestamp("2026-11-14 07:00:00")       # the history stops here; the event starts two hours later


def main() -> None:
    try:
        from reco.priority import background
        background()
    except Exception:
        pass
    from offline.build_dataset import live_feedback, load_catalogs
    _, cat = load_catalogs()
    data = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data"))
    df = pd.read_parquet(data / "cf_carousel.parquet", columns=["request", "item", "slot", "click", "buy", "pc", "pb", "s"])
    df = df[df.groupby("request").slot.transform("size") == 10].sort_values(["request", "slot"]).reset_index(drop=True)
    fb = live_feedback()
    df["user"] = fb.user_id.to_numpy()[df.request.to_numpy()]
    df["hour"] = pd.to_datetime(fb.ts_ms.to_numpy()[df.request.to_numpy()], unit="ms").hour
    df["sub"] = np.array(cat.sub_names)[np.asarray(cat.sub)[df.item.to_numpy()]]
    df["category"] = np.array(cat.cat_names)[np.asarray(cat.cat)[df.item.to_numpy()]]

    hist = pd.read_parquet(data / "eda" / "purchases.parquet")
    names = pd.read_parquet(data / "eda" / "catalog.parquet", columns=["product_id", "subcategory", "category"]).set_index("product_id")
    hist = hist[hist.user_id.isin(df.user.unique())].copy()
    hist["sub"] = hist.product_id.map(names.subcategory)
    hist["category"] = hist.product_id.map(names.category)
    hist["days"] = (END - pd.to_datetime(hist.ts.str[:19])).dt.total_seconds() / 86400
    total = hist.groupby("user_id").agg(u_n=("days", "size"), u_last=("days", "min"))
    by_sub = hist.groupby(["user_id", "sub"]).agg(n=("days", "size"), last=("days", "min"), first=("days", "max")).reset_index()
    by_cat = hist.groupby(["user_id", "category"]).agg(cat_last=("days", "min")).reset_index()
    df = df.merge(by_sub, left_on=["user", "sub"], right_on=["user_id", "sub"], how="left").drop(columns="user_id")
    df = df.merge(by_cat, left_on=["user", "category"], right_on=["user_id", "category"], how="left").drop(columns="user_id")
    df = df.join(total, on="user").sort_values(["request", "slot"]).reset_index(drop=True)
    known = df[df.u_n.notna()].copy()
    print(f"lists of shoppers with a purchase history: {known.request.nunique():,} of {df.request.nunique():,}; clicks {int(known.click.sum()):,}; "
          f"purchases {int(known.buy.sum()):,}; impressions in a subcategory the shopper bought in: {100 * known.n.notna().mean():.1f}%")

    known["when"] = pd.cut(known["last"].fillna(999), [-1, 7, 21, 42, 70, 1000],
                           labels=["last purchase there: 0-7 days ago", "8-21 days", "22-42 days", "43-60 days", "never bought there"])
    known["count"] = pd.cut(known.n.fillna(0), [-1, 0, 1, 2, 4, 1000], labels=["no purchase there", "1 purchase", "2", "3-4", "5 or more"])
    known["cat_when"] = pd.cut(known.cat_last.fillna(999), [-1, 7, 21, 70, 1000],
                               labels=["last purchase in the category: 0-7 days ago", "8-21 days", "22-60 days", "never in the category"])
    known["active"] = pd.cut(known.u_last, [-1, 3, 14, 70], labels=["shopper's last purchase: 0-3 days ago", "4-14 days", "15-60 days"])
    ratio_table(known, "when", "1) by the time since the shopper's last purchase in the product's subcategory")
    ratio_table(known, "count", "2) by the number of purchases there (v9 has this one: the yardstick)")
    ratio_table(known[known.n.notna()], ["count", "when"], "   both together, products of bought subcategories only")
    ratio_table(known, "cat_when", "3) by the time since the last purchase in the product's category")
    ratio_table(known, "active", "4) by how recently the shopper bought anything (a property of the list, not of the product)")
    ratio_table(df, "hour", "5) all lists, by hour of the day UTC (does v9 age?)")

    known["recent"] = (known["last"] <= 7).astype(float)
    known["mid"] = ((known["last"] > 7) & (known["last"] <= 21)).astype(float)
    known["old"] = (known["last"] > 42).astype(float)
    for flag, pred, what in (("click", "pc", "clicks"), ("buy", "pb", "purchases")):
        logit(known, flag, pred, ["recent", "mid", "old"],
              f"6) conditional logit on {what}: slot + v9's prediction + when the last purchase in the subcategory was (against 22-42 days or never)")


if __name__ == "__main__":
    main()
