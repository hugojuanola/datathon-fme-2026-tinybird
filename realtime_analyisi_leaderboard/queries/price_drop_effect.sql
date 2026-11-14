-- Do shoppers react to a price drop? At 10:30 UTC on 14 Nov ~620 products dropped ≈18-20% (shop.catalog_updates,
-- change = 'price_change'). Compare the hour before and the hour after, discounted products vs all the others
-- (difference in differences on organic shop.events). The final round announces its own price changes.
--   python scripts/rt.py -f realtime_analyisi_leaderboard/queries/price_drop_effect.sql
SELECT if(d.pid != '', 'price dropped at 10:30', 'price unchanged')              AS products,
       if(e.ts < '2026-11-14 10:30:00', '1 hour before', '2 hour after')         AS period,
       uniqExact(e.pid)                                                          AS n_products,
       countIf(e.ev = 'view')                                                    AS views,
       countIf(e.ev = 'add_to_cart')                                             AS carts,
       countIf(e.ev = 'purchase')                                                AS purchases,
       round(100 * countIf(e.ev = 'add_to_cart') / countIf(e.ev = 'view'), 2)    AS carts_per_100_views,
       round(100 * countIf(e.ev = 'purchase') / countIf(e.ev = 'view'), 2)       AS purchases_per_100_views
FROM (SELECT product_id::String AS pid, event_type::String AS ev, ts::DateTime64(3) AS ts FROM shop.events
      WHERE ts >= '2026-11-14 09:30:00' AND ts < '2026-11-14 11:30:00') AS e
LEFT JOIN (SELECT DISTINCT product_id::String AS pid FROM shop.catalog_updates
           WHERE change = 'price_change' AND ts < '2026-11-14 11:00:00') AS d ON d.pid = e.pid
GROUP BY products, period
ORDER BY products, period
