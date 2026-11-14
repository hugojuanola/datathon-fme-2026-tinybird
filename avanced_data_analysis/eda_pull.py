#!/usr/bin/env python3
"""Pull the data the EDA needs from RawTree into $SKORE_DATA_DIR/eda/*.parquet (re-creatable).

The cache lives outside the repository (SKORE_DATA_DIR in .env; default: ./data) because the repository
sits in a OneDrive folder and bulky files there compete with the live server for the uplink.

Aggregations run inside RawTree; only summaries and a 10% sample of the carousel log come down.

    python avanced_data_analysis/eda_pull.py            # skip files that already exist
    python avanced_data_analysis/eda_pull.py --force    # re-pull everything
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from rt import load_env, query  # noqa: E402

load_env()
OUT = Path(os.environ.get("SKORE_DATA_DIR", ROOT / "data")) / "eda"
EV = "shop.history_events"
SE = "shop.history_sessions"
NN = "ifNull(clicked::Nullable(String), '')"
PP = "ifNull(purchased::Nullable(String), '')"

QUERIES: dict[str, str | list[str]] = {
    "catalog": """
        SELECT product_id::String AS product_id, category::String AS category, subcategory::String AS subcategory,
               brand::String AS brand, price_eur::Float64 AS price_eur, toString(created_at) AS created_at,
               description::String AS description
        FROM shop.catalog""",
    "catalog_updates": """
        SELECT product_id::String AS product_id, change::String AS change, toString(ts) AS ts,
               price_eur::Float64 AS price_eur, category::String AS category, subcategory::String AS subcategory,
               brand::String AS brand
        FROM shop.catalog_updates""",
    # organic behaviour per product (60 days)
    "product_events": f"""
        SELECT product_id::String AS product_id,
               countIf(event_type = 'view') AS views, countIf(event_type = 'add_to_cart') AS carts,
               countIf(event_type = 'purchase') AS purchases, uniqExact(user_id::String) AS users,
               countIf(event_type = 'purchase' AND ts > '2026-11-07 07:00:00') AS purchases_last7d,
               countIf(event_type = 'purchase' AND ts <= '2026-09-22 07:00:00') AS purchases_first7d
        FROM {EV} GROUP BY product_id""",
    # how each product did inside the old carousel
    "product_carousel": f"""
        SELECT t.1 AS product_id, count() AS impressions, avg(t.2) AS avg_slot, avg(t.3) AS avg_propensity,
               countIf(c = t.1) AS clicks, countIf(p = t.1) AS buys
        FROM (SELECT arrayJoin(arrayZip(shown::Array(String), arrayEnumerate(shown::Array(String)),
                                        propensity::Array(Float64))) AS t, {NN} AS c, {PP} AS p FROM {SE})
        GROUP BY product_id""",
    "users": f"""
        SELECT user_id::String AS user_id,
               countIf(event_type = 'view') AS views, countIf(event_type = 'add_to_cart') AS carts,
               countIf(event_type = 'purchase') AS purchases, uniqExact(session_id::String) AS sessions,
               uniqExact(product_id::String) AS n_products,
               sumIf(price_eur::Float64, event_type = 'purchase') AS spend,
               avgIf(price_eur::Float64, event_type = 'view') AS avg_view_price,
               avgIf(price_eur::Float64, event_type = 'purchase') AS avg_buy_price,
               any(device::String) AS main_device, uniqExact(device::String) AS n_devices,
               any(region::String) AS main_region, uniqExact(region::String) AS n_regions,
               toString(min(ts::DateTime64(3))) AS first_ts, toString(max(ts::DateTime64(3))) AS last_ts
        FROM {EV} GROUP BY user_id""",
    "user_category": f"""
        SELECT e.user_id::String AS user_id, c.category::String AS category,
               countIf(e.event_type = 'view') AS views, countIf(e.event_type = 'purchase') AS purchases
        FROM {EV} AS e INNER JOIN shop.catalog AS c ON c.product_id::String = e.product_id::String
        GROUP BY user_id, category""",
    "events_hourly": f"""
        SELECT toString(toStartOfHour(ts::DateTime64(3))) AS hour, event_type::String AS event_type, count() AS n
        FROM {EV} GROUP BY hour, event_type""",
    "category_daily": f"""
        SELECT toString(toDate(e.ts::DateTime64(3))) AS day, c.category::String AS category,
               countIf(e.event_type = 'view') AS views, countIf(e.event_type = 'purchase') AS purchases
        FROM {EV} AS e INNER JOIN shop.catalog AS c ON c.product_id::String = e.product_id::String
        GROUP BY day, category""",
    "region_category": f"""
        SELECT e.region::String AS region, c.category::String AS category, e.device::String AS device,
               countIf(e.event_type = 'view') AS views, countIf(e.event_type = 'purchase') AS purchases
        FROM {EV} AS e INNER JOIN shop.catalog AS c ON c.product_id::String = e.product_id::String
        GROUP BY region, category, device""",
    "sessions_segments": f"""
        SELECT context.page::String AS page, context.device::String AS device, context.region::String AS region,
               length(recent_views) AS n_recent, toHour(ts::DateTime64(3)) AS hour,
               toDayOfWeek(ts::DateTime64(3)) AS dow,
               count() AS n, countIf({NN} != '') AS clicks, countIf({PP} != '') AS buys,
               sum(revenue_eur::Float64) AS revenue
        FROM {SE} GROUP BY page, device, region, n_recent, hour, dow""",
    "sessions_daily": f"""
        SELECT toString(toDate(ts::DateTime64(3))) AS day, count() AS n, countIf({NN} != '') AS clicks,
               countIf({PP} != '') AS buys, sum(revenue_eur::Float64) AS revenue
        FROM {SE} GROUP BY day""",
    # repeat purchases: does a shopper buy the same product twice? (satiation)
    "purchases": f"""
        SELECT user_id::String AS user_id, product_id::String AS product_id, toString(ts::DateTime64(3)) AS ts
        FROM {EV} WHERE event_type = 'purchase'""",
    # 10% hash sample of the carousel log, full detail, in 4 chunks (100 MiB result cap)
    "sessions_sample": [
        f"""
        SELECT request_id::String AS request_id, toString(ts::DateTime64(3)) AS ts, user_id::String AS user_id,
               context.device::String AS device, context.page::String AS page, context.region::String AS region,
               arrayMap(v -> v.product_id::String, recent_views::Array(JSON)) AS recent,
               shown::Array(String) AS shown, propensity::Array(Float64) AS propensity,
               {NN} AS clicked, {PP} AS purchased, revenue_eur::Float64 AS revenue_eur
        FROM {SE} WHERE cityHash64(request_id::String) % 40 = {k}"""
        for k in range(4)
    ],
    # live side (practice round)
    "live_requests": """
        SELECT context.page::String AS page, context.device::String AS device, context.region::String AS region,
               is_new_user::Bool AS is_new_user, length(recent_views) AS n_recent, count() AS n
        FROM shop.requests GROUP BY page, device, region, is_new_user, n_recent""",
    "live_feedback": """
        SELECT r.context.page::String AS page, r.is_new_user::Bool AS is_new_user, length(r.recent_views) AS n_recent,
               f.served_by::String AS served_by, count() AS n, countIf(f.clicked != '') AS clicks,
               countIf(f.purchased != '') AS buys, sum(f.revenue_eur::Float64) AS revenue
        FROM team_NN.feedback AS f INNER JOIN shop.requests AS r ON r.request_id::String = f.request_id::String
        WHERE f.request_id != '__init__'
        GROUP BY page, is_new_user, n_recent, served_by""",
}


def main() -> None:
    force = "--force" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    for name, sql in QUERIES.items():
        path = OUT / f"{name}.parquet"
        if path.exists() and not force:
            print(f"{name:20s} cached")
            continue
        t0 = time.time()
        parts = []
        for q in sql if isinstance(sql, list) else [sql]:
            q = q.replace("team_NN", os.environ.get("TEAM_ID", "team_NN"))
            parts.append(pd.DataFrame(query(q)["data"]))
        df = pd.concat(parts, ignore_index=True)
        df.to_parquet(path, index=False)
        print(f"{name:20s} {len(df):>9,} rows  {time.time() - t0:5.1f}s")


if __name__ == "__main__":
    main()
