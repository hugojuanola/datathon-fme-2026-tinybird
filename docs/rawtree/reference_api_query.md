# Query (/docs/reference/api/query)



Query [#query]

Run RawTree SQL through the service API. RawTree is a ClickHouse fork. Its SQL capabilities extend beyond this HTTP endpoint.

SQL and REST capabilities [#sql-and-rest-capabilities]

| Capability              | REST method                            | SQL through Query API                                  |
| ----------------------- | -------------------------------------- | ------------------------------------------------------ |
| Create a RawTree table  | `POST /v1/tables`                      | Restricted `CREATE TABLE`                              |
| Insert JSON rows        | `POST /v1/tables/{table}`              | Use REST for JSON, `INSERT SELECT` for query results   |
| Empty a table           | No separate method                     | `TRUNCATE TABLE`                                       |
| Change a sorting key    | `PATCH /v1/tables/{table}`             | `ALTER TABLE … MODIFY ORDER BY`                        |
| Projections and indexes | No separate method                     | Supported `ALTER TABLE` operations                     |
| Roles and table grants  | No separate method                     | `CREATE ROLE`, `DROP ROLE`, `GRANT SELECT` or `INSERT` |
| Row policies            | No separate method                     | Supported `CREATE ROW POLICY` and `DROP ROW POLICY`    |
| Workloads and resources | No separate method                     | Supported `CREATE`, `CREATE OR REPLACE`, and `DROP`    |
| Settings profiles       | No separate method                     | Restricted workload and concurrency settings           |
| Named collections       | No separate method                     | Restricted `CREATE NAMED COLLECTION`                   |
| Handler definitions     | Create and list through `/v1/handlers` | `CREATE HANDLER`, `ALTER HANDLER`, `DROP HANDLER`      |

These are Query API restrictions. Direct database connections use RawTree SQL and database grants.
The service manages user and service-account identities. It does not expose arbitrary `CREATE USER` through the Query API.

POST `/v1/query-format` [#post-v1query-format]

Format SQL with the native RawTree formatter. Statements are parsed without
execution or database access, and do not enter `system.query_log`. Query logging
settings remain unchanged. All API key permission levels and signed-in sessions
can use this endpoint.

```json
{ "sql": "select 1" }
```

The response contains the complete formatted SQL:

```json
{ "formatted": "SELECT 1" }
```

The endpoint accepts multiple statements and preserves literal values, including
credentials written in SQL. It keeps an existing final semicolon and does not
add one when absent. The response has no trailing line breaks. Separators between
statements remain intact.
It runs in the normal backend service independently
of query and ingestion admission limits. Database `max_query_size` and query-log
truncation settings do not limit formatting.

Syntax checking follows the native formatter. Inline `INSERT ... VALUES` data
is copied verbatim without validating its completeness or the table schema.

The JSON request body is limited to 50 MiB. Formatting has a 30-second timeout
and a 100 MiB output limit. Syntax errors or excessive formatting complexity
return `400`, timeouts return `408`, oversized requests or output return `413`,
and unavailable or busy formatters return `503`. Errors never return partial formatted SQL.

Use an API key, a permitted workload token, or a user bearer token. Database-role keys support only the operations listed in [Authentication](/docs/reference/authentication#existing-database-roles).

Parameters:

| Field | Location | Type   | Required | Notes                                                          |
| ----- | -------- | ------ | -------- | -------------------------------------------------------------- |
| `sql` | body     | string | Yes      | Complete SQL to format. Statements are parsed, never executed. |

Request:

```bash
# Create query.
curl -X POST "https://api.rawtree.com/v1/query-format?database=analytics" \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "sql": "select 42 as answer"
}'
```

Expected response: **HTTP 200**.

```json
{
  "formatted": "SELECT 42 AS answer"
}
```

Errors: `400`, `401`, `403`, `408`, `413`, `503`. See [API errors](/docs/reference/errors).

POST `/v1/query` [#post-v1query]

Execute a SQL query.

Read-only queries support `SELECT`, `WITH`, `EXPLAIN`, and `DESCRIBE` statements:

```json
{ "sql": "SELECT * FROM events LIMIT 10" }
```

The Query API also supports changing a table's sorting key:

```json
{ "sql": "ALTER TABLE events MODIFY ORDER BY (region, user.id)" }
```

It can also manage projections on a table in the selected database:

| Action                                  | SQL                                                                                         |
| --------------------------------------- | ------------------------------------------------------------------------------------------- |
| Create                                  | `ALTER TABLE t ADD PROJECTION [IF NOT EXISTS] p (SELECT ... [GROUP BY ...] [ORDER BY ...])` |
| Build for existing data                 | `ALTER TABLE t MATERIALIZE PROJECTION [IF EXISTS] p`                                        |
| Delete stored data, keep the definition | `ALTER TABLE t CLEAR PROJECTION [IF EXISTS] p`                                              |
| Delete                                  | `ALTER TABLE t DROP PROJECTION [IF EXISTS] p`                                               |
| Stop a running build or clear           | `KILL MUTATION WHERE table = 't' [AND mutation_id = '...']`                                 |

```json
{ "sql": "ALTER TABLE events ADD PROJECTION by_region (SELECT `__raw_data.region`, count() GROUP BY `__raw_data.region`)" }
```

Projection definitions must refer to fields by their storage path,
`` `__raw_data.<field>` ``. Queries that use the plain field name, such as
`SELECT region, count() FROM events GROUP BY region`, can still use the
projection. A new projection applies only to data written after it was
created; use `MATERIALIZE PROJECTION` to build it for existing data.

`MATERIALIZE PROJECTION` and `CLEAR PROJECTION` return immediately and run in
the background. Follow their progress, and find the `mutation_id` to pass to
`KILL MUTATION`, in `system.mutations`. List projections with
`system.projections`. `KILL MUTATION` only matches mutations in the selected
database and returns one row per matched mutation.

The Query API supports indexes, including text indexes. See the
[ALTER TABLE reference](/docs/reference/sql/statements/alter-table#indexes).

ALTER and `KILL MUTATION` have these limits:

* They require admin permission or a signed-in session.
* One operation per `ALTER` statement. `ON CLUSTER` and `IN PARTITION` are not
  supported.
* The table must be in the selected database.
* `KILL MUTATION` string values accept literal characters and doubled single
  quotes (`'odd''name'`). Backslash escapes are not supported.

It can also create a table, with an optional sorting key and table settings. Only the
`ReplicatedRawMergeTree` engine is supported, and creating a table requires
admin permission:

```json
{ "sql": "CREATE TABLE IF NOT EXISTS events ENGINE = ReplicatedRawMergeTree ORDER BY (region, user.id)" }
```

Other engines, column definitions, engine arguments, `AS SELECT`, and clauses
other than `ORDER BY` and `SETTINGS` are rejected with a `400`. The error `hint` includes a
supported statement you can copy. Creating a table that already exists returns
`409` unless the statement uses `IF NOT EXISTS`.

Table settings use the engine's native validation. For example:

```sql
CREATE TABLE events ENGINE = ReplicatedRawMergeTree
ORDER BY user.id SETTINGS replacing_enable = 1, index_granularity = 4096;

ALTER TABLE events MODIFY SETTING max_parts_in_total = 100000;
ALTER TABLE events RESET SETTING max_parts_in_total;
```

Send each statement in a separate query request. `MODIFY SETTING` and
`RESET SETTING` require admin permission or a signed-in session. Some settings
can only be specified at creation. On databases using custom S3 storage,
`CREATE TABLE ... SETTINGS` is not supported and returns `400`. Create the table
without a `SETTINGS` clause.

The table details **Settings** tab displays only explicit table overrides that
can be changed after creation. Inherited engine defaults are omitted from the
list and editor. Creation-only and obsolete settings, `disk`, and `storage_policy` are excluded from
the list and cannot be changed through this editor. **Edit settings** opens a SQL
editor with the displayed values.
Edit or add comma-separated assignments; only changed or added values are sent to
the engine. Unchanged and omitted settings stay as they are. The engine validates
which settings can be changed. Unchanged inherited values remain inherited when
saving. The editor requires a custom
sorting key before enabling replacement. Rows with the same sorting key,
including missing or NULL key values, can be deduplicated during merges or by
`FINAL`. Turning replacement off does not recover removed rows.

`GET /v1/tables/{table}/settings` returns editable `settings` with `name`, `value`
(SQL syntax), and `level` (`Table` or `Inherited`), plus `sorting_key`, the effective
`replacing_enable` value, and
`can_update`. This API includes inherited defaults for validation; the editor displays
only rows whose level is `Table`. `GET /v1/tables/{table}` still returns the full stored settings.
`replacing_enable` is null on engines without replacement support.
`PATCH /v1/tables/{table}/settings` accepts SQL assignments from the editor:

```json
{"settings": "max_parts_in_total = 100000, max_suspicious_broken_parts = 17"}
```

It applies changed or added values and preserves omitted settings. Duplicate
names and subqueries are rejected. The existing `{"replacing_enable": true}`
request is also supported. Both forms require admin permission or a signed-in
session. Use Query API `RESET SETTING` to restore engine defaults.

To materialize query results into another table, such as a rollup or a cleaned
copy of raw events, use `INSERT INTO ... SELECT`:

```json
{
  "sql": "INSERT INTO daily_clicks SELECT toDate(timestamp) AS day, count() AS clicks FROM events GROUP BY day"
}
```

`INSERT INTO ... SELECT` has these limits:

* The target table must already exist in the selected database. Create it with
  `CREATE TABLE`, `POST /v1/tables`, or by inserting data first.
* The API key needs both read and write permission.
* URL table functions (`url()` and `urlCluster()`) are rejected.
* `SETTINGS` clauses are passed to RawTree for validation and execution.
* `INSERT ... VALUES` and `INSERT ... FORMAT` are not supported; send JSON rows
  to `POST /v1/tables/{table}` instead.
* The Query API supplies a default `max_execution_time` of 30 seconds. An explicit
  `SETTINGS` clause can override it.

The response is an empty result set. `statistics.written_rows` reports how many
rows were inserted:

```json
{
  "meta": [],
  "data": [],
  "rows": 0,
  "statistics": { "elapsed": 0.42, "rows_read": 120000, "bytes_read": 9600000, "written_rows": 31 }
}
```

Use an API key, a permitted workload token, or a user bearer token. Database-role keys support only the operations listed in [Authentication](/docs/reference/authentication#existing-database-roles).

Parameters:

| Field      | Location | Type           | Required | Notes                                                                                                                                                                                                |
| ---------- | -------- | -------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sql`      | body     | string         | Yes      | —                                                                                                                                                                                                    |
| `query_id` | body     | string or null | No       | —                                                                                                                                                                                                    |
| `format`   | body     | string or null | No       | Optional ClickHouse output format. Defaults to JSON. JSONEachRowWithProgress streams read-query records; errors after headers are reported in the body and clients must consume the complete stream. |

Request:

```bash
# Execute SQL query and return results in the requested ClickHouse format.
curl -X POST "https://api.rawtree.com/v1/query?database=analytics" \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "sql": "SELECT 42 AS answer",
  "query_id": "docs-query-42"
}'
```

Expected response: **HTTP 200**.

```json
{
  "meta": [
    {
      "name": "answer",
      "type": "UInt8"
    }
  ],
  "data": [
    {
      "answer": 42
    }
  ],
  "rows": 1,
  "statistics": {
    "elapsed": 0.001,
    "rows_read": 1,
    "bytes_read": 1
  }
}
```

Errors: `400`, `401`, `403`, `408`, `409`, `413`, `429`. See [API errors](/docs/reference/errors).

SQL-defined HTTP endpoints [#sql-defined-http-endpoints]

Use [Handlers](/docs/reference/api/handlers) to create, list, and call named query endpoints through REST.
Alteration and deletion use SQL through `POST /v1/query`. These requests require an organization administrator or an admin API key.

```sql
CREATE HANDLER double_number ON CLUSTER 'default'
URL '/double-number'
METHODS (GET)
AS SELECT {n:UInt32} * 2 AS result
FORMAT JSONEachRow;
```

```sql
ALTER HANDLER double_number ON CLUSTER 'default'
URL '/double-number'
AS SELECT {n:UInt32} * 3 AS result FORMAT JSONEachRow;
```

```sql
DROP HANDLER IF EXISTS double_number ON CLUSTER 'default';
```

Send each statement in its own request. Handler SQL executes as submitted.
The service does not insert `ON CLUSTER`, `METHODS`, or rewrite URLs in SQL requests.
Omit `ON CLUSTER` for native local scope, or include it when the cluster requires distributed DDL.
After a distributed-DDL timeout, inspect the replicas before retrying. Timed-out DDL can still finish in the background.

Query response format [#query-response-format]

The optional `format` field selects the database response format. It defaults
to `JSON`, and supports `JSONEachRow`, `JSONEachRowWithProgress`, `JSONCompact`,
`CSV`, `CSVWithNames`, `TSV`, `TSVWithNames`, and `TabSeparated`. For formats
other than `JSON`, the response body is returned in the requested raw format.
For example:

```json
{
  "sql": "EXPLAIN SELECT 1",
  "format": "JSONEachRowWithProgress"
}
```

For read queries, `JSONEachRowWithProgress` streams newline-delimited JSON
records as the engine produces them, with content type `application/x-ndjson`.
Records include progress, column metadata, rows, and optional totals or extremes.
Progress can arrive before metadata. Network chunks can contain partial records
or several records; split on newlines after incrementally decoding UTF-8.
Request gzip compression with `Accept-Encoding: gzip`.

Validation and upstream errors detected before the response starts use the usual
HTTP error status and JSON error body. After streaming starts, HTTP `200` does
not establish query success: a query can end with a top-level `exception` record,
or the connection can fail. Consume the entire stream, check for exceptions, and
treat results from an unsuccessful transfer as incomplete. The API does not
retry a query after handing its response stream to the client.

The standard query defaults apply. See [Limits](/docs/reference/limits) for execution-time and result-size settings. Supply
`query_id` and use `/v1/query/cancel` to cancel execution; closing the download
alone does not confirm server-side cancellation. Default `JSON` responses and
write-statement completion handling remain buffered.

Default `JSON` response without query hints:

```json
{
  "meta": [{ "name": "action", "type": "String" }],
  "data": [{ "action": "click" }],
  "rows": 1,
  "statistics": { "elapsed": 0.001, "rows_read": 1, "bytes_read": 128 }
}
```

When the engine records runtime type-compatibility warnings, the JSON result
also contains `hints`, an array of diagnostic strings. The engine omits this
field when the list is empty. These warnings can accompany a successful query
that skips incompatible `Dynamic` values or substitutes `NULL` or default results.

Messages identify the function and incompatible concrete types. They can also
include the column name, expression, and query scope. Identical messages are
deduplicated per query. They do not include an affected-row count.

Some operations can skip incompatible values without a hint.
See [Runtime type-compatibility warnings](/docs/concepts/dynamic-fields#runtime-type-compatibility-warnings)
for the supported cases and limits. The singular `hint` in an
[API error response](/docs/reference/errors) gives guidance for a failed request.

Row policies [#row-policies]

Organization administrators and admin API keys can create row policies through
`/v1/query`. A policy filters the rows that an existing database role can read
from one table. Select the table's database with `database=<name>` and send each
statement in a separate request:

```sql
CREATE ROW POLICY acme_events ON events
FOR SELECT USING __raw_data.tenant_id::String = 'acme'
TO analytics_reader;
```

The role must already exist and have a `SELECT` grant on the table. Create an
API key with `database_roles: ["analytics_reader"]` to query as that role; see
[database-role keys](/docs/reference/authentication#existing-database-roles).
Permission-based keys and user sessions do not assume this role.

Supported statements are `CREATE ROW POLICY [IF NOT EXISTS | OR REPLACE]` and
`DROP ROW POLICY [IF EXISTS]`. `OR REPLACE` replaces the complete definition,
including its role targets:

```sql
CREATE ROW POLICY OR REPLACE acme_events ON events
FOR SELECT USING __raw_data.tenant_id::String = 'acme' AND __raw_data.environment::String = 'production'
TO analytics_reader;
```

```sql
DROP ROW POLICY IF EXISTS acme_events ON events;
```

An optional `ON CLUSTER 'default'` can appear immediately before or after
`ON database.table`. With `ON CLUSTER`, the database must be explicit and match
the selected database; unqualified targets are rejected because distributed
access DDL can otherwise resolve a replica's default database. Omit `ON CLUSTER`
when using replicated access storage; otherwise
include it to apply the statement to every current replica. The API preserves
this choice and reports distributed DDL errors. With replicated access storage,
plain `CREATE` or `DROP` combined with `ON CLUSTER` can race between replicas;
use `IF NOT EXISTS` or `IF EXISTS` when sending those forms.

Policies default to `AS PERMISSIVE`; `AS RESTRICTIVE` is also supported before
or after the `USING` filter. Matching permissive policies combine with **OR**,
then matching restrictive policies combine with **AND**. A restrictive policy
needs a matching permissive policy to allow any rows.

RawTree currently allows readers without any matching policy to keep their
existing access. Creating a policy for one role does not restrict other roles,
permission-based keys, or user sessions. This depends on the server setting
`access_control_improvements.users_without_row_policies_can_read_rows`; disabling
it denies rows to readers without a matching permissive policy. Plan policies
for every role that needs restricted access. Policies filter `SELECT` results;
they do not constrain inserts or provide isolation from users who can modify
tables. Use read-only roles for row-restricted readers.

Each request accepts one policy on one table in the selected user database,
a scalar filter expression, and 1–32 distinct existing roles. Cross-database
targets, wildcards, subqueries, user targets, `ALL`, `ALL EXCEPT`, `NONE`,
`CURRENT_USER`, `ALTER ROW POLICY`, and access-storage selectors are unsupported.
Role names that collide with database user names are rejected. System databases
and the internal organization do not support policy management.

Workload scheduling [#workload-scheduling]

Separate interactive queries and batch processing into named workloads with
CPU and disk I/O scheduling policies. Organization administrators and admin API
keys can manage definitions through `/v1/query`:

```sql
CREATE WORKLOAD all ON CLUSTER 'default' SETTINGS max_concurrent_threads = 8;
CREATE WORKLOAD default ON CLUSTER 'default' IN all;
CREATE WORKLOAD interactive ON CLUSTER 'default' IN all SETTINGS weight = 3;
CREATE WORKLOAD batch ON CLUSTER 'default' IN all SETTINGS weight = 1;
CREATE RESOURCE cpu ON CLUSTER 'default' (MASTER THREAD, WORKER THREAD);
```

Send **each statement in its own request**, using the `sql` field. Definitions
are independent of the selected database. Choose replication according to the
cluster's workload storage:

* **Local workload storage:** include `ON CLUSTER 'default'` after the object name,
  as in the example, to apply the definition to the cluster's current replicas.
  Without it, the statement affects only the server that receives the request.
* **Keeper-backed workload storage** (`workload_zookeeper_path`): omit `ON CLUSTER`;
  the engine replicates definitions automatically and rejects `ON CLUSTER`.

The API preserves this choice. Other cluster names, multiple statements, and
backslash escapes in identifiers are rejected. The internal organization
does not support scheduling management.

Supported management statements:

* `CREATE WORKLOAD [IF NOT EXISTS] <name> [IN <parent>] [SETTINGS ...]`
* `CREATE OR REPLACE WORKLOAD <name> [IN <parent>] [SETTINGS ...]`
* `DROP WORKLOAD [IF EXISTS] <name>`
* `CREATE RESOURCE [IF NOT EXISTS] <name> (<operations>)`
* `CREATE OR REPLACE RESOURCE <name> (<operations>)`
* `DROP RESOURCE [IF EXISTS] <name>`

Resource operations are `MASTER THREAD`, `WORKER THREAD`, `READ DISK <name>`,
`WRITE DISK <name>`, `READ ANY DISK`, and `WRITE ANY DISK`. Memory reservation
and query-slot resources are not supported by this API. Workload settings accept
numeric or string literals and an optional `FOR <resource>` per setting; the
engine validates setting names, values, and hierarchy constraints. For example:

```json
{
  "sql": "CREATE OR REPLACE WORKLOAD batch ON CLUSTER 'default' IN all SETTINGS weight = 1, max_concurrent_threads = 2"
}
```

Replacement supplies the full definition. Remove children before dropping their
parent, and remove resource-specific workload settings before dropping the
referenced resource. Successful management returns the same empty result shape
as other DDL. A replica error or distributed DDL timeout returns an error;
cluster DDL is not transactional, so inspect the definitions before retrying.
With local workload storage, provision the same definitions when adding replicas.
Keeper-backed storage supplies definitions to new replicas automatically; configure
it in the cluster infrastructure and omit `ON CLUSTER` from management requests.

Select a leaf workload for a read query or `INSERT INTO ... SELECT` using a SQL
`SETTINGS` clause:

```json
{
  "sql": "SELECT count() FROM events SETTINGS workload = 'interactive'"
}
```

Read-only and custom database-role keys can select a workload while retaining
their existing data permissions. Workload selection does not grant access to
tables.

Scheduling only takes effect when
resources and the referenced workload exist. The engine's default workload is
`default`; with `throw_on_unknown_workload` disabled, unknown names bypass
scheduling. This endpoint does not change that server policy. For enforced CPU
scheduling, operators must also constrain `use_concurrency_control` so callers
cannot disable it. CPU limits apply per server, not as one cluster-wide budget.
See the upstream [ClickHouse workload scheduling reference](https://clickhouse.com/docs/operations/workload-scheduling)
for resource configuration and enforcement.

Inspect definitions and scheduling activity with `SELECT` queries against
`system.workloads`, `system.resources`, and `system.scheduler` using a key with
access to those system tables.

Workload settings profiles [#workload-settings-profiles]

Assign a default workload to a database role so its API keys do not need a
`SETTINGS workload` clause on every query. Organization administrators and admin
API keys can create, replace, and drop workload settings profiles through
`/v1/query`. Create the role and workload first, then send this SQL in the `sql`
field:

```sql
CREATE SETTINGS PROFILE interactive_profile
SETTINGS workload = 'interactive'
TO app_reader;
```

API keys with `database_roles: ["app_reader"]` inherit the default. Without a
constraint, callers can choose another workload in SQL. To lock the workload
and prevent callers from disabling CPU concurrency control, replace the profile:

```sql
CREATE SETTINGS PROFILE OR REPLACE interactive_profile
SETTINGS workload = 'interactive' READONLY, use_concurrency_control = 1 CONST
TO app_reader;
```

`READONLY` and `CONST` lock the individual setting; they do not grant or remove
table permissions. Profiles apply to existing and newly created API keys using
the selected roles. Replacement supplies the entire definition, including the
role list. Custom-role keys retain their existing Query API restrictions.

Supported statements are `CREATE SETTINGS PROFILE [IF NOT EXISTS]`,
`CREATE SETTINGS PROFILE OR REPLACE`, and `DROP SETTINGS PROFILE [IF EXISTS]`.
Submit one profile and one statement per request. Profile settings are limited
to `workload` (a nonempty string) and `use_concurrency_control` (`0` or `1`), with
optional `READONLY` or `CONST` constraints. Creation requires `TO` followed by
1–32 distinct existing roles without same-named database users. User targets, `ALL`, `NONE`, inheritance, other
settings, and `ALTER SETTINGS PROFILE` are not supported. Profile management is
not available to non-admin callers, workflows, or the internal organization.

An optional `ON CLUSTER 'default'` after the profile name retains ClickHouse's
native access-storage behavior. Settings profiles use access storage, which is
separate from workload storage: with replicated access storage, profiles
replicate automatically; local access storage needs `ON CLUSTER` for all current
replicas. Omit `ON CLUSTER` with replicated access storage to avoid duplicate
creation or deletion as access entities replicate between nodes. The API does
not add the clause. Other cluster names are rejected.

```sql
DROP SETTINGS PROFILE IF EXISTS interactive_profile;
```

See the upstream [ClickHouse settings profile reference](https://clickhouse.com/docs/sql-reference/statements/create/settings-profile)
for the underlying SQL syntax. Workloads and resources must still be configured
for scheduling to take effect.

Named collections [#named-collections]

Create named collections through `/v1/query`. See the
[named collection reference](/docs/reference/sql/statements/named-collection).

SQL management request examples [#sql-management-request-examples]

Use an administrator credential for these requests. Create the target table and roles before you assign grants or policies.
Send one statement per request. Each example assumes the earlier objects exist.
The SQL sections above describe restrictions, replication, and supported variants.

Create a database role [#create-a-database-role]

```bash
# Create a database role.
curl -X POST 'https://api.rawtree.com/v1/query?database=analytics' \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "sql": "CREATE ROLE IF NOT EXISTS analytics_reader"
}
JSON
```

Expected response: **HTTP 200**, with an empty result set.

```json
{
  "meta": [],
  "data": [],
  "rows": 0,
  "statistics": {
    "elapsed": 0.001,
    "rows_read": 0,
    "bytes_read": 0
  }
}
```

Grant table reads [#grant-table-reads]

```bash
# Grant table reads.
curl -X POST 'https://api.rawtree.com/v1/query?database=analytics' \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "sql": "GRANT SELECT ON analytics.events TO analytics_reader"
}
JSON
```

Expected response: **HTTP 200**, with an empty result set.

```json
{
  "meta": [],
  "data": [],
  "rows": 0,
  "statistics": {
    "elapsed": 0.001,
    "rows_read": 0,
    "bytes_read": 0
  }
}
```

Create a row policy [#create-a-row-policy]

```bash
# Create a row policy.
curl -X POST 'https://api.rawtree.com/v1/query?database=analytics' \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "sql": "CREATE ROW POLICY IF NOT EXISTS acme_events ON events FOR SELECT USING __raw_data.tenant_id::String = 'acme' TO analytics_reader"
}
JSON
```

Expected response: **HTTP 200**, with an empty result set.

```json
{
  "meta": [],
  "data": [],
  "rows": 0,
  "statistics": {
    "elapsed": 0.001,
    "rows_read": 0,
    "bytes_read": 0
  }
}
```

Create a workload [#create-a-workload]

```bash
# Create a workload.
curl -X POST 'https://api.rawtree.com/v1/query?database=analytics' \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "sql": "CREATE WORKLOAD IF NOT EXISTS interactive"
}
JSON
```

Expected response: **HTTP 200**, with an empty result set.

```json
{
  "meta": [],
  "data": [],
  "rows": 0,
  "statistics": {
    "elapsed": 0.001,
    "rows_read": 0,
    "bytes_read": 0
  }
}
```

Create a settings profile [#create-a-settings-profile]

```bash
# Create a settings profile.
curl -X POST 'https://api.rawtree.com/v1/query?database=analytics' \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "sql": "CREATE SETTINGS PROFILE IF NOT EXISTS interactive_profile SETTINGS workload = 'interactive' TO analytics_reader"
}
JSON
```

Expected response: **HTTP 200**, with an empty result set.

```json
{
  "meta": [],
  "data": [],
  "rows": 0,
  "statistics": {
    "elapsed": 0.001,
    "rows_read": 0,
    "bytes_read": 0
  }
}
```

Create a named collection [#create-a-named-collection]

```bash
# Create a named collection.
curl -X POST 'https://api.rawtree.com/v1/query?database=analytics' \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "sql": "CREATE NAMED COLLECTION IF NOT EXISTS event_source AS url = 'https://example.com/events.json'"
}
JSON
```

Expected response: **HTTP 200**, with an empty result set.

```json
{
  "meta": [],
  "data": [],
  "rows": 0,
  "statistics": {
    "elapsed": 0.001,
    "rows_read": 0,
    "bytes_read": 0
  }
}
```

Alter a handler [#alter-a-handler]

```bash
# Alter a handler.
curl -X POST 'https://api.rawtree.com/v1/query?database=analytics' \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "sql": "ALTER HANDLER double_number URL '/double' AS SELECT {value:UInt64} * 3 AS doubled FORMAT JSONEachRow"
}
JSON
```

Expected response: **HTTP 200**, with an empty result set.

```json
{
  "meta": [],
  "data": [],
  "rows": 0,
  "statistics": {
    "elapsed": 0.001,
    "rows_read": 0,
    "bytes_read": 0
  }
}
```

Drop a handler [#drop-a-handler]

```bash
# Drop a handler.
curl -X POST 'https://api.rawtree.com/v1/query?database=analytics' \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "sql": "DROP HANDLER IF EXISTS double_number"
}
JSON
```

Expected response: **HTTP 200**, with an empty result set.

```json
{
  "meta": [],
  "data": [],
  "rows": 0,
  "statistics": {
    "elapsed": 0.001,
    "rows_read": 0,
    "bytes_read": 0
  }
}
```

Table retention [#table-retention]

The Query API accepts `CREATE TABLE ... TTL <expression>` and
`ALTER TABLE <table> MODIFY TTL <expression>` with an optional `DELETE WHERE <condition>`.
See [CREATE TABLE](/docs/reference/sql/statements/create-table#row-retention) and
[ALTER TABLE](/docs/reference/sql/statements/alter-table#row-retention) for missing-field behavior and examples.

Empty a table [#empty-a-table]

`TRUNCATE` removes all rows and keeps the table, sorting key, TTL, and settings.
It requires `admin`, `read_write`, or `write_only` permission. Read-only and database-role keys cannot truncate through this API.

```sql
TRUNCATE TABLE [IF EXISTS] [database.]<table> [SYNC]
```

Send the statement to `POST /v1/query`:

```json
{"sql": "TRUNCATE TABLE events"}
```

The table must belong to the selected database. `IF EXISTS` succeeds when the table is absent.
The API always waits for replica completion, including when you omit `SYNC`.
An unavailable replica can cause the request to fail after other replicas have already removed data.

Submit one table per request. Database-wide truncation, multiple tables, `ON CLUSTER`, and extra clauses are not accepted.
Workflows do not accept `TRUNCATE`.

Stop concurrent writers and wait for pending inserts before truncating a table for a full reload.
Truncate-and-reload is not atomic: readers can see an empty or partially reloaded table.
`EXCHANGE TABLES`, `RENAME TABLE`, and workflow replacement remain unsupported.
