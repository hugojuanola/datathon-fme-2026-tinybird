# Raw tables (/docs/concepts/raw-tables)



Raw tables [#raw-tables]

Raw tables accept JSON rows before you define a schema. RawTree stores each
row's undeclared fields in the internal `__raw_data` JSON column.

Physical columns and JSON paths [#physical-columns-and-json-paths]

Declared physical columns can exist beside paths in `__raw_data`. A physical
column takes precedence when its name matches a JSON path.

RawTree exposes known JSON leaf paths as logical SQL columns. Query those paths
by name, such as `user.id`, without reading the parent JSON value.

Use `__raw_data.path` when you need the JSON value at a path. Use `__raw_data`
only when you need the complete parsed JSON object.

`SELECT *` expansion [#select--expansion]

`SELECT *` returns declared columns and known JSON leaf paths. It does not
return the parent `__raw_data` column.

The set of known paths can change as rows arrive. Select named paths in
reusable queries to keep the result shape stable.

```sql test
SELECT event, user.id FROM events LIMIT 10
```

Missing and unknown paths [#missing-and-unknown-paths]

A known path that is absent from one row returns `NULL`. A path that does not
exist in the table schema returns an `UNKNOWN_IDENTIFIER` exception.

Inspect the table or query known fields before you use a new path. The
[`is_raw` setting](/docs/reference/sql/settings/merge-tree#is_raw) marks a raw
table. The `system.tables.is_raw` value identifies a raw table.

Related [#related]

* [Dynamic fields](/docs/concepts/dynamic-fields)
* [Query data](/docs/guides/query/query-data)
* [Optimize queries](/docs/guides/query/optimize-queries)
* [Ingestion model](/docs/concepts/ingestion-model)
* [Storage and compute](/docs/concepts/storage-and-compute)
