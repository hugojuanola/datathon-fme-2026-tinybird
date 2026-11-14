-- Which tier of the ranking earns the purchases? One row per (tier, slot) from what we served.
-- team_NN.scratch holds, for every answer, the tier each product came from (written by reco/serve.py).
--   python scripts/rt.py -f queries/tiers.sql
SELECT tier,
       count()                                   AS impressions,
       round(avg(slot), 1)                       AS avg_slot,
       sum(click)                                AS clicks,
       sum(buy)                                  AS purchases,
       round(100 * sum(click) / count(), 2)      AS ctr_pct,
       round(100 * sum(buy) / count(), 3)        AS conversion_pct
FROM (
    SELECT arrayJoin(arrayZip(s.items, s.tiers, range(1, 11))) AS t, t.1 AS pid, t.2 AS tier, t.3 AS slot,
           f.clicked = pid AS click, f.purchased = pid AS buy
    FROM (SELECT request_id::String AS rid, any(items::Array(String)) AS items, any(tiers::Array(String)) AS tiers
          FROM team_NN.scratch WHERE kind = 'served' GROUP BY rid) AS s
    INNER JOIN (SELECT request_id::String AS rid, clicked::String AS clicked, purchased::String AS purchased
                FROM team_NN.feedback WHERE served_by = 'team') AS f ON f.rid = s.rid
)
GROUP BY tier
ORDER BY conversion_pct DESC
