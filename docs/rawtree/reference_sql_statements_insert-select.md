# INSERT ... SELECT (/docs/reference/sql/statements/insert-select)



INSERT ... SELECT [#insert--select]

This page describes statements accepted by the Query API in RawTree Cloud
and RawTree BYOC. Its restrictions apply to the API, not to all RawTree SQL.
See [ClickHouse compatibility and API scope](/docs/reference/clickhouse-compatibility).

Syntax [#syntax]

```sql
INSERT INTO <table> [(<columns>)] SELECT ...
```

The target table must exist in the selected database. The API key needs read
and write access.

Clauses [#clauses]

| Clause      | Meaning                                      |
| ----------- | -------------------------------------------- |
| `<table>`   | Existing target table.                       |
| `<columns>` | Optional target column list.                 |
| `SELECT`    | Query that supplies rows for the insert.     |
| `SETTINGS`  | Optional settings passed to query execution. |

URL table functions are not supported in the source query. `VALUES` and
`FORMAT` inserts are not supported; use the table insert API for JSON rows.

<a id="rawtree-behavior" />

Query API behavior [#query-api-behavior]

* **Supported:** `INSERT INTO ... SELECT ...` with a table in the selected database.
* **Not exposed by the Query API:** `VALUES`, `FORMAT`, `INSERT INTO FUNCTION`, and URL table functions.
* **Query API scope:** The Query API accepts only `INSERT ... SELECT` for SQL inserts.

Errors [#errors]

Error: `Unsupported INSERT statement.`

Hint:

```text
Only INSERT INTO <table> [(columns)] SELECT ... is supported. Use the tables insert API for JSON rows.
```

URL table functions return this error.

```text
Table functions are not supported in INSERT ... SELECT.
```

Hint:

```text
Select from tables in your database.
```

Examples [#examples]

Create a target table before you insert rows.

```sql test
CREATE TABLE daily_events ENGINE = ReplicatedRawMergeTree
```

Insert aggregated results into the target.

```sql test
INSERT INTO daily_events SELECT service, count() AS event_count FROM events GROUP BY service
```

Related [#related]

* [API reference: table insert](/docs/reference/api/tables#post-v1tablestable)
* [Query data](/docs/guides/query/query-data)
