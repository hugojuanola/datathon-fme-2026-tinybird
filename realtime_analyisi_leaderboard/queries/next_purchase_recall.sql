-- Why are we far from the reference? Use the shopper's NEXT ORGANIC PURCHASE as evidence of what they wanted.
-- For every organic purchase (shop.events) made within 30 minutes after one of the requests we served, take
-- the latest such request and ask: was the purchased product in our 10? If not, what was it to the shopper —
-- something we could have known (recent view, abandoned cart, a subcategory they buy in, the category they
-- were browsing) or something nobody could have guessed?
--   python scripts/rt.py -f realtime_analyisi_leaderboard/queries/next_purchase_recall.sql
WITH
cat AS (SELECT product_id::String AS pid, any(category::String) AS c, any(subcategory::String) AS s
        FROM (SELECT product_id, category, subcategory FROM shop.catalog
              UNION ALL SELECT product_id, category, subcategory FROM shop.catalog_updates WHERE change = 'new_product')
        GROUP BY pid),
m AS (  -- each organic purchase with the latest request of that shopper before it
    SELECT p.u AS u, p.pid AS pid, p.ts AS pts, r.rid AS rid, r.rts AS rts, r.is_new AS is_new, r.rv AS rv
    FROM (SELECT user_id::String AS u, product_id::String AS pid, ts::DateTime64(3) AS ts
          FROM shop.events WHERE event_type = 'purchase' AND ts > now() - INTERVAL 150 MINUTE) AS p
    ASOF INNER JOIN (SELECT request_id::String AS rid, user_id::String AS u, ts::DateTime64(3) AS rts,
                            is_new_user::Bool AS is_new,
                            arrayMap(v -> v.product_id::String, recent_views::Array(JSON)) AS rv
                     FROM shop.requests WHERE ts > now() - INTERVAL 150 MINUTE) AS r
         ON r.u = p.u AND r.rts <= p.ts
    WHERE p.ts <= r.rts + INTERVAL 30 MINUTE
)
SELECT if(m.is_new, 'new', 'known')                                                        AS shopper,
       count()                                                                             AS next_purchases,
       round(100 * countIf(has(f.shown, m.pid)) / count(), 1)                              AS pct_in_our_10,
       round(100 * countIf(hp.p > 0) / count(), 1)                                         AS pct_repeat_of_history,
       -- from here on: only purchases of products NOT bought before (what the carousel can sell)
       countIf(hp.p = 0)                                                                   AS sellable,
       round(100 * countIf(hp.p = 0 AND has(f.shown, m.pid)) / countIf(hp.p = 0), 1)       AS sellable_pct_in_our_10,
       round(100 * countIf(hp.p = 0 AND has(m.rv, m.pid)) / countIf(hp.p = 0), 1)          AS pct_in_recent_views,
       round(100 * countIf(hp.p = 0 AND hp.c > 0) / countIf(hp.p = 0), 1)                  AS pct_carted_in_history,
       round(100 * countIf(hp.p = 0 AND cl.s = cp.s AND cl.s != '') / countIf(hp.p = 0), 1) AS pct_same_subcat_as_last_view,
       round(100 * countIf(hp.p = 0 AND cl.c = cp.c AND cl.c != '') / countIf(hp.p = 0), 1) AS pct_same_cat_as_last_view,
       round(100 * countIf(hp.p = 0 AND hs.p > 0) / countIf(hp.p = 0), 1)                  AS pct_subcat_with_purchase_history,
       round(100 * countIf(hp.p = 0 AND hs.p = 0 AND hs.v > 0) / countIf(hp.p = 0), 1)     AS pct_subcat_only_viewed,
       round(100 * countIf(hp.p = 0 AND NOT has(m.rv, m.pid) AND hp.c = 0 AND NOT (cl.c = cp.c AND cl.c != '')
                           AND hs.p = 0) / countIf(hp.p = 0), 1)                           AS pct_none_of_these
FROM m
INNER JOIN (SELECT request_id::String AS rid, shown::Array(String) AS shown
            FROM team_NN.feedback WHERE served_by = 'team' AND ts > now() - INTERVAL 150 MINUTE) AS f ON f.rid = m.rid
INNER JOIN cat AS cp ON cp.pid = m.pid
LEFT JOIN cat AS cl ON cl.pid = m.rv[-1]
LEFT JOIN (SELECT user_id::String AS u, product_id::String AS pid, countIf(event_type = 'add_to_cart') AS c,
                  countIf(event_type = 'purchase') AS p
           FROM shop.history_events GROUP BY u, pid) AS hp ON hp.u = m.u AND hp.pid = m.pid
LEFT JOIN (SELECT e.user_id::String AS u, k.subcategory::String AS s, countIf(e.event_type = 'view') AS v,
                  countIf(e.event_type = 'purchase') AS p
           FROM shop.history_events AS e INNER JOIN shop.catalog AS k ON k.product_id::String = e.product_id::String
           GROUP BY u, s) AS hs ON hs.u = m.u AND hs.s = cp.s
GROUP BY shopper
ORDER BY shopper
