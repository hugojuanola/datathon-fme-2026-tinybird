"""How the store moves during the event, measured on the organic stream, and how the live detector sees it.

    python -m offline.store_moves          # every aggregate is computed in RawTree; a report on screen

The brief says the final brings trends ("visible early in the live shop.events"), price changes and new
products. The 60-day history has none of them, so the only place to learn their shape is today's stream:

1. Trends      organic purchases per 10 minutes by category, subcategory and brand, against each group's
               share over the whole day: which groups jump, when, for how long, by how much.
2. Detector    reco.features.Trends — the class the server runs every second — replayed minute by minute
               over the day: how soon it sees each trend, how long it holds on, how often it is wrong.
3. Prices      share of the store's purchases taken by the products of each price change, before and after.
4. New         the same for the products added during the event.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from reco.features import BUY_WINDOW, LEVEL_SIZE, LEVELS, Trends
from reco.rawtree import query_tsv

PRODUCTS = """(SELECT product_id::String AS product_id, category::String AS category, subcategory::String AS subcategory,
                     brand::String AS brand FROM shop.catalog
              UNION ALL
              SELECT product_id::String, category::String, subcategory::String, brand::String
              FROM shop.catalog_updates WHERE change::String = 'new_product')"""

BY_GROUP = """
SELECT toUnixTimestamp(toStartOfInterval(e.ts::DateTime64(3), INTERVAL {step} MINUTE)) AS t, c.{group} AS k,
       countIf(e.ev = 'p') AS buys, countIf(e.ev = 'v') AS views
FROM (SELECT ts, product_id::String AS product_id, substring(event_type::String, 1, 1) AS ev FROM shop.events) AS e
INNER JOIN """ + PRODUCTS + """ AS c ON c.product_id = e.product_id
GROUP BY t, k ORDER BY t, k"""

HISTORY = """
SELECT c.{group} AS k, countIf(e.ev = 'p') AS buys, countIf(e.ev = 'v') AS views
FROM (SELECT product_id::String AS product_id, substring(event_type::String, 1, 1) AS ev FROM shop.history_events) AS e
INNER JOIN """ + PRODUCTS + """ AS c ON c.product_id = e.product_id
GROUP BY k"""

BY_PRODUCT = """
SELECT toUnixTimestamp(toStartOfInterval(ts::DateTime64(3), INTERVAL 10 MINUTE)) AS t, product_id::String AS pid,
       count() AS buys
FROM shop.events WHERE event_type::String = 'purchase' GROUP BY t, pid"""

MOVES = """
SELECT toUnixTimestamp(u.ts::DateTime64(3)) AS t, u.change::String AS change, u.product_id::String AS pid,
       u.price_eur::Float64 AS price, c.base AS base, u.subcategory::String AS subcategory
FROM shop.catalog_updates AS u
LEFT JOIN (SELECT product_id::String AS product_id, price_eur::Float64 AS base FROM shop.catalog) AS c
    ON c.product_id = u.product_id::String
WHERE u.change::String IN ('price_change', 'new_product') ORDER BY t"""


def clock(seconds: float) -> str:
    return pd.to_datetime(seconds, unit="s").strftime("%H:%M")


def complete(df: pd.DataFrame) -> pd.DataFrame:
    """Drop the last time bucket: it is still filling."""
    return df[df.t < df.t.max()]


def trends() -> dict[str, tuple[int, int]]:
    """Which groups jump. Returns the trending subcategories as {name: (first minute, last minute)}."""
    found: dict[str, tuple[int, int]] = {}
    print("1. TRENDS — purchases per 10 minutes against the group's share of the day")
    for group in ("category", "subcategory", "brand"):
        g = complete(query_tsv(BY_GROUP.format(step=10, group=group))).pivot(index="k", columns="t", values="buys").fillna(0)
        day_share = g.sum(axis=1) / g.values.sum()
        lift = (g + 3) / (np.outer(day_share, g.sum()) + 3)
        hot = (lift >= 3) & (g >= 12)
        print(f"   {group}: {len(g)} groups, {int(hot.any(axis=1).sum())} of them sell 3x their share (12+ purchases) in some bucket")
        for k in hot.index[hot.any(axis=1)]:
            on = hot.columns[hot.loc[k]]
            quiet = g.loc[k, ~hot.loc[k]].mean()
            views = complete(query_tsv(BY_GROUP.format(step=10, group=group)))
            v = views[views.k == k].set_index("t").views
            print(f"      {k:<16} {clock(on.min())}-{clock(on.max() + 600)}: purchases x{g.loc[k, on].mean() / quiet:.1f}, "
                  f"views x{v.reindex(on).mean() / v.drop(on).mean():.1f} (usual share of purchases {100 * day_share[k]:.2f} %)")
            if group == "subcategory":
                found[k] = (int(on.min()) // 60, int(on.max()) // 60 + 10)
    return found


def inside(found: dict[str, tuple[int, int]]) -> None:
    """Does a trend lift every product of the subcategory, or a few?"""
    names = "', '".join(found)
    subs = query_tsv(f"SELECT product_id AS pid, subcategory FROM {PRODUCTS} WHERE subcategory IN ('{names}')")
    buys = complete(query_tsv(BY_PRODUCT)).merge(subs, on="pid")
    for k, (a, b) in found.items():
        d = buys[buys.subcategory == k]
        on = d[(d.t // 60 >= a) & (d.t // 60 < b)].groupby("pid").buys.sum()
        off = d[(d.t // 60 < a) | (d.t // 60 >= b)].groupby("pid").buys.sum()
        both = pd.concat([on.rename("on"), off.rename("off")], axis=1).fillna(0)
        print(f"      inside {k}: {len(both)} products sell; a product's share of the subcategory during the trend vs "
              f"the rest of the day correlates {np.corrcoef(both.on, both.off)[0, 1]:.2f}")


def detector(found: dict[str, tuple[int, int]]) -> None:
    """The deployed class, minute by minute, on today's views and purchases at its three levels."""
    trends, usual_views, usual_buys, name_of, sub_key = Trends(), {}, {}, {}, {}
    views_of: dict[str, pd.Series] = {}
    for level, group in enumerate(LEVELS):
        live = complete(query_tsv(BY_GROUP.format(step=1, group=group)))
        hist = query_tsv(HISTORY.format(group=group)).set_index("k")
        for i, k in enumerate(sorted(set(live.k) | set(hist.index))):
            key = level * LEVEL_SIZE + i
            name_of[key] = k if level == 0 else f"{group} {k}"
            if k in hist.index:
                usual_views[key], usual_buys[key] = hist.views[k] / hist.views.sum(), hist.buys[k] / hist.buys.sum()
            rows = live[live.k == k]
            for t, n_buys, n_views in zip(rows.t // 60, rows.buys, rows.views):
                if n_views:
                    trends.views.setdefault(int(t), {})[key] = int(n_views)
                if n_buys:
                    trends.buys.setdefault(int(t), {})[key] = int(n_buys)
            if level == 0:
                sub_key[k] = key
                views_of[k] = rows.set_index(rows.t // 60).views
    minutes = range(min(trends.views) + BUY_WINDOW, max(trends.views) + 1)
    fired = {}
    for m in minutes:
        trends.newest = m
        fired[m] = trends.lifts(usual_views, usual_buys)      # what the server knows when minute m ends
    print()
    print(f"2. DETECTOR — reco.features.Trends on {len(minutes)} minutes, {len(name_of)} groups (subcategories, categories, brands)")
    expected = set()
    for k, (a, b) in found.items():
        v = views_of[k].reindex(range(a - 15, b + 15)).fillna(0)
        usual = views_of[k].median()
        hot = v.rolling(3, center=True).mean() > 2 * usual        # the trend to the minute, from its views
        start, end = int(hot[hot].index.min()), int(hot[hot].index.max()) + 1
        on = [m for m in minutes if sub_key[k] in fired[m] and start - 5 <= m < end + 15]
        expected.update((m, sub_key[k]) for m in on)
        if not on:
            print(f"      {k:<16} {clock(60 * start)}-{clock(60 * end)} MISSED")
            continue
        lifts = [fired[m][sub_key[k]] for m in on if m < end]
        print(f"      {k:<16} {clock(60 * start)}-{clock(60 * end)}: seen after {on[0] + 1 - start} min, dropped {on[-1] + 1 - end:+d} min "
              f"after its end; lift in its first 3 minutes {np.mean(lifts[:3]):.1f}, afterwards median {np.median(lifts[3:]):.1f} "
              f"(range {min(lifts[3:]):.1f}-{max(lifts[3:]):.1f})")
    false = [(m, key) for m in minutes for key in fired[m] if (m, key) not in expected]
    print(f"      false alarms: {len(false)} group-minutes out of {len(minutes) * len(name_of):,}")
    for m, key in false[:8]:
        print(f"         {clock(60 * m)} {name_of[key]} x{fired[m][key]:.1f}")


def prices_and_new() -> None:
    moves = query_tsv(MOVES)
    buys = complete(query_tsv(BY_PRODUCT))
    total = buys.groupby("t").buys.sum()
    print("\n3. PRICE CHANGES — share of the store's purchases taken by the products of each batch")
    pc = moves[moves.change == "price_change"].assign(ratio=lambda d: d.price / d.base)
    for t, batch in pc.groupby("t"):
        drop = batch[batch.ratio < 0.95]
        if len(drop) < 20:
            print(f"      {clock(t)}: {len(batch)} products back to the catalogue price")
            continue
        s = (buys[buys.pid.isin(drop.pid)].groupby("t").buys.sum().reindex(total.index).fillna(0) / total)
        before, after = s[(s.index < t) & (s.index >= t - 3600)], s[(s.index >= t) & (s.index < t + 3600)]
        if len(before) and len(after):
            print(f"      {clock(t)}: {len(drop)} products at {100 * drop.ratio.median():.0f} % of their price: "
                  f"{100 * before.mean():.2f} % of purchases in the hour before -> {100 * after.mean():.2f} % in the hour after "
                  f"(x{after.mean() / before.mean():.2f}; elasticity {np.log(after.mean() / before.mean()) / -np.log(drop.ratio.median()):.1f})")
    print("\n4. NEW PRODUCTS — share of the store's purchases from the moment they appear")
    for t, batch in moves[moves.change == "new_product"].groupby("t"):
        s = (buys[buys.pid.isin(batch.pid)].groupby("t").buys.sum().reindex(total.index).fillna(0) / total)
        after = s[s.index >= t]
        print(f"      {clock(t)}: {len(batch)} products in {batch.subcategory.nunique()} subcategories: "
              f"{100 * after.iloc[:1].mean():.2f} % of purchases in their first 10 minutes, {100 * after.iloc[:6].mean():.2f} % "
              f"in the first hour, {100 * after.iloc[6:].mean():.2f} % later")


if __name__ == "__main__":
    subcategories = trends()
    if subcategories:
        inside(subcategories)
        detector(subcategories)
    prices_and_new()
