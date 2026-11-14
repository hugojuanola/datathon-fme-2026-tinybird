#!/usr/bin/env python3
"""Read an A/B between model versions: who converts, and whether each arm pulls the levers we measured.

    python realtime_analyisi_leaderboard/ab_mechanism.py --since "2026-11-14 14:55:12"          # UTC
    python realtime_analyisi_leaderboard/ab_mechanism.py --since "2026-11-14 12:40:00" --brand  # brand vs attributes

Per arm, on the requests we served since --since: conversion for new and known shoppers with purchase counts,
and the mechanism — what share of the impressions are products whose attributes the shopper likes, share
attributes with the product just viewed, are in a subcategory the shopper has bought. A version that uses a
lever has to move its share; conversion should follow.

Read-only and light: one query on the live tables, joined locally to the cache in $SKORE_DATA_DIR/eda
(purchases.parquet, catalog.parquet). Needs pandas (project environment).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from rt import load_env, query  # noqa: E402

PRIOR = 5.0   # a shopper's attribute share is shrunk towards everybody's with this many pseudo-purchases

SERVED = """
SELECT toString(r.ts) AS ts, r.u AS u, r.is_new AS is_new, r.rv AS rv, s.mv AS mv, f.shown AS shown,
       f.clicked AS clicked, f.purchased AS purchased
FROM (SELECT request_id::String AS rid, user_id::String AS u, is_new_user::Bool AS is_new, ts::DateTime64(3) AS ts,
             arrayMap(v -> v.product_id::String, recent_views::Array(JSON)) AS rv
      FROM shop.requests WHERE ts > '{since}'::DateTime64(3) - INTERVAL 1 MINUTE) AS r
INNER JOIN (SELECT request_id::String AS rid, shown::Array(String) AS shown, clicked::String AS clicked,
                   purchased::String AS purchased
            FROM {team}.feedback WHERE served_by = 'team' AND ts > '{since}') AS f ON f.rid = r.rid
INNER JOIN (SELECT request_id::String AS rid, any(model_version::String) AS mv FROM {team}.submissions GROUP BY rid) AS s
        ON s.rid = r.rid"""
NEW_PRODUCTS = """
SELECT DISTINCT product_id::String AS product_id, subcategory::String AS subcategory, brand::String AS brand,
       description::String AS description
FROM shop.catalog_updates WHERE change = 'new_product'"""


def attribute_vocabulary(descriptions: pd.Series) -> list[str]:
    """The attribute phrases, read from the two description templates that name them unambiguously."""
    voc = set()
    for text in descriptions:
        m = re.match(r"^From .+? \(.+?\): (.+), (.+)\.$", text) or re.search(r", featuring (.+?)\. Comes with (.+?)\.$", text)
        if m:
            voc.update(re.sub(r"^(an?|the) ", "", a.strip().lower()) for a in m.groups())
    return sorted(voc, key=len, reverse=True)


def main() -> None:
    since = sys.argv[sys.argv.index("--since") + 1]
    load_env()
    team = os.environ["TEAM_ID"]
    d = pd.DataFrame(query(SERVED.format(team=team, since=since))["data"])
    d = d[d.shown.map(len) == 10].reset_index(drop=True)
    d["is_new"] = d.is_new.astype(bool)
    d["ts"] = pd.to_datetime(d.ts.str[:23])
    d["buy"], d["click"] = d.purchased != "", d.clicked != ""
    cache = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data")) / "eda"
    cat = pd.read_parquet(cache / "catalog.parquet", columns=["product_id", "subcategory", "brand", "description"])
    cat = pd.concat([cat, pd.DataFrame(query(NEW_PRODUCTS)["data"])], ignore_index=True).drop_duplicates("product_id")
    cat = cat.set_index("product_id")
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
    sub, brand = cat.subcategory.to_dict(), cat.brand.to_dict()
    pur = pd.read_parquet(cache / "purchases.parquet", columns=["user_id", "product_id"])
    counts = pur.product_id.value_counts()
    g = np.zeros(len(index))
    for p, c in counts.items():
        for i in pa.get(p, []):
            g[i] += c
    g /= counts.sum()
    pur = pur[pur.user_id.isin(d.u.unique())]
    profile: dict[str, np.ndarray] = {}
    for u, p in zip(pur.user_id, pur.product_id):
        v = profile.setdefault(u, np.zeros(len(index)))
        for i in pa.get(p, []):
            v[i] += 1
    n_pur = pur.groupby("user_id").size().to_dict()
    bought = set(zip(pur.user_id, pur.product_id))
    bought_sub = set(zip(pur.user_id, pur.product_id.map(sub)))
    bought_brand = set(zip(pur.user_id, pur.product_id.map(brand)))

    def affinity(u: str, item: str) -> float:
        ia, c = pa.get(item), profile.get(u)
        if not ia or c is None:
            return np.nan
        return float(np.mean([((c[i] + PRIOR * g[i]) / (n_pur[u] + PRIOR)) / g[i] for i in ia]))

    n = len(d)
    e = pd.DataFrame({"req": np.repeat(np.arange(n), 10), "slot": np.tile(np.arange(1, 11), n),
                      "item": np.array(d.shown.tolist()).ravel()})
    for c in ("u", "is_new", "mv", "clicked", "purchased"):
        e[c] = np.repeat(d[c].to_numpy(), 10)
    last = d.rv.map(lambda a: a[-1] if len(a) else None).to_numpy()
    e["last"] = last[e.req.to_numpy()]
    e["b"] = e.item == e.purchased
    e["shared"] = [len(set(pa.get(i, [])) & set(pa.get(lv, []))) if lv and i != lv else np.nan for i, lv in zip(e.item, e["last"])]
    e["new_product"] = ~e.item.isin(counts.index)
    known = e[~e.is_new].copy()
    known = known[[(u, i) not in bought for u, i in zip(known.u, known.item)]]
    known["aff"] = [affinity(u, i) for u, i in zip(known.u, known.item)]
    known["sub"] = [(u, sub.get(i)) in bought_sub for u, i in zip(known.u, known.item)]
    known["brand"] = [(u, brand.get(i)) in bought_brand for u, i in zip(known.u, known.item)]

    print(f"served since {since} UTC: {n:,} requests, last at {d.ts.max():%H:%M:%S}; {len(voc)} attribute phrases\n")
    arms = d.groupby("mv").agg(requests=("buy", "size"), first_seen=("ts", "min"), last_seen=("ts", "max"))
    print(arms.assign(first_seen=arms.first_seen.dt.strftime("%H:%M:%S"), last_seen=arms.last_seen.dt.strftime("%H:%M:%S")).to_string(), "\n")

    conv = d.groupby(["mv", d.is_new.map({True: "new", False: "known"})]).agg(requests=("buy", "size"), clicks=("click", "sum"), buys=("buy", "sum"))
    conv["conv_pct"] = (100 * conv.buys / conv.requests).round(2)
    conv["two_se"] = (200 * np.sqrt((conv.buys / conv.requests) * (1 - conv.buys / conv.requests) / conv.requests)).round(2)
    tot = d.groupby("mv").agg(requests=("buy", "size"), clicks=("click", "sum"), buys=("buy", "sum"))
    tot["conv_pct"] = (100 * tot.buys / tot.requests).round(2)
    tot["two_se"] = (200 * np.sqrt((tot.buys / tot.requests) * (1 - tot.buys / tot.requests) / tot.requests)).round(2)
    print("conversion per arm and kind of shopper (two_se = two standard errors, in points):")
    print(conv.to_string(), "\n")
    print("all shoppers:")
    print(tot.to_string(), "\n")

    mech = known.groupby("mv").agg(
        impressions=("b", "size"),
        pct_affinity_under_1=("aff", lambda s: round(100 * (s < 1.0).mean(), 1)),
        pct_affinity_over_1_25=("aff", lambda s: round(100 * (s > 1.25).mean(), 1)),
        pct_bought_subcategory=("sub", lambda s: round(100 * s.mean(), 1)),
        pct_bought_brand=("brand", lambda s: round(100 * s.mean(), 1)))
    print("mechanism — known shoppers, products not bought (attribute affinity from 60-day purchases):")
    print(mech.to_string(), "\n")
    sess = e[e.shared.notna()].groupby(["mv", e.is_new.map({True: "new", False: "known"})]).agg(
        impressions=("b", "size"),
        pct_share_1_attribute=("shared", lambda s: round(100 * (s == 1).mean(), 1)),
        pct_share_2_attributes=("shared", lambda s: round(100 * (s == 2).mean(), 2)))
    print("mechanism — requests with a recent view: attributes shared with the last viewed product:")
    print(sess.to_string(), "\n")
    print("share of impressions that are products added during the event:")
    print((100 * e.groupby("mv").new_product.mean()).round(1).to_string(), "\n")

    if "--bands" in sys.argv:   # does each arm sell what the levers promise, and how varied are its lists?
        k = known[known.aff.notna()].copy()
        k["band"] = pd.cut(k.aff, [0, 1.0, 1.25, 1.75, 99], labels=["under 1.0", "1.0-1.25", "1.25-1.75", "over 1.75"])
        t = k.groupby(["mv", "band"], observed=True).agg(impressions=("b", "size"), buys=("b", "sum"), mean_slot=("slot", "mean"))
        t["buy_pct"] = (100 * t.buys / t.impressions).round(3)
        t["mean_slot"] = t.mean_slot.round(1)
        print("known shoppers, products not bought — purchases per impression by attribute-affinity band, per arm:")
        print(t[t.impressions >= 300].to_string(), "\n")
        v = e[e.shared.notna()]
        t = v.groupby(["mv", v.is_new.map({True: "new", False: "known"}), "shared"]).agg(impressions=("b", "size"), buys=("b", "sum"))
        t["buy_pct"] = (100 * t.buys / t.impressions).round(3)
        print("requests with a recent view — purchases per impression by attributes shared with the last view, per arm:")
        print(t[t.impressions >= 300].to_string(), "\n")
        d["n_sub"] = d.shown.map(lambda a: len({sub.get(i) for i in a}))
        d["n_pair"] = d.shown.map(lambda a: len({tuple(pa.get(i, [])) for i in a}))
        div = d.groupby(["mv", d.is_new.map({True: "new", False: "known"})]).agg(
            requests=("buy", "size"), subcategories_in_list=("n_sub", "mean"), attribute_pairs_in_list=("n_pair", "mean")).round(2)
        print("variety of the lists (mean distinct subcategories / attribute pairs among the 10 products):")
        print(div[div.requests >= 100].to_string(), "\n")
        kd = d[~d.is_new & ~d.mv.str.contains("v5|v6")].copy()
        kd["variety"] = pd.cut(kd.n_sub, [0, 3, 5, 7, 10], labels=["1-3 subcategories", "4-5", "6-7", "8-10"])
        t = kd.groupby("variety", observed=True).agg(requests=("buy", "size"), buys=("buy", "sum"))
        t["conv_pct"] = (100 * t.buys / t.requests).round(2)
        print("known shoppers, attribute models and their exploration arms — conversion by variety of the list:")
        print(t.to_string(), "\n")

    if "--brand" in sys.argv:   # is brand history just a stand-in for attribute affinity?
        k = known[known.aff.notna() & ~known.mv.str.contains("explore")].copy()
        rate = k.groupby("slot").b.mean()
        k["exp"] = k.slot.map(rate)
        k["band"] = pd.cut(k.aff, [0, 1.0, 1.25, 1.75, 99], labels=["under 1.0", "1.0-1.25", "1.25-1.75", "over 1.75"])
        t = k.groupby(["band", "brand"], observed=True).agg(impressions=("b", "size"), buys=("b", "sum"), expected=("exp", "sum"))
        t["buy_pct"] = (100 * t.buys / t.impressions).round(3)
        t["obs_over_exp"] = (t.buys / t.expected).round(2)
        print("brand history inside each attribute-affinity band (known shoppers, slot-adjusted):")
        print(t.drop(columns="expected").to_string())


if __name__ == "__main__":
    main()
