# CREATE TABLE (/docs/reference/sql/statements/create-table)



CREATE TABLE [#create-table]

This page describes statements accepted by the Query API in RawTree Cloud
and RawTree BYOC. Its restrictions apply to the API, not to all RawTree SQL.
See [ClickHouse compatibility and API scope](/docs/reference/clickhouse-compatibility).

Syntax [#syntax]

```sql
CREATE TABLE [IF NOT EXISTS] <table>
  ENGINE = ReplicatedRawMergeTree
  [ORDER BY <expressions>]
  [TTL <expression> [DELETE [WHERE <condition>]]]
  [SETTINGS <name> = <value> [, ...]]
```

`CREATE TABLE` requires admin permission. The table belongs to the selected
database.

Clauses [#clauses]

| Clause          | Meaning                                                                  |
| --------------- | ------------------------------------------------------------------------ |
| `IF NOT EXISTS` | Do not return an error when the table exists.                            |
| `ENGINE`        | Use `ReplicatedRawMergeTree`.                                            |
| `ORDER BY`      | Set an optional sorting-key expression.                                  |
| `TTL`           | Delete expired rows using a date/time expression and optional condition. |
| `SETTINGS`      | Set table settings with the engine's native validation.                  |

<a id="rawtree-behavior" />

Query API behavior [#query-api-behavior]

* **Supported:** The syntax shown above.
* **Not exposed by the Query API:** Column definitions, engine arguments, `AS SELECT`, other engines, and other table clauses.
* **Query API scope:** The API creates raw tables and selects the engine and database.

`CREATE TABLE ... SETTINGS` returns `400` on databases with custom S3 storage.
Create the table without a `SETTINGS` clause. Some settings can only be set at creation.

Errors [#errors]

Error: `Unsupported CREATE TABLE statement.`

Hint: The API returns the supported form with your table name.

```text
Only CREATE TABLE [IF NOT EXISTS] <table> ENGINE = ReplicatedRawMergeTree [ORDER BY <expressions>] [TTL <expression> [DELETE [WHERE <condition>]]] [SETTINGS name = value, ...] is supported. Use: CREATE TABLE my_table ENGINE = ReplicatedRawMergeTree
```

Examples [#examples]

Create a table with an explicit sorting key.

```sql test
CREATE TABLE events ENGINE = ReplicatedRawMergeTree ORDER BY (tenant, event_time)
```

Create a table only when it does not exist.

```sql test
CREATE TABLE IF NOT EXISTS archive_events ENGINE = ReplicatedRawMergeTree
```

Row retention [#row-retention]

Set a TTL before inserting data. Use an explicit `__raw_data` path for a field
that does not exist yet. These examples use `Int64` timestamps in Unix seconds.
Extract the concrete type before converting to `DateTime`.

Missing timestamps can become zero when cast and make rows expire.
Use `DELETE WHERE` to retain rows with missing timestamps or other stored types:

```sql test
CREATE TABLE retained_events ENGINE = ReplicatedRawMergeTree
TTL toDateTime(ifNull(dynamicElement(__raw_data.ts, 'Int64'), 0)) + INTERVAL 30 DAY
DELETE WHERE dynamicElement(__raw_data.ts, 'Int64') IS NOT NULL
```

Expired rows are removed during background TTL processing. The request does not
wait for deletion. Only row-deletion TTL is supported; storage moves, recompression,
aggregation, and multiple TTL rules are not accepted.

Change retention later with [MODIFY TTL](/docs/reference/sql/statements/alter-table#row-retention).

Related [#related]

* [Raw-table concepts](/docs/concepts/raw-tables)
* [Sorting-key concepts](/docs/concepts/sorting-keys)
* [Change a sorting key](/docs/guides/operate/change-sorting-key)
