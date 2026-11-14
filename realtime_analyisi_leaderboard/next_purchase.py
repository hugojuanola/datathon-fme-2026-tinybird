#!/usr/bin/env python3
"""What do shoppers buy right after we answer them, and did we show it?

    python realtime_analyisi_leaderboard/next_purchase.py --since "2026-11-14 17:45:00"     # UTC

For every organic purchase (shop.events) made within 30 minutes after a request we served, it takes the
latest such request and asks whether the purchased product was among our 10. For the ones we missed it
describes the product from the shopper's side — attributes they like, a subcategory they buy in, how popular
it is inside its subcategory, what it shares with the last view — to tell a ranking problem (we had the
signal and ranked it out) from a blind spot (nothing pointed at it).

Organic purchases are a proxy for intent, not the carousel's own sales: products the shopper had already
bought are set aside, because the carousel does not sell them again. Read-only: two queries on the live
tables, joined locally to the cache in $SKORE_DATA_DIR/eda. Needs pandas (project environment).
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
sys.path.insert(0, str(HERE))
from ab_mechanism import NEW_PRODUCTS, PRIOR, attribute_vocabulary  # noqa: E402
from rt import load_env, query  # noqa: E402

SERVED = """
SELECT toString(r.ts) AS ts, r.u AS u, r.is_new AS is_new, r.page AS page, r.rv AS rv, s.mv AS mv, f.shown AS shown
FROM (SELECT request_id::String AS rid, user_id::String AS u, is_new_user::Bool AS is_new, context.page::String AS page,
             ts::DateTime64(3) AS ts, arrayMap(v -> v.product_id::String, recent_views::Array(JSON)) AS rv
      FROM shop.requests WHERE ts > '{since}'::DateTime64(3) - INTERVAL 1 MINUTE) AS r
INNER JOIN (SELECT request_id::String AS rid, shown::Array(String) AS shown
            FROM {team}.feedback WHERE served_by = 'team' AND ts > '{since}') AS f ON f.rid = r.rid
INNER JOIN (SELECT request_id::String AS rid, any(model_version::String) AS mv FROM {team}.submissions GROUP BY rid) AS s
        ON s.rid = r.rid"""
BOUGHT = """
SELECT user_id::String AS u, product_id::String AS pid, toString(ts::DateTime64(3)) AS ts
FROM shop.events WHERE event_type = 'purchase' AND ts > '{since}'"""


def share(mask: pd.Series) -> str:
    return f"{100 * mask.mean():5.1f}%" if len(mask) else "   n/a"


def main() -> None:
    since = sys.argv[sys.argv.index("--since") + 1]
    load_env()
    team = os.environ["TEAM_ID"]
    req = pd.DataFrame(query(SERVED.format(team=team, since=since))["data"])
    buy = pd.DataFrame(query(BOUGHT.format(since=since))["data"])
    for d in (req, buy):
        d["ts"] = pd.to_datetime(d.ts.str[:23])
    req["is_new"] = req.is_new.astype(bool)
    cache = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data")) / "eda"
    cat = pd.read_parquet(cache / "catalog.parquet", columns=["product_id", "category", "subcategory", "description"])
    new = pd.DataFrame(query(NEW_PRODUCTS)["data"])
    cat = pd.concat([cat, new], ignore_index=True).drop_duplicates("product_id").set_index("product_id")
    voc = attribute_vocabulary(cat.description)
    index = {a: i for i, a in enumerate(sorted(voc))}

    def attrs_of(text: str) -> list[int]:
        text, out = text.lower(), []
        for a in voc:
            if a in text:
                out.append(index[a])
                text = text.replace(a, " ")
        return out

    pa = {p: attrs_of(t) for p, t in cat.description.items()}
    sub = cat.subcategory.to_dict()
    hist = pd.read_parquet(cache / "purchases.parquet", columns=["user_id", "product_id"])
    counts = hist.product_id.value_counts()
    rank = counts.rank(ascending=False, method="first").groupby(counts.index.map(sub)).rank(method="first")   # rank inside the subcategory
    g = np.zeros(len(index))
    for p, c in counts.items():
        for i in pa.get(p, []):
            g[i] += c
    g /= counts.sum()
    hist = hist[hist.user_id.isin(buy.u.unique())]
    profile: dict[str, np.ndarray] = {}
    for u, p in zip(hist.user_id, hist.product_id):
        v = profile.setdefault(u, np.zeros(len(index)))
        for i in pa.get(p, []):
            v[i] += 1
    n_pur = hist.groupby("user_id").size().to_dict()
    bought = set(zip(hist.user_id, hist.product_id))
    bought_sub = set(zip(hist.user_id, hist.product_id.map(sub)))

    def affinity(u: str, item: str) -> float:
        ia, c = pa.get(item), profile.get(u)
        if not ia or c is None:
            return np.nan
        return float(np.mean([((c[i] + PRIOR * g[i]) / (n_pur[u] + PRIOR)) / g[i] for i in ia]))

    req["rts"] = req.ts
    m = pd.merge_asof(buy.sort_values("ts"), req.sort_values("ts"), on="ts", by="u", direction="backward",
                      tolerance=pd.Timedelta(minutes=30), suffixes=("", "_r")).dropna(subset=["mv"])
    m["is_new"] = m.is_new.astype(bool)
    m["in_list"] = [p in s for p, s in zip(m.pid, m.shown)]
    m["repeat"] = [(u, p) in bought for u, p in zip(m.u, m.pid)]
    m["last"] = m.rv.map(lambda a: a[-1] if len(a) else None)
    m["family"] = m.mv.map(lambda v: {"21": "v9", "22": "v9", "23": "routed v9", "24": "routed v9", "25": "v16", "26": "v16",
                                      "27": "routed v16", "28": "routed v16"}.get(v[-2:], v.replace("skore_money_", "")))
    print(f"organic purchases since {since} UTC: {len(buy):,}; within 30 minutes after a request we served: {len(m):,}\n")
    for kind, d in (("known", m[~m.is_new]), ("new", m[m.is_new])):
        s = d[~d.repeat]
        print(f"{kind} shoppers: {len(d):,} next purchases, {share(d.repeat).strip()} of products already bought before (set aside); "
              f"{len(s):,} left; in our 10: {share(s.in_list).strip()}")
        t = s.groupby("family").in_list.agg(["size", "mean"])
        print("   by ranker set-up: " + " | ".join(f"{k} {100 * r['mean']:.1f}% of {int(r['size'])}" for k, r in t.iterrows() if r["size"] >= 80))
    k = m[~m.is_new & ~m.repeat].copy()
    k["aff"] = [affinity(u, p) for u, p in zip(k.u, k.pid)]
    k["sub"] = [(u, sub.get(p)) in bought_sub for u, p in zip(k.u, k.pid)]
    k["rank"] = k.pid.map(rank)
    k["new_product"] = ~k.pid.isin(counts.index)
    k["shared"] = [len(set(pa.get(p, [])) & set(pa.get(lv, []))) if lv else -1 for p, lv in zip(k.pid, k["last"])]
    k["same_cat"] = [bool(lv) and cat.category.get(p) == cat.category.get(lv) for p, lv in zip(k.pid, k["last"])]
    k["band"] = pd.cut(k.aff, [0, 1.0, 1.25, 1.75, 99], labels=["under 1.0", "1.0-1.25", "1.25-1.75", "over 1.75"])
    k["rk"] = pd.cut(k["rank"], [0, 3, 10, 30, 1e9], labels=["top 3", "4-10", "11-30", "31+"])
    miss, hit = k[~k.in_list], k[k.in_list]
    print(f"\nKNOWN shoppers, products not bought before: {len(k):,} next purchases, {len(hit):,} shown, {len(miss):,} missed")
    print("\n1) attribute affinity of the purchased product — share of the purchases, and how often we showed it:")
    t = k.groupby("band", observed=True).agg(purchases=("in_list", "size"), shown_pct=("in_list", lambda s: round(100 * s.mean(), 1)))
    t["share_pct"] = (100 * t.purchases / len(k)).round(1)
    print(t.to_string())
    print("\n2) is it in a subcategory the shopper has bought in? × popularity rank inside its subcategory:")
    t = k.groupby(["sub", "rk"], observed=True).agg(purchases=("in_list", "size"), shown_pct=("in_list", lambda s: round(100 * s.mean(), 1)))
    t["share_pct"] = (100 * t.purchases / len(k)).round(1)
    print(t.to_string())
    print("\n3) the missed purchases, by what pointed at them:")
    strong = miss[(miss.aff > 1.25) & miss["sub"]]
    some = miss[((miss.aff > 1.25) | miss["sub"]) & ~((miss.aff > 1.25) & miss["sub"])]
    none = miss[~(miss.aff > 1.25) & ~miss["sub"]]
    for label, d in (("liked attributes AND a bought subcategory (we had the signal: a ranking problem)", strong),
                     ("only one of the two", some), ("neither (nothing in the purchase history pointed at it)", none)):
        print(f"   {share(pd.Series(miss.index.isin(d.index))).strip():>6} {label}; of these, top-10 of their subcategory: "
              f"{share(d['rank'] <= 10).strip()}, same category as the last view: {share(d.same_cat).strip()}, "
              f"share an attribute with the last view: {share(d.shared >= 1).strip()}, added during the event: {share(d.new_product).strip()}")
    print(f"\n4) with a recent view ({share(k.shared >= 0).strip()} of them): the purchase shares 0 / 1 / 2 attributes with the last view in "
          f"{share(k[k.shared >= 0].shared == 0).strip()} / {share(k[k.shared >= 0].shared == 1).strip()} / {share(k[k.shared >= 0].shared == 2).strip()}"
          f" (two random products: about 81% / 18% / 1%); same category as the last view: {share(k[k.shared >= 0].same_cat).strip()}")
    print(f"5) minutes between the request and the purchase, median: {(k.ts - k.rts).dt.total_seconds().median() / 60:.1f}")


if __name__ == "__main__":
    main()
