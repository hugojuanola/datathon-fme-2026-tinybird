-- Is our system healthy? Last 10 minutes of our feedback, split by who served the shopper.
-- Healthy = almost everything served_by = 'team' and p95 latency well under 3000 ms.
--   python3 scripts/rt.py -f queries/health.sql
SELECT served_by::String       AS served_by,
       fallback_reason::String AS reason,
       count()                 AS requests,
       round(100 * countIf(clicked != '') / count(), 2)   AS ctr_pct,
       round(100 * countIf(purchased != '') / count(), 2) AS conversion_pct,
       round(sum(revenue_eur::Float64) / count(), 3)      AS eur_per_request,
       round(quantileIf(0.5)(latency_ms::Float64, latency_ms IS NOT NULL))  AS p50_latency_ms,  -- null when the fallback served
       round(quantileIf(0.95)(latency_ms::Float64, latency_ms IS NOT NULL)) AS p95_latency_ms
FROM team_NN.feedback
WHERE ts > now() - INTERVAL 10 MINUTE AND request_id != '__init__'
GROUP BY served_by, reason
ORDER BY requests DESC
