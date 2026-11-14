-- Compare the variants we have served: conversion, revenue and latency per model_version.
-- The model_version of each answer lives in team_NN.submissions; the outcome in team_NN.feedback.
--   python scripts/rt.py -f queries/variants.sql
SELECT s.model_version AS model_version,
       count()                                              AS requests,
       round(100 * countIf(f.clicked != '') / count(), 2)   AS ctr_pct,
       round(100 * countIf(f.purchased != '') / count(), 2) AS conversion_pct,
       round(sum(f.revenue_eur::Float64) / count(), 3)      AS eur_per_request,
       round(quantile(0.5)(f.latency_ms::Float64))          AS p50_latency_ms,
       round(quantile(0.95)(f.latency_ms::Float64))         AS p95_latency_ms,
       min(f.ts::DateTime64(3))                             AS first_seen,
       max(f.ts::DateTime64(3))                             AS last_seen
FROM (SELECT request_id::String AS rid, clicked::String AS clicked, purchased::String AS purchased,
             revenue_eur, latency_ms, ts
      FROM team_NN.feedback
      WHERE served_by = 'team' AND request_id != '__init__') AS f
INNER JOIN (SELECT request_id::String AS rid, any(model_version::String) AS model_version
            FROM team_NN.submissions GROUP BY rid) AS s ON s.rid = f.rid
GROUP BY model_version
ORDER BY first_seen
