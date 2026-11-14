# RawTree cheat sheet

RawTree (by Tinybird) is a schema-free analytics database: **JSON in, SQL out**. It is a ClickHouse fork,
so ClickHouse SQL and functions apply. This page is what an agent needs for the challenge; the vendored
official docs are in [`rawtree/`](rawtree/) and the full index is [`sources/rawtree-llms.txt`](sources/rawtree-llms.txt)
(live: <https://rawtree.com/llms.txt>).

## Access

| | |
|---|---|
| API base | `https://api.rawtree.com` |
| Auth | `Authorization: Bearer $RAWTREE_API_KEY` |
| Our databases | read `shop`, read/write `team_06` |
| Credentials | `.env` at the repo root (`TEAM_ID`, `RAWTREE_API_KEY`). Never commit, print or paste the key. |

Our key is verified to work for `POST /v1/query` (reads on `shop.*` and `team_06.*`) and for the hosted MCP server.

## Three ways to talk to it

### 1. Repo helper (no install, stdlib only) — default for agents

```bash
python3 scripts/rt.py "SELECT count() FROM shop.requests"
python3 scripts/rt.py --json "SELECT * FROM team_NN.feedback ORDER BY ts DESC LIMIT 5"   # team_NN → $TEAM_ID
python3 scripts/rt.py --stats -f some_query.sql      # rows/bytes read + type hints on stderr
python3 scripts/leaderboard.py                       # public leaderboard, our team marked
```

`rt.py` refuses anything that is not `SELECT / WITH / EXPLAIN / DESCRIBE` unless `--write` is passed.

### 2. HTTP API

```bash
# Query
curl -s https://api.rawtree.com/v1/query \
  -H "Authorization: Bearer $RAWTREE_API_KEY" -H "Content-Type: application/json" \
  -d '{"sql": "SELECT count() FROM shop.requests"}'

# Insert (one object or an array of objects) — this is how answers are submitted
curl -s "https://api.rawtree.com/v1/tables/submissions?database=team_06" \
  -H "Authorization: Bearer $RAWTREE_API_KEY" -H "Content-Type: application/json" \
  -d '[{"request_id": "r_...", "items": ["p_...", "..."], "model_version": "v1"}]'
```

- Query response (default `format: "JSON"`): `{"meta": [...], "data": [{col: value}], "rows": n,
  "statistics": {"elapsed", "rows_read", "bytes_read"}, "hints": [...]}`. `hints` is optional and reports
  Dynamic values that were skipped or defaulted — check it when a number looks off.
- Body: `sql` plus optional `query_id` and `format`. **There are no bound parameters**: build the final SQL
  string in code and escape literals yourself.
- Database selection: `?database=<name>` or header `x-rawtree-database`; otherwise the key's default.
  Fully-qualified names (`shop.catalog`, `team_06.feedback`) work in any case.
- Insert response: `{"written_rows": "N", ...}`. Inserts are append-only; a failed request may still have
  written rows. Optional `insert_deduplication_token` / `deduplicate_insert` query parameters exist.
- Accepted statement starts: `SELECT`, `WITH`, `EXPLAIN`, `DESCRIBE`, `INSERT INTO ... SELECT`,
  `CREATE TABLE`, `ALTER TABLE`, `TRUNCATE TABLE`, plus role/workload/handler management. `SHOW ...` is rejected.
  Creating tables and `ALTER` need admin permission, which a team key may not have.
- OpenAPI: <https://api.rawtree.com/v1/openapi.json>

### 3. MCP server and CLI (optional)

```bash
# Claude Code — local scope, so the key stays out of the repo
claude mcp add --transport http rawtree https://mcp.rawtree.com/mcp \
  --header "Authorization: Bearer $RAWTREE_API_KEY"

# CLI
curl -fsSL https://rawtree.com/install.sh | bash
rtree query --api-key $RAWTREE_API_KEY --database $TEAM_ID "SELECT count() FROM shop.requests"
```

The official RawTree agent skill is vendored at [`.claude/skills/rawtree/`](../.claude/skills/rawtree/SKILL.md)
(Claude Code loads it automatically; other agents can read the files directly).

## Limits that matter here

| Limit | Value | When exceeded |
|---|---|---|
| Query execution time | **30 s** | HTTP 408 `request_timeout` |
| Query result size | 100 MiB | HTTP 400 |
| Query requests | 10,000 /s per database | HTTP 429 (honour `retry-after`) |
| Insert requests | 1,000 /s per table | HTTP 429 |
| Insert body | 100 MiB | HTTP 413 |

The 30 s cap and the 100 MiB result cap are what shape bulk exports: pull the 12 M-row history in
time-sliced or aggregated chunks, never with one `SELECT *`.

## SQL on Dynamic columns — the rules

Every JSON leaf is `Dynamic`: each row keeps its own concrete type.

```sql
-- Cast join keys, argMax/argMin arguments, and anything you aggregate or group by
SELECT c.category::String AS category, count() AS n
FROM shop.events AS e
INNER JOIN shop.catalog AS c ON c.product_id::String = e.product_id::String
WHERE e.event_type = 'purchase' AND e.ts > now() - INTERVAL 1 HOUR
GROUP BY category ORDER BY n DESC;

-- Inspect what is really stored
SELECT dynamicType(recent_views) AS t, count() FROM shop.requests GROUP BY t;

-- Inspect a table
DESCRIBE TABLE shop.requests SETTINGS describe_include_subcolumns = 1;
SELECT name, total_rows FROM system.tables WHERE database IN ('shop', 'team_06');
```

- Casts you will use constantly: `::String`, `::Float64`, `::Bool`, `::DateTime64(3)`,
  `::Array(String)`, `::Array(Float64)`.
- `x::T` is strict and turns a missing value into the type default (`''`, `0`): that can create false join
  matches. `accurateCastOrNull(x, 'T')` returns `NULL` instead, but it blocks index use on key columns.
- Presence: use `x IS NOT NULL` / `countIf(x IS NOT NULL)`. `count(x)` can count null Dynamic wrappers.
- A known path missing in a row is `NULL`; a path that exists in no row raises `UNKNOWN_IDENTIFIER`
  (this is why queries on a table with zero rows fail).
- Nested objects are sub-paths: `context.device`, `context.page`. Arrays of objects:
  `recent_views[-1].product_id::String`, `arrayJoin(recent_views)`, `arrayMap(v -> v.product_id::String, recent_views)`.
- Aggregates silently skip values of incompatible types (`sum` over a column holding strings and numbers).
  When a result looks wrong, check `hints` and `dynamicType`.
- Storage order is not result order: always `ORDER BY` explicitly.

## Performance habits

- Select named columns, not `SELECT *`, in anything that runs in the live loop.
- Always bound live-table reads with a time filter (`ts > now() - INTERVAL 10 SECOND`) plus `ORDER BY ts DESC LIMIT n`.
- Aggregate inside RawTree and return the summary; do not ship raw rows to Python to count them.
- Compare variants with `EXPLAIN indexes = 1` and the `statistics.rows_read` / `bytes_read` of the response.
- For anything queried on every request, precompute it (in memory, or in `team_06.scratch`) instead of
  re-running a heavy query 3 times a second.

## Worth knowing for the "Use of RawTree" jury points (5)

The jury looks at features computed in SQL, embeddings, and how the pipeline reads and writes. RawTree offers:

- `team_06.scratch`: free schemaless table for features, embeddings and model outputs.
- `INSERT INTO ... SELECT` to materialise query results into a table (`rawtree/reference_sql_statements_insert-select.md`).
- **SQL workflows**: saved SQL run on demand or on a schedule, with results delivered to sinks
  (`rawtree/guides_transform_workflows.md`, `rawtree/concepts_sql-workflows.md`).
- Transforms applied at insert time (`rawtree/guides_transform_transforms.md`).
- Projections and sorting keys for hot query shapes (`rawtree/reference_sql_statements_alter-table.md`).

Whether our team key has the permission for each of these is **not verified yet**: test with a harmless
statement before designing around one.

## Starter SQL

[`starter/queries.sql`](../starter/queries.sql) has seven ready examples: current catalogue, popularity per
category in the last hour, trending subcategories (15 min vs the previous 3 h), co-views, feedback
conversion per hour, reliability/latency, and position bias.
