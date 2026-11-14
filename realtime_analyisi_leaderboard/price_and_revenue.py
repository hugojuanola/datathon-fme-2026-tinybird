#!/usr/bin/env python3
"""What price does to a sale on our carousel, and where the revenue of a request comes from.

    python realtime_analyisi_leaderboard/price_and_revenue.py --since "2026-11-14 15:30:00"     # UTC

Revenue per request is the tie-breaker of the final and one of the three numbers on the board. This reads
our own feedback (every impression we served: slot, price, clicked, purchased) to answer: do dearer products
sell less per impression at the same slot, how much does one impression of each price band bring, where in
the list do we put the dear products, and how concentrated the revenue is (which is why the revenue of a
small arm over a quarter of an hour is a lottery).

Read-only: one query on the team's feedback joined with the requests and our submissions, one on the
catalogue updates for current prices; the rest is local. Needs pandas (project environment).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
from rt import load_env, query  # noqa: E402

SERVED = """
SELECT f.rid AS rid, r.is_new AS is_new, r.page AS page, s.mv AS mv, f.shown AS shown, f.clicked AS clicked, f.purchased AS purchased
FROM (SELECT request_id::String AS rid, shown::Array(String) AS shown, clicked::String AS clicked, purchased::String AS purchased
      FROM {team}.feedback WHERE served_by = 'team' AND ts > '{since}') AS f
INNER JOIN (SELECT request_id::String AS rid, is_new_user::Bool AS is_new, context.page::String AS page
            FROM shop.requests WHERE ts > '{since}'::DateTime64(3) - INTERVAL 1 MINUTE) AS r ON r.rid = f.rid
INNER JOIN (SELECT request_id::String AS rid, any(model_version::String) AS mv FROM {team}.submissions GROUP BY rid) AS s
        ON s.rid = f.rid"""
PRICES = """
SELECT product_id::String AS product_id, argMax(price_eur::Float64, ts::DateTime64(3)) AS price_eur
FROM shop.catalog_updates GROUP BY product_id"""
BANDS = [0, 15, 30, 60, 120, 1e9]
LABELS = ["under 15", "15-30", "30-60", "60-120", "over 120"]


def by_slot(d: pd.DataFrame, value: str) -> float:
    """Mean of `value` with every slot weighing the same, so a band that sits in good slots gets no credit for them."""
    return float(d.groupby("slot")[value].mean().reindex(range(1, 11)).mean())


def main() -> None:
    since = sys.argv[sys.argv.index("--since") + 1]
    load_env()
    team = os.environ["TEAM_ID"]
    req = pd.DataFrame(query(SERVED.format(team=team, since=since))["data"])
    cache = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data")) / "eda"
    price = pd.read_parquet(cache / "catalog.parquet", columns=["product_id", "price_eur"]).set_index("product_id").price_eur
    live = pd.DataFrame(query(PRICES)["data"]).set_index("product_id").price_eur.astype(float)
    price = pd.concat([price[~price.index.isin(live.index)], live])
    req["is_new"] = req.is_new.astype(bool)
    imp = req.explode("shown").rename(columns={"shown": "pid"})
    imp["slot"] = imp.groupby("rid").cumcount() + 1
    imp["price"] = imp.pid.map(price)
    imp["click"] = (imp.pid == imp.clicked).astype(float)
    imp["buy"] = (imp.pid == imp.purchased).astype(float)
    imp["eur"] = imp.buy * imp.price
    imp = imp.dropna(subset=["price"])
    imp["band"] = pd.cut(imp.price, BANDS, labels=LABELS)
    n_req, n_buy = len(req), int(imp.buy.sum())
    print(f"requests we served since {since} UTC: {n_req:,}; impressions with a price: {len(imp):,}; clicks {int(imp.click.sum()):,}; "
          f"purchases {n_buy:,}; realised {100 * n_buy / n_req:.2f} purchases and {imp.eur.sum() / n_req:.3f} EUR per request... "
          f"({imp.eur.sum() / max(n_buy, 1):.1f} EUR per purchase)\n")

    print("1) by price band, every slot weighing the same (rates per 1,000 impressions):")
    print(f"   {'band EUR':<10} {'impr share':>10} {'clicks':>7} {'purchases':>9} {'buy|click':>9} {'EUR':>7}   purchases, raw count")
    for b in LABELS:
        d = imp[imp.band == b]
        clicks = d.click.sum()
        print(f"   {b:<10} {100 * len(d) / len(imp):9.1f}% {1000 * by_slot(d, 'click'):7.1f} {1000 * by_slot(d, 'buy'):9.2f} "
              f"{100 * d.buy.sum() / max(clicks, 1):8.1f}% {1000 * by_slot(d, 'eur'):7.1f}   {int(d.buy.sum())}")

    print("\n2) where we put the dear products, and what each slot brings:")
    print(f"   {'slots':<6} {'mean EUR':>8} {'median':>7} {'over 60 EUR':>11} {'clicks/1000':>11} {'purchases/1000':>14} {'EUR/1000':>9}")
    for label, lo, hi in (("1", 1, 1), ("2-3", 2, 3), ("4-6", 4, 6), ("7-10", 7, 10)):
        d = imp[imp.slot.between(lo, hi)]
        print(f"   {label:<6} {d.price.mean():8.1f} {d.price.median():7.1f} {100 * (d.price > 60).mean():10.1f}% {1000 * d.click.mean():11.1f} "
              f"{1000 * d.buy.mean():14.2f} {1000 * d.eur.mean():9.1f}")

    bought = imp[imp.buy == 1]
    lists = imp.groupby("rid").price.mean()
    ratio = (bought.price / bought.rid.map(lists)).median()
    top = bought.price.sort_values(ascending=False)
    print(f"\n3) the purchases: mean price {bought.price.mean():.1f} EUR, median {bought.price.median():.1f}; shown products: mean "
          f"{imp.price.mean():.1f}, median {imp.price.median():.1f}; a purchased product costs {ratio:.2f} times the mean of its own list (median)")
    print(f"   revenue concentration: the dearest 10% of the purchases bring {100 * top.head(max(len(top) // 10, 1)).sum() / top.sum():.0f}% of the revenue; "
          f"the dearest 1% bring {100 * top.head(max(len(top) // 100, 1)).sum() / top.sum():.0f}%")
    rng = np.random.default_rng(0)
    per_req = imp.groupby("rid").agg(eur=("eur", "sum"), buy=("buy", "sum"))
    per_req = per_req.reindex(req.rid).fillna(0.0)
    for size in (185, 1000, 4000):
        e = [per_req.eur.to_numpy()[rng.integers(0, len(per_req), size)].mean() for _ in range(2000)]
        c = [100 * per_req.buy.to_numpy()[rng.integers(0, len(per_req), size)].mean() for _ in range(2000)]
        print(f"   realised numbers of a random {size:>5} requests, 5th to 95th percentile: purchases per 100 {np.percentile(c, 5):.2f} to "
              f"{np.percentile(c, 95):.2f}; EUR per request {np.percentile(e, 5):.2f} to {np.percentile(e, 95):.2f}")

    print("\n4) by kind of shopper and by ranker family of the night arms (v21-v24 rank warm requests with v9, v25-v28 with v16):")
    imp["family"] = imp.mv.map(lambda v: "v9 family" if v[-2:] in ("21", "22", "23", "24") else "v16 family" if v[-2:] in ("25", "26", "27", "28") else None)
    print(f"   {'group':<22} {'requests':>8} {'EUR slots 1-3':>13} {'EUR all slots':>13} {'EUR purchased':>13} {'purchases/100':>13} {'EUR/request':>11}")
    groups = [("new shoppers", imp[imp.is_new]), ("known shoppers", imp[~imp.is_new])]
    groups += [(f"{f}, {k}", imp[(imp.family == f) & (imp.is_new == new)]) for f in ("v9 family", "v16 family") for k, new in (("new", True), ("known", False))]
    for label, d in groups:
        n = d.rid.nunique()
        if n:
            print(f"   {label:<22} {n:>8,} {d[d.slot <= 3].price.mean():13.1f} {d.price.mean():13.1f} {d[d.buy == 1].price.mean():13.1f} "
                  f"{100 * d.buy.sum() / n:13.2f} {d.eur.sum() / n:11.3f}")

    # Table 1 compares products across requests, and dear products are shown more in requests that convert
    # anyway. This one stays inside each list: given that the shopper clicked (bought) something from these
    # ten, is it a dear one more often than its slot alone predicts?
    print("\n5) inside a list: share of the clicked / purchased products above a price, against what the slots alone predict:")
    print(f"   {'events':<24} {'n':>6} " + " ".join(f"{'over ' + str(t) + ': actual / by slot':>30}" for t in (30, 60, 120)))
    subsets = [("all", imp), ("new shoppers", imp[imp.is_new]), ("known shoppers", imp[~imp.is_new]),
               ("v9 family", imp[imp.family == "v9 family"]), ("v16 family", imp[imp.family == "v16 family"])]
    for flag, name in (("click", "clicks"), ("buy", "purchases")):
        weight = imp.groupby("slot")[flag].mean()
        for label, sub in subsets:
            rids = sub.loc[sub[flag] == 1, "rid"].unique()
            if len(rids) < 80:
                continue
            d = sub[sub.rid.isin(rids)].copy()
            d["w"] = d.slot.map(weight)
            d["w"] /= d.groupby("rid").w.transform("sum")
            cells = []
            for t in (30, 60, 120):
                dear = d.price > t
                expected = float((d.w * dear).sum() / len(rids))
                actual = float(dear[d[flag] == 1].mean())
                se = (actual * (1 - actual) / len(rids)) ** 0.5
                cells.append(f"{100 * actual:5.1f}% / {100 * expected:5.1f}%  ({(actual - expected) / max(se, 1e-9):+.1f} se)")
            print(f"   {name + ', ' + label:<24} {len(rids):>6} " + " ".join(f"{c:>30}" for c in cells))


if __name__ == "__main__":
    main()
