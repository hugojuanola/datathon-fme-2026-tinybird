-- Follow-up to next_purchase_recall.sql, known shoppers only, products not bought before:
-- WHERE does the next organic purchase fall? Rank of its subcategory among the subcategories the shopper has
-- bought in (1 = the one they buy most), and rank of the product by popularity inside its subcategory.
-- This sizes a candidate generator: "top-N products of the shopper's top-K purchase subcategories".
--   python scripts/rt.py -f realtime_analyisi_leaderboard/queries/next_purchase_where.sql
WITH
cat AS (SELECT product_id::String AS pid, any(subcategory::String) AS s
        FROM (SELECT product_id, subcategory FROM shop.catalog
              UNION ALL SELECT product_id, subcategory FROM shop.catalog_updates WHERE change = 'new_product')
        GROUP BY pid),
m AS (
    SELECT p.u AS u, p.pid AS pid
    FROM (SELECT user_id::String AS u, product_id::String AS pid, ts::DateTime64(3) AS ts
          FROM shop.events WHERE event_type = 'purchase' AND ts > now() - INTERVAL 150 MINUTE) AS p
    ASOF INNER JOIN (SELECT user_id::String AS u, ts::DateTime64(3) AS rts
                     FROM shop.requests WHERE ts > now() - INTERVAL 150 MINUTE AND NOT is_new_user::Bool) AS r
         ON r.u = p.u AND r.rts <= p.ts
    WHERE p.ts <= r.rts + INTERVAL 30 MINUTE
),
sub_rank AS (  -- the shopper's purchase subcategories, most bought first
    SELECT u, s, p, row_number() OVER (PARTITION BY u ORDER BY p DESC, s) AS rk, count() OVER (PARTITION BY u) AS n_subs
    FROM (SELECT e.user_id::String AS u, k.subcategory::String AS s, count() AS p
          FROM shop.history_events AS e INNER JOIN shop.catalog AS k ON k.product_id::String = e.product_id::String
          WHERE e.event_type = 'purchase' AND e.user_id::String IN (SELECT u FROM m) GROUP BY u, s)
),
prod_rank AS (  -- products by all-time purchases inside their subcategory
    SELECT pid, row_number() OVER (PARTITION BY s ORDER BY p DESC, pid) AS rk
    FROM (SELECT e.product_id::String AS pid, any(k.subcategory::String) AS s, countIf(e.event_type = 'purchase') AS p
          FROM shop.history_events AS e INNER JOIN shop.catalog AS k ON k.product_id::String = e.product_id::String
          GROUP BY pid)
)
SELECT count()                                                              AS sellable_next_purchases,
       round(avg(sr.n_subs), 1)                                             AS avg_purchase_subcats_per_shopper,
       round(100 * countIf(sr.rk = 1) / count(), 1)                         AS pct_in_top1_subcat,
       round(100 * countIf(sr.rk BETWEEN 1 AND 3) / count(), 1)             AS pct_in_top3_subcats,
       round(100 * countIf(sr.rk BETWEEN 1 AND 5) / count(), 1)             AS pct_in_top5_subcats,
       round(100 * countIf(sr.rk BETWEEN 1 AND 10) / count(), 1)            AS pct_in_top10_subcats,
       round(100 * countIf(sr.rk > 0) / count(), 1)                         AS pct_in_any_purchase_subcat,
       round(100 * countIf(pr.rk <= 3) / count(), 1)                        AS pct_product_top3_of_its_subcat,
       round(100 * countIf(pr.rk <= 10) / count(), 1)                       AS pct_product_top10_of_its_subcat,
       round(100 * countIf(pr.rk <= 20) / count(), 1)                       AS pct_product_top20_of_its_subcat,
       round(100 * countIf(sr.rk BETWEEN 1 AND 3 AND pr.rk <= 3) / count(), 1)   AS pct_top3_subcats_x_top3_products,
       round(100 * countIf(sr.rk BETWEEN 1 AND 5 AND pr.rk <= 10) / count(), 1)  AS pct_top5_subcats_x_top10_products,
       round(100 * countIf(sr.rk BETWEEN 1 AND 10 AND pr.rk <= 20) / count(), 1) AS pct_top10_subcats_x_top20_products
FROM m
INNER JOIN cat AS cp ON cp.pid = m.pid
LEFT JOIN sub_rank AS sr ON sr.u = m.u AND sr.s = cp.s
LEFT JOIN prod_rank AS pr ON pr.pid = m.pid
LEFT JOIN (SELECT DISTINCT user_id::String AS u, product_id::String AS pid, 1 AS b
           FROM shop.history_events WHERE event_type = 'purchase') AS hb ON hb.u = m.u AND hb.pid = m.pid
WHERE hb.b = 0
