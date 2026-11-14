-- What is the model actually showing? Composition of the lists of one model_version, by period, using only
-- the live tables. A sharp change between periods points at the piece of state that changed (session views,
-- carts, satiation, new products) rather than at the shoppers.
-- Edit the model_version and the period boundaries (UTC) before running.
--   python scripts/rt.py -f realtime_analyisi_leaderboard/queries/list_composition_by_period.sql
WITH
cat AS (SELECT product_id::String AS pid, any(category::String) AS c, any(subcategory::String) AS s
        FROM (SELECT product_id, category, subcategory FROM shop.catalog
              UNION ALL SELECT product_id, category, subcategory FROM shop.catalog_updates WHERE change = 'new_product')
        GROUP BY pid),
newp AS (SELECT DISTINCT product_id::String AS pid FROM shop.catalog_updates WHERE change = 'new_product'),
x AS (
    SELECT multiIf(f.ts < '2026-11-14 13:57:00', 'A 13:34-13:57', f.ts < '2026-11-14 14:06:31', 'B 13:57-14:06',
                   'C 14:06-now') AS period,
           r.u AS u, r.ts AS rts, r.rv AS rv, r.is_new AS is_new, arrayJoin(f.shown) AS item,
           f.clicked AS clicked, f.purchased AS purchased
    FROM (SELECT request_id::String AS rid, ts::DateTime64(3) AS ts, shown::Array(String) AS shown,
                 clicked::String AS clicked, purchased::String AS purchased
          FROM team_NN.feedback WHERE served_by = 'team' AND ts > '2026-11-14 13:34:05') AS f
    INNER JOIN (SELECT request_id::String AS rid, user_id::String AS u, ts::DateTime64(3) AS ts,
                       is_new_user::Bool AS is_new,
                       arrayMap(v -> v.product_id::String, recent_views::Array(JSON)) AS rv
                FROM shop.requests WHERE ts > '2026-11-14 13:33:00') AS r ON r.rid = f.rid
    INNER JOIN (SELECT request_id::String AS rid, any(model_version::String) AS mv
                FROM team_NN.submissions GROUP BY rid) AS s ON s.rid = f.rid
    WHERE s.mv = 'skore_money_v5'
)
SELECT x.period AS period, if(x.is_new, 'new', 'known') AS shopper, count() AS impressions,
       round(100 * countIf(has(x.rv, x.item)) / count(), 1)                                  AS pct_in_recent_views,
       round(100 * countIf(ci.c = cl.c AND cl.c != '') / countIf(length(x.rv) > 0), 1)       AS pct_same_cat_as_last_view,
       round(100 * countIf(ci.s = cl.s AND cl.s != '') / countIf(length(x.rv) > 0), 1)       AS pct_same_subcat_as_last_view,
       round(100 * countIf(n.pid != '') / count(), 1)                                        AS pct_new_products,
       round(100 * countIf(arrayCount(t -> t < x.rts, e.bought) > 0) / count(), 2)           AS pct_bought_live_before,
       round(100 * countIf(arrayCount(t -> t < x.rts, e.carted) > 0
                           AND arrayCount(t -> t < x.rts, e.bought) = 0) / count(), 1)       AS pct_carted_live_not_bought,
       round(100 * countIf(arrayCount(t -> t < x.rts, e.viewed) > 0) / count(), 1)           AS pct_viewed_live_before,
       uniqExact(x.item)                                                                     AS distinct_products_shown,
       round(100 * countIf(x.purchased = x.item) / count(), 3)                               AS buy_pct
FROM x
INNER JOIN cat AS ci ON ci.pid = x.item
LEFT JOIN cat AS cl ON cl.pid = x.rv[-1]
LEFT JOIN newp AS n ON n.pid = x.item
LEFT JOIN (SELECT user_id::String AS u, product_id::String AS pid,
                  groupArrayIf(ts::DateTime64(3), event_type = 'purchase')    AS bought,
                  groupArrayIf(ts::DateTime64(3), event_type = 'add_to_cart') AS carted,
                  groupArrayIf(ts::DateTime64(3), event_type = 'view')        AS viewed
           FROM shop.events GROUP BY u, pid) AS e ON e.u = x.u AND e.pid = x.item
GROUP BY period, shopper
ORDER BY shopper, period
