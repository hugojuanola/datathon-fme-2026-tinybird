-- Generalisation: does "the shopper has bought in this subcategory before" still work when the only history
-- we use is the LIVE stream (shop.events before the request), ignoring the 60 days? That is all we will have
-- for the new shoppers of the final.
-- Per impression of our carousel feedback, for products the shopper has not bought live before the request.
--   python scripts/rt.py -f realtime_analyisi_leaderboard/queries/generalisation_lever_live_only.sql
SELECT if(x.is_new, 'new shopper', 'known shopper')                               AS shopper,
       multiIf(arrayCount(t -> t < x.rts, lp.pts) > 0, '1 bought live in this subcategory',
               arrayCount(t -> t < x.rts, lv.vts) > 0, '2 only viewed live this subcategory',
               '3 no live history in this subcategory')                          AS live_history,
       count()                                                                    AS impressions,
       countIf(x.clicked = x.item)                                                AS clicks,
       countIf(x.purchased = x.item)                                              AS buys,
       round(100 * countIf(x.clicked = x.item) / count(), 3)                      AS ctr_pct,
       round(100 * countIf(x.purchased = x.item) / count(), 3)                    AS buy_pct
FROM (SELECT r.u AS u, r.is_new AS is_new, r.ts AS rts, arrayJoin(f.shown) AS item, f.clicked AS clicked,
             f.purchased AS purchased
      FROM (SELECT request_id::String AS rid, shown::Array(String) AS shown, clicked::String AS clicked,
                   purchased::String AS purchased
            FROM team_NN.feedback WHERE request_id != '__init__') AS f
      INNER JOIN (SELECT request_id::String AS rid, user_id::String AS u, is_new_user::Bool AS is_new,
                         ts::DateTime64(3) AS ts FROM shop.requests) AS r ON r.rid = f.rid) AS x
INNER JOIN (SELECT product_id::String AS pid, any(subcategory::String) AS s
            FROM (SELECT product_id, subcategory FROM shop.catalog
                  UNION ALL SELECT product_id, subcategory FROM shop.catalog_updates WHERE change = 'new_product')
            GROUP BY pid) AS c ON c.pid = x.item
LEFT JOIN (SELECT e.user_id::String AS u, k.s AS s, groupArray(e.ts::DateTime64(3)) AS pts
           FROM shop.events AS e
           INNER JOIN (SELECT product_id::String AS pid, any(subcategory::String) AS s
                       FROM (SELECT product_id, subcategory FROM shop.catalog
                             UNION ALL SELECT product_id, subcategory FROM shop.catalog_updates WHERE change = 'new_product')
                       GROUP BY pid) AS k ON k.pid = e.product_id::String
           WHERE e.event_type = 'purchase' GROUP BY u, s) AS lp ON lp.u = x.u AND lp.s = c.s
LEFT JOIN (SELECT e.user_id::String AS u, k.s AS s, groupArray(e.ts::DateTime64(3)) AS vts
           FROM shop.events AS e
           INNER JOIN (SELECT product_id::String AS pid, any(subcategory::String) AS s
                       FROM (SELECT product_id, subcategory FROM shop.catalog
                             UNION ALL SELECT product_id, subcategory FROM shop.catalog_updates WHERE change = 'new_product')
                       GROUP BY pid) AS k ON k.pid = e.product_id::String
           WHERE e.event_type = 'view' GROUP BY u, s) AS lv ON lv.u = x.u AND lv.s = c.s
LEFT JOIN (SELECT user_id::String AS u, product_id::String AS pid, groupArray(ts::DateTime64(3)) AS bts
           FROM shop.events WHERE event_type = 'purchase' GROUP BY u, pid) AS lb ON lb.u = x.u AND lb.pid = x.item
WHERE arrayCount(t -> t < x.rts, lb.bts) = 0
GROUP BY shopper, live_history
ORDER BY shopper, live_history
