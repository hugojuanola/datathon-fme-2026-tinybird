# ClickHouse compatibility (/docs/reference/clickhouse-compatibility)



<a id="compared-with-clickhouse" />

ClickHouse compatibility [#clickhouse-compatibility]

RawTree is a database forked from ClickHouse. It shares SQL execution and
constructs such as users, roles, grants, row policies, settings profiles,
workloads, and resources. Its raw tables and adaptive behavior add or change
parts of that model. A fork does not imply complete compatibility with every
upstream version, engine, setting, or deployment.

Database capabilities and differences [#database-capabilities-and-differences]

| Area                     | RawTree behavior                                                                                                                                                                                |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SQL and database objects | SQL defines reads, writes, access controls, and workload scheduling.                                                                                                                            |
| Raw tables               | Undeclared JSON fields live in `__raw_data` and appear as logical columns.                                                                                                                      |
| Dynamic fields           | Stored types can vary by row. Conversions and exact type extraction have different semantics.                                                                                                   |
| Physical optimization    | Raw tables can use automatic sorting keys and optional automatic projections.                                                                                                                   |
| Inspection               | System tables, statistics, and `EXPLAIN` expose database behavior. Query hints report [runtime type-compatibility warnings](/docs/concepts/dynamic-fields#runtime-type-compatibility-warnings). |

See [Raw tables](/docs/concepts/raw-tables),
[Dynamic fields](/docs/concepts/dynamic-fields), and
[Adaptive optimization](/docs/concepts/adaptive-optimization) for these differences.
Generated reference pages describe the engine binary used for this build.
Configuration and the table engine still determine which features apply.

Service interfaces [#service-interfaces]

RawTree Cloud and RawTree BYOC expose the database through service APIs.
The Query API validates supported statement forms before sending SQL to RawTree.
Its restrictions are not a complete description of database capabilities.

For example, RawTree supports SQL users. The service creates a database user
for a database-role API key, but the public Query API rejects `CREATE USER`.
API key lifecycle belongs to the service, while the database enforces grants.

<a id="compatibility" />

Query API statement support [#query-api-statement-support]

The following table applies to `POST /v1/query` in this service version.
**Not exposed** means that this API rejects the statement. It does not mean
that RawTree lacks the corresponding database capability.
Supported entries still have syntax and permission limits in the
[statement reference](/docs/reference/sql/statements).

| Statement or feature                                                   | Query API status                |
| ---------------------------------------------------------------------- | ------------------------------- |
| `SELECT`, `WITH`, `EXPLAIN`, `DESCRIBE`                                | Supported                       |
| `CREATE ROLE`, `DROP ROLE`, selected `GRANT` forms                     | Supported                       |
| `CREATE ROW POLICY`, `DROP ROW POLICY`                                 | Supported                       |
| `CREATE SETTINGS PROFILE`, `DROP SETTINGS PROFILE`                     | Supported                       |
| `CREATE WORKLOAD`, `DROP WORKLOAD`, `CREATE RESOURCE`, `DROP RESOURCE` | Supported                       |
| `CREATE NAMED COLLECTION`                                              | Supported                       |
| `CREATE USER`                                                          | Not exposed                     |
| `CREATE TABLE` with `ReplicatedRawMergeTree`                           | Supported                       |
| `INSERT INTO ... SELECT`                                               | Supported                       |
| `ALTER TABLE ... MODIFY ORDER BY`                                      | Supported                       |
| `ALTER TABLE ... MODIFY SETTING` and `RESET SETTING`                   | Supported                       |
| Projection `ADD`, `MATERIALIZE`, `CLEAR`, and `DROP`                   | Supported                       |
| Index `ADD`, `MATERIALIZE`, `CLEAR`, and `DROP`                        | Supported                       |
| `ALTER` and `DROP NAMED COLLECTION`                                    | Not exposed                     |
| `KILL MUTATION`                                                        | Supported                       |
| `CREATE MATERIALIZED VIEW`                                             | Not exposed                     |
| `CREATE VIEW`                                                          | Not exposed                     |
| `CREATE DICTIONARY`                                                    | Not exposed                     |
| Row-deletion `TTL` and `ALTER TABLE ... MODIFY TTL`                    | Supported                       |
| `ALTER ROW POLICY`                                                     | Not exposed                     |
| `ALTER ROLE`                                                           | Not exposed                     |
| `REVOKE`                                                               | Not exposed                     |
| `SET ROLE`                                                             | Not exposed                     |
| Lightweight `DELETE`                                                   | Not exposed                     |
| `ALTER TABLE ... DELETE`/`UPDATE` mutations                            | Not exposed                     |
| `UPDATE`                                                               | Not exposed                     |
| `OPTIMIZE`                                                             | Not exposed                     |
| `TRUNCATE TABLE [IF EXISTS] <table> [SYNC]`                            | Supported with write permission |
| `RENAME`                                                               | Not exposed                     |
| `ALTER SETTINGS PROFILE`                                               | Not exposed                     |
| `INSERT ... VALUES`                                                    | Not exposed                     |
| `INSERT ... FORMAT`                                                    | Not exposed                     |
| `INSERT INTO FUNCTION`                                                 | Not exposed                     |
| URL table functions in `INSERT ... SELECT`                             | Not exposed                     |

<a id="verified-rejections" />

Verified Query API rejections [#verified-query-api-rejections]

These examples test the service interface. They do not test direct database
execution and must not be used as an engine compatibility test.

Create a materialized view.

```sql test expect-error="Unsupported query."
CREATE MATERIALIZED VIEW daily_view ENGINE = ReplicatedRawMergeTree AS SELECT 1
```

Create a view.

```sql test expect-error="Unsupported query."
CREATE VIEW daily_view AS SELECT 1
```

Create a dictionary.

```sql test expect-error="Unsupported query."
CREATE DICTIONARY daily_dictionary (id UInt64) PRIMARY KEY id SOURCE(CLICKHOUSE(TABLE 'events')) LAYOUT(FLAT()) LIFETIME(0)
```

Create a table with a TTL clause.

```sql test
CREATE TABLE ttl_events ENGINE = ReplicatedRawMergeTree
TTL toDateTime(ifNull(dynamicElement(__raw_data.event_time, 'Int64'), 0)) + INTERVAL 1 DAY
DELETE WHERE dynamicElement(__raw_data.event_time, 'Int64') IS NOT NULL
```

Alter a row policy.

```sql test expect-error="Unsupported ALTER statement."
ALTER ROW POLICY acme_statement_only ON events USING 1
```

Alter a role.

```sql test expect-error="Unsupported ALTER statement."
ALTER ROLE events_statement_reader
```

Revoke a grant.

```sql test expect-error="Unsupported query."
REVOKE SELECT ON analytics.events FROM events_statement_reader
```

Set the active role.

```sql test expect-error="Unsupported query."
SET ROLE events_statement_reader
```

Use lightweight delete syntax.

```sql test expect-error="Unsupported query."
DELETE FROM events WHERE event_time < 1
```

Use an `ALTER TABLE` delete mutation.

```sql test expect-error="Unsupported ALTER statement."
ALTER TABLE events DELETE WHERE event_time < 1
```

Update a table row.

```sql test expect-error="Unsupported query."
UPDATE events SET event_time = 1 WHERE tenant = 'north'
```

Optimize a table.

```sql test expect-error="Unsupported query."
OPTIMIZE TABLE events
```

Truncate a table.

```sql test
TRUNCATE TABLE events
```

Rename a table.

```sql test expect-error="Unsupported query."
RENAME TABLE events TO archived_events
```

Alter a settings profile.

```sql test expect-error="Unsupported ALTER statement."
ALTER SETTINGS PROFILE profile_statement_profile SETTINGS workload = 'default'
```

Insert literal values.

```sql test expect-error="Unsupported INSERT statement."
INSERT INTO events VALUES (1)
```

Insert rows in a format.

```sql test expect-error="Unsupported INSERT statement."
INSERT INTO events FORMAT JSONEachRow
```

Insert into a table function.

```sql test expect-error="Unsupported INSERT statement."
INSERT INTO FUNCTION file('events.csv') SELECT 1
```

Read an external table function during an insert.

```sql test expect-error="Table functions are not supported in INSERT ... SELECT."
INSERT INTO events SELECT * FROM url('https://example.com/events.csv', 'CSV')
```

Related [#related]

* [SQL statements](/docs/reference/sql/statements)
* [Query API](/docs/reference/api/query#post-v1query)
* [Query best practices](/docs/guides/query/optimize-queries#query-best-practices)
