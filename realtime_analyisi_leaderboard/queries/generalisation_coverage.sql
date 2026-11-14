-- Generalisation: if we knew NOTHING about a shopper before the stream opened (as with the new shoppers of
-- the final), how much would the live stream alone tell us, and how fast?
-- For every request of the first two hours of the stream (the final lasts two hours), count the shopper's
-- own live events (shop.events) that happened before the request.
--   python scripts/rt.py -f realtime_analyisi_leaderboard/queries/generalisation_coverage.sql
SELECT toStartOfInterval(r.ts, INTERVAL 30 MINUTE)                       AS half_hour_utc,
       count()                                                          AS requests,
       round(100 * countIf(arrayCount(t -> t < r.ts, e.views) > 0) / count(), 1)      AS pct_with_live_view,
       round(100 * countIf(arrayCount(t -> t < r.ts, e.views) >= 5) / count(), 1)     AS pct_with_5_live_views,
       round(100 * countIf(arrayCount(t -> t < r.ts, e.carts) > 0) / count(), 1)      AS pct_with_live_cart,
       round(100 * countIf(arrayCount(t -> t < r.ts, e.purchases) > 0) / count(), 1)  AS pct_with_live_purchase
FROM (SELECT user_id::String AS u, ts::DateTime64(3) AS ts FROM shop.requests
      WHERE ts < '2026-11-14 11:00:00') AS r
LEFT JOIN (SELECT user_id::String AS u,
                  groupArrayIf(ts::DateTime64(3), event_type = 'view')        AS views,
                  groupArrayIf(ts::DateTime64(3), event_type = 'add_to_cart') AS carts,
                  groupArrayIf(ts::DateTime64(3), event_type = 'purchase')    AS purchases
           FROM shop.events WHERE ts < '2026-11-14 11:00:00' GROUP BY u) AS e ON e.u = r.u
GROUP BY half_hour_utc
ORDER BY half_hour_utc
