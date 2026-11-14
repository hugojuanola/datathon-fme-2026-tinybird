"""Export the history from RawTree to local parquet files ($SKORE_DATA_DIR, default data/, git-ignored).

    python -m offline.pull_data              # catalog + sessions + events
    python -m offline.pull_data sessions     # only one of: catalog, sessions, events
    python -m offline.pull_data live         # our live feedback so far, incrementally (re-run to refresh)

RawTree caps a query at 30 s / 100 MiB, so the two big tables are pulled in time slices, in
parallel, with arrays flattened to comma-separated strings inside SQL (TSV transport).
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pandas as pd

from reco.rawtree import DATA, TEAM, query_tsv
from reco.priority import background

START = datetime(2026, 9, 15, 6)   # history spans 2026-09-15 07:00 → 2026-11-14 07:08 UTC
END = datetime(2026, 11, 14, 8)

SESSIONS = """
SELECT toUnixTimestamp64Milli(ts::DateTime64(3)) AS ts_ms, user_id::String AS user_id,
       context.device::String AS device, context.region::String AS region, context.page::String AS page,
       arrayStringConcat(arrayMap(v -> v.product_id::String, recent_views::Array(JSON)), ',') AS rv,
       arrayStringConcat(arrayMap(v -> toString(toUnixTimestamp64Milli(v.ts::DateTime64(3))), recent_views::Array(JSON)), ',') AS rv_ts,
       arrayStringConcat(shown::Array(String), ',') AS shown,
       arrayStringConcat(arrayMap(x -> toString(x), propensity::Array(Float64)), ',') AS propensity,
       ifNull(clicked::Nullable(String), '') AS clicked, ifNull(purchased::Nullable(String), '') AS purchased,
       revenue_eur::Float64 AS revenue_eur
FROM shop.history_sessions
WHERE ts::DateTime64(3) >= '{lo}' AND ts::DateTime64(3) < '{hi}'
ORDER BY ts_ms"""

EVENTS = """
SELECT toUnixTimestamp(ts::DateTime64(3)) AS ts, substring(event_type::String, 1, 1) AS ev,
       user_id::String AS user_id, session_id::String AS session_id, product_id::String AS product_id,
       price_eur::Float64 AS price_eur
FROM shop.history_events
WHERE ts::DateTime64(3) >= '{lo}' AND ts::DateTime64(3) < '{hi}'
ORDER BY ts"""

CATALOG = """
SELECT product_id::String AS product_id, category::String AS category, subcategory::String AS subcategory,
       brand::String AS brand, price_eur::Float64 AS price_eur, description::String AS description,
       toUnixTimestamp(created_at::DateTime64(3)) AS created_at
FROM shop.catalog ORDER BY product_id"""

UPDATES = """
SELECT toUnixTimestamp64Milli(ts::DateTime64(3)) AS ts_ms, change::String AS change,
       product_id::String AS product_id, category::String AS category, subcategory::String AS subcategory,
       brand::String AS brand, price_eur::Float64 AS price_eur, description::String AS description,
       toUnixTimestamp(created_at::DateTime64(3)) AS created_at
FROM shop.catalog_updates ORDER BY ts_ms"""


LIVE_START = datetime(2026, 11, 14, 9)   # the practice stream opened at 09:00 UTC

LIVE_EVENTS = EVENTS.replace("shop.history_events", "shop.events")

LIVE_FEEDBACK = """
SELECT toUnixTimestamp64Milli(r.ts) AS ts_ms, r.user_id AS user_id, r.device AS device, r.region AS region,
       r.page AS page, r.is_new AS is_new, r.rv AS rv, f.shown AS shown, f.clicked AS clicked,
       f.purchased AS purchased, f.served_by AS served_by, f.request_id AS request_id
FROM (SELECT request_id::String AS request_id, arrayStringConcat(shown::Array(String), ',') AS shown,
             clicked::String AS clicked, purchased::String AS purchased, served_by::String AS served_by
      FROM {team}.feedback
      WHERE request_id != '__init__' AND ts::DateTime64(3) >= '{lo}' AND ts::DateTime64(3) < '{hi}') AS f
INNER JOIN (SELECT request_id::String AS request_id, ts::DateTime64(3) AS ts, user_id::String AS user_id,
                   context.device::String AS device, context.region::String AS region, context.page::String AS page,
                   is_new_user::Bool AS is_new,
                   arrayStringConcat(arrayMap(v -> v.product_id::String, recent_views::Array(JSON)), ',') AS rv
            FROM shop.requests
            WHERE ts::DateTime64(3) >= toDateTime64('{lo}', 3) - INTERVAL 10 SECOND AND ts::DateTime64(3) < '{hi}') AS r
    ON r.request_id = f.request_id
ORDER BY ts_ms"""


def _slices(hours: int, start: datetime = START, end: datetime = END) -> list[tuple[str, str]]:
    out, t = [], start
    while t < end:
        out.append((t.strftime("%Y-%m-%d %H:%M:%S"), (t + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")))
        t += timedelta(hours=hours)
    return out


def _pull(template: str, lo: str, hi: str) -> pd.DataFrame:
    for attempt in range(5):
        try:
            return query_tsv(template.format(lo=lo, hi=hi), timeout=90)
        except Exception as e:  # transient network / 429 / 408: retry the slice
            print(f"  retry {lo}: {str(e)[:120]}", flush=True)
            time.sleep(2 + 3 * attempt)
    raise RuntimeError(f"slice {lo} failed")


def pull_sliced(name: str, template: str, hours: int, workers: int = 6,
                start: datetime = START, end: datetime = END) -> None:
    t0 = time.time()
    with ThreadPoolExecutor(workers) as pool:
        parts = list(pool.map(lambda s: _pull(template, *s), _slices(hours, start, end)))
    df = pd.concat([p for p in parts if len(p)], ignore_index=True)
    df.to_parquet(DATA / f"{name}.parquet", index=False)
    print(f"{name}: {len(df):,} rows in {time.time() - t0:.0f}s", flush=True)


def pull_live_feedback() -> None:
    """Our feedback joined with its request: one parquet per hour, one light query at a time. Hours already
    on disk are kept; only the last two are read again (feedback for a request lands a few seconds later)."""
    folder = DATA / "live"
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    hour, rows = LIVE_START, 0
    while hour <= now:
        path = folder / f"feedback-{hour:%Y%m%d%H}.parquet"
        if not path.exists() or hour >= now - timedelta(hours=2):
            df = _pull(LIVE_FEEDBACK.replace("{team}", TEAM), f"{hour:%Y-%m-%d %H}:00:00",
                       f"{hour + timedelta(hours=1):%Y-%m-%d %H}:00:00")
            df.to_parquet(path, index=False)
            rows += len(df)
        hour += timedelta(hours=1)
    print(f"live feedback: {rows:,} rows refreshed", flush=True)


def main() -> None:
    background()   # never compete with the live loop for the CPU
    DATA.mkdir(parents=True, exist_ok=True)
    what = sys.argv[1:] or ["catalog", "sessions", "events"]
    if "catalog" in what:
        query_tsv(CATALOG).to_parquet(DATA / "catalog.parquet", index=False)
        query_tsv(UPDATES).to_parquet(DATA / "catalog_updates.parquet", index=False)
        print("catalog: ok", flush=True)
    if "sessions" in what:
        pull_sliced("sessions", SESSIONS, hours=24)
    if "events" in what:
        pull_sliced("events", EVENTS, hours=12)
    if "live" in what:
        query_tsv(UPDATES).to_parquet(DATA / "catalog_updates.parquet", index=False)
        pull_live_feedback()
        if not any((DATA / "cache" / "journal").glob("events-*.tsv")):   # no server journal on this machine
            pull_sliced("live_events", LIVE_EVENTS, hours=1, workers=2, start=LIVE_START,
                        end=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=1))

if __name__ == "__main__":
    main()
