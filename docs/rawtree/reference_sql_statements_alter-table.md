# ALTER TABLE (/docs/reference/sql/statements/alter-table)



ALTER TABLE [#alter-table]

This page describes statements accepted by the Query API in RawTree Cloud
and RawTree BYOC. Its restrictions apply to the API, not to all RawTree SQL.
See [ClickHouse compatibility and API scope](/docs/reference/clickhouse-compatibility).

Syntax [#syntax]

```sql
ALTER TABLE <table> MODIFY ORDER BY <expressions>
ALTER TABLE <table> MODIFY TTL <expression> [DELETE [WHERE <condition>]]
ALTER TABLE <table> MODIFY SETTING <name> = <value> [, ...]
ALTER TABLE <table> RESET SETTING <name> [, ...]
ALTER TABLE <table> ADD PROJECTION [IF NOT EXISTS] <name> (SELECT ...)
ALTER TABLE <table> MATERIALIZE PROJECTION [IF EXISTS] <name>
ALTER TABLE <table> CLEAR PROJECTION [IF EXISTS] <name>
ALTER TABLE <table> DROP PROJECTION [IF EXISTS] <name>
ALTER TABLE <table> ADD INDEX [IF NOT EXISTS] <name> <expression> TYPE <type> [GRANULARITY <n>]
ALTER TABLE <table> MATERIALIZE INDEX [IF EXISTS] <name>
ALTER TABLE <table> CLEAR INDEX [IF EXISTS] <name>
ALTER TABLE <table> DROP INDEX [IF EXISTS] <name>
```

Clauses [#clauses]

| Clause                   | Meaning                                                    |
| ------------------------ | ---------------------------------------------------------- |
| `MODIFY ORDER BY`        | Set the table sorting-key expression.                      |
| `MODIFY TTL`             | Set or replace the row-deletion TTL.                       |
| `MODIFY SETTING`         | Change table settings with the engine's native validation. |
| `RESET SETTING`          | Restore engine defaults for the named table settings.      |
| `ADD PROJECTION`         | Add a projection definition.                               |
| `MATERIALIZE PROJECTION` | Build the projection for existing parts.                   |
| `CLEAR PROJECTION`       | Remove stored projection data and keep its definition.     |
| `DROP PROJECTION`        | Remove a projection definition.                            |
| `ADD INDEX`              | Add a data-skipping index definition.                      |
| `MATERIALIZE INDEX`      | Build the index for existing parts.                        |
| `CLEAR INDEX`            | Remove stored index data and keep its definition.          |
| `DROP INDEX`             | Remove an index definition.                                |

Submit one operation per statement. The target table must be in the selected
database. `ALTER` requires admin permission or a signed-in session.

<a id="rawtree-behavior" />

Query API behavior [#query-api-behavior]

* **Supported:** The sorting-key, TTL, table-setting, projection, and index operations in the syntax section.
* **Not exposed by the Query API:** Other `ALTER` operations, `AFTER`, `ON CLUSTER`, and `IN PARTITION`.
* **Query API scope:** This API accepts one table operation per request.

Errors [#errors]

Error: `Unsupported ALTER statement.`

Hint:

```text
Supported statements include ALTER TABLE <table> MODIFY ORDER BY <expressions>, MODIFY SETTING or RESET SETTING, projection operations, and ADD, MATERIALIZE, CLEAR, or DROP INDEX, one operation per statement.
```

| Error                           | Meaning                                                                                     | Action                                       |
| ------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Not finished mutation (code 36) | `CLEAR INDEX` or `DROP INDEX` targets an index while its `MATERIALIZE INDEX` mutation runs. | Wait for the mutation to finish, then retry. |

Examples [#examples]

Change a table sorting key.

```sql test
ALTER TABLE events MODIFY ORDER BY (tenant, event_time)
```

Add one projection.

```sql test
ALTER TABLE events ADD PROJECTION by_tenant (SELECT `__raw_data.tenant`, count() GROUP BY `__raw_data.tenant`)
```

Materialize the projection for existing parts.

```sql test
ALTER TABLE events MATERIALIZE PROJECTION by_tenant
```

After materialization completes, run `ALTER TABLE events CLEAR PROJECTION by_tenant`
to remove its stored data and keep its definition. Run
`ALTER TABLE events DROP PROJECTION by_tenant` to remove the definition.

Row retention [#row-retention]

Set or replace a table's TTL after creation:

```sql test
ALTER TABLE events MODIFY TTL
  toDateTime(ifNull(dynamicElement(__raw_data.event_time, 'Int64'), 0)) + INTERVAL 30 DAY
  DELETE WHERE dynamicElement(__raw_data.event_time, 'Int64') IS NOT NULL
```

The new rule applies to existing and future rows. Deletion runs in the background.
The condition retains rows with missing timestamps or other stored types.
Omit it only if those rows should expire too.
Extract a concrete type from Dynamic values before converting to a date/time type. Only one row-deletion rule is accepted.

Indexes [#indexes]

Add an index with `ADD INDEX`. The expression can use a nested storage path.
Use a cast when the index type requires a concrete type.

```sql test
ALTER TABLE docs_index_examples ADD INDEX IF NOT EXISTS idx_text lower(__raw_data.commit.record.text::String) TYPE text(tokenizer = splitByNonAlpha)
```

Build an index for existing parts with `MATERIALIZE INDEX`. The operation runs
in the background.

```sql test
ALTER TABLE docs_index_examples MATERIALIZE INDEX IF EXISTS idx_text
```

Wait for the `MATERIALIZE INDEX` mutation to finish before you clear or drop
the index. If the mutation is not finished, RawTree returns error code 36.

Check progress with `system.mutations`.

```sql test
SELECT mutation_id, is_done
FROM system.mutations
WHERE database = currentDatabase()
  AND table = 'docs_index_examples'
  AND is_done = 0
```

Poll until the query returns no rows.

```bash test
deadline=$((SECONDS + 60))
while (( SECONDS < deadline )); do
  pending="$(curl --silent --show-error -X POST \
    "https://api.rawtree.com/v1/query?database=$DATABASE" \
    --header "Authorization: Bearer $RAWTREE_API_KEY" \
    --header "Content-Type: application/json" \
    -d "$(jq -n --arg sql "SELECT mutation_id, is_done FROM system.mutations WHERE database = currentDatabase() AND table = 'docs_index_examples' AND is_done = 0" '{sql: $sql}')")"
  if jq -e '(.data | type) == "array" and (.data | length) == 0' <<<"$pending" >/dev/null; then
    printf 'No pending index mutations.\n'
    exit 0
  fi
  sleep 1
done
echo "Timed out waiting for index materialization." >&2
exit 1
```

Use `CLEAR INDEX` to remove stored index data without removing its definition.
Use `DROP INDEX` to remove the definition.

```sql test
ALTER TABLE docs_index_examples CLEAR INDEX IF EXISTS idx_text
```

Wait for any clear mutation to finish before you drop the index.

```bash test
deadline=$((SECONDS + 60))
while (( SECONDS < deadline )); do
  pending="$(curl --silent --show-error -X POST \
    "https://api.rawtree.com/v1/query?database=$DATABASE" \
    --header "Authorization: Bearer $RAWTREE_API_KEY" \
    --header "Content-Type: application/json" \
    -d "$(jq -n --arg sql "SELECT mutation_id, is_done FROM system.mutations WHERE database = currentDatabase() AND table = 'docs_index_examples' AND is_done = 0" '{sql: $sql}')")"
  if jq -e '(.data | type) == "array" and (.data | length) == 0' <<<"$pending" >/dev/null; then
    printf 'No pending index mutations.\n'
    exit 0
  fi
  sleep 1
done
echo "Timed out waiting for index clear." >&2
exit 1
```

```sql test
ALTER TABLE docs_index_examples DROP INDEX IF EXISTS idx_text
```

`GRANULARITY` must be a positive integer. `AFTER` is not supported.
Track materialization and clear operations in `system.mutations`.
Inspect index definitions in `system.data_skipping_indices`.
Use table-scoped `KILL MUTATION` syntax to stop a running operation.

Related [#related]

* [Sorting-key concepts](/docs/concepts/sorting-keys)
* [Projection concepts](/docs/concepts/projections)
* [Change a sorting key](/docs/guides/operate/change-sorting-key)
* [Use projections](/docs/guides/operate/projections)
