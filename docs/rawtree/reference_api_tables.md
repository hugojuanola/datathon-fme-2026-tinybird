# Tables (/docs/reference/api/tables)



Tables [#tables]

Reads require read permission. Inserts require write permission. Table creation, configuration, and deletion require admin permission.

GET `/v1/tables` [#get-v1tables]

List tables in the selected database.

Use an API key, a permitted workload token, or a user bearer token. Database-role keys support only the operations listed in [Authentication](/docs/reference/authentication#existing-database-roles).

Request:

```bash
# List all tables in a database.
curl -X GET "https://api.rawtree.com/v1/tables?database=analytics" \
  -H "Authorization: Bearer $RAWTREE_API_KEY"
```

Expected response: **HTTP 200**.

```json
{
  "tables": [
    {
      "name": "events",
      "created_at": "2026-11-09T10:00:00Z",
      "total_rows": 1,
      "total_bytes": 128
    }
  ]
}
```

Errors: `401`. See [API errors](/docs/reference/errors).

POST `/v1/tables` [#post-v1tables]

Create a table. Requires `admin` permission.

```json
{
  "name": "events",
  "sorting_key": "region, user.id",
  "settings": {
    "replacing_enable": true,
    "index_granularity": 4096
  }
}
```

`sorting_key` is optional. Omit it, or send an empty string, and the table picks a
sorting key per part from the ingested data. The string contains SQL expressions
in key order, separated by commas. A bare name such as `user.id` is read as a path
into the ingested JSON.

`ttl` is an optional row-deletion TTL expression:

```json
{"ttl": "toDateTime(ifNull(dynamicElement(__raw_data.ts, 'Int64'), 0)) + INTERVAL 30 DAY DELETE WHERE dynamicElement(__raw_data.ts, 'Int64') IS NOT NULL"}
```

Use an explicit `__raw_data` path to configure TTL before the field exists.
These examples use `Int64` timestamps in Unix seconds.
Extract the concrete type before converting to `DateTime`. The condition retains rows with missing timestamps or other stored types.
Without this condition, missing timestamps can become zero when cast and make rows expire.
Only one row-deletion rule is accepted. Expiration runs in the background.

`settings` is an optional object of engine setting names and JSON boolean, number,
or string values. Strings are literal values, not SQL expressions. The engine
validates setting names and values. Omitting `settings` or sending `{}` preserves
the default creation behavior. Nonempty settings on a database with custom S3
return HTTP 400: `Custom settings are not supported for custom S3.`

Use an API key, a permitted workload token, or a user bearer token. Database-role keys support only the operations listed in [Authentication](/docs/reference/authentication#existing-database-roles).

Parameters:

| Field         | Location | Type           | Required | Notes                                                                                                                                            |
| ------------- | -------- | -------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `name`        | body     | string         | Yes      | Table name in the selected database. The table uses the database's customer-owned S3 storage when configured, then the cluster default.          |
| `ttl`         | body     | string or null | No       | Row-deletion TTL expression, optionally followed by `DELETE WHERE <condition>`.                                                                  |
| `sorting_key` | body     | string or null | No       | Optional comma-separated SQL sorting expressions. Omit it, or send an empty string, to let the table pick a key per part from the ingested data. |

Request:

```bash
# Create a table in the selected database.
curl -X POST "https://api.rawtree.com/v1/tables?database=analytics" \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "events"
}'
```

Expected response: **HTTP 201**.

```json
{
  "database": "analytics",
  "table": "events",
  "storage": {
    "type": "default"
  },
  "sorting_key": ""
}
```

Errors: `400`, `401`, `403`, `409`. See [API errors](/docs/reference/errors).

GET `/v1/tables/{table}` [#get-v1tablestable]

Describe a table. The response includes `sorting_key`, which is empty when the
table picks a key per part. `table.settings` lists every explicitly configured
setting, including settings supplied by the platform. Each entry has a `name`
and a `value` in SQL syntax, with secrets masked by the engine:

```json
{"name": "index_granularity", "value": "4096"}
```

Create and update responses also include this `settings` list.
All three responses include `ttl`, containing the stored SQL expression or `null` when no TTL exists. Unset engine
defaults are not included, and the list does not identify who set each value.

Use an API key, a permitted workload token, or a user bearer token. Database-role keys support only the operations listed in [Authentication](/docs/reference/authentication#existing-database-roles).

Request:

```bash
# Describe columns of a table.
curl -X GET "https://api.rawtree.com/v1/tables/events?database=analytics" \
  -H "Authorization: Bearer $RAWTREE_API_KEY"
```

Expected response: **HTTP 200**.

```json
{
  "table": {
    "name": "events",
    "created_at": "2026-11-09T10:00:00Z",
    "total_rows": 1,
    "total_bytes": 128,
    "columns": [
      {
        "name": "__raw_data",
        "type": "JSON"
      }
    ],
    "sorting_key": ""
  }
}
```

Errors: `400`, `401`. See [API errors](/docs/reference/errors).

PATCH `/v1/tables/{table}` [#patch-v1tablestable]

Update a table's RawTree configuration. Requires `admin` permission. Only the
fields you send are changed; omitted fields are left as they are.

```json
{ "sorting_key": "timestamp" }
```

Functions and multiple expressions use the same string field. Commas inside
function arguments remain part of that function:

```json
{ "sorting_key": "ifNull(cityHash64(host, instanceId), 0)" }
```

To change table settings, send a nonempty `settings` object with the same value
types accepted by POST:

```json
{ "settings": { "max_parts_in_total": 100000 } }
```

To set or replace retention, send the same `ttl` expression accepted by POST.
The new rule applies to existing and future rows. Omitted or `null` TTL values
leave retention unchanged; an empty string is invalid.

Send sorting-key, TTL, and settings changes in separate PATCH requests. Set the
sorting key first when enabling replacement. Omitted settings retain their values;
`null` is not a reset operation. Use Query API `ALTER TABLE ... RESET SETTING ...`
to restore engine defaults. The engine decides which settings can be changed and
which setting combinations are valid.

Bare column names inside functions resolve to fields in the ingested JSON.
Use SQL identifier quotes for unusual column names, such as `` `user-agent` ``.
Create, update, and describe responses return `sorting_key` as a string; an empty
string indicates automatic sorting.

The new sorting key applies to newly inserted parts and wins later merges, so
existing parts are re-sorted in the background rather than rewritten by the
request. The key must contain at least one column or expression; a sorting key
cannot be removed once set. The service checks expression syntax before sending the
key to the engine. An unusable key, such as one that repeats a column, is
answered with the engine's own error.

Use an API key, a permitted workload token, or a user bearer token. Database-role keys support only the operations listed in [Authentication](/docs/reference/authentication#existing-database-roles).

Parameters:

| Field         | Location | Type           | Required | Notes                                                                           |
| ------------- | -------- | -------------- | -------- | ------------------------------------------------------------------------------- |
| `ttl`         | body     | string or null | No       | Row-deletion TTL expression, optionally followed by `DELETE WHERE <condition>`. |
| `sorting_key` | body     | string or null | No       | Comma-separated SQL expressions for the custom sorting key.                     |

Request:

```bash
# Update a table's ClickHouse configuration.
curl -X PATCH "https://api.rawtree.com/v1/tables/events?database=analytics" \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "sorting_key": "region, user.id"
}'
```

Expected response: **HTTP 200**.

```json
{
  "database": "analytics",
  "table": "events",
  "sorting_key": "region, user.id"
}
```

Errors: `400`, `401`, `403`. See [API errors](/docs/reference/errors).

POST `/v1/tables/{table}` [#post-v1tablestable]

Insert data. Send one JSON object or an array of JSON objects.

```json
[{ "action": "click", "user": "alice" }]
```

Successful JSON body inserts without a transform return the database's native
summary fields at the top level. Counters retain their string representation:

```json
{
  "read_rows": "3",
  "read_bytes": "73",
  "written_rows": "3",
  "written_bytes": "73",
  "total_rows_to_read": "0",
  "result_rows": "3",
  "result_bytes": "73",
  "elapsed_ns": "74267625",
  "memory_usage": "1091943"
}
```

This example shows the native fields from a three-object insert; timing, memory,
and byte counts depend on the request.

| Field                | Meaning                                                                                          |
| -------------------- | ------------------------------------------------------------------------------------------------ |
| `read_rows`          | Rows processed from the input.                                                                   |
| `read_bytes`         | Input-processing byte count reported by the database.                                            |
| `written_rows`       | Reported insert row count. Deduplicated requests can report rows without adding new stored rows. |
| `written_bytes`      | Reported insert byte count, not compressed storage size.                                         |
| `total_rows_to_read` | Estimated total input rows; zero can mean no estimate is available.                              |
| `result_rows`        | Execution-result row count; for ordinary inserts this reflects insert progress.                  |
| `result_bytes`       | Execution-result byte count.                                                                     |
| `elapsed_ns`         | Database-reported elapsed time in nanoseconds.                                                   |
| `memory_usage`       | Database-reported query memory in bytes, not total server or API-backend memory.                 |

The response also retains `inserted` for compatibility: it is the numeric value
of `written_rows`, or `null` when that count is unavailable. New clients should
use `written_rows`. Summary fields are forwarded when the database provides a
valid summary.

Without a transform, the API forwards the body unchanged using `JSONAsObject`.
The database handles JSON validation, empty inputs, and insert errors. An error
does not add an API-level rollback guarantee: any rows already written follow
the database's insert behavior. A missing table can be auto-created even when
the payload is empty or the database subsequently rejects it.

Optional transform for JSON body inserts:

```text
POST /v1/tables/traces?transform=otlp-traces
```

Transforms flatten known source formats before insert.

See [Transforms](/docs/guides/transforms) for supported input shapes and emitted rows.

Supported transforms:

* `otlp-traces`
* `otlp-logs`
* `otlp-metrics`
* `cloudwatch-logs`
* `cloudtrail`
* `firehose`

For AWS Firehose HTTP endpoint delivery, use:

```text
POST /v1/tables/events?transform=firehose
X-Amz-Firehose-Access-Key: <rawtree-api-key>
```

Firehose records must contain base64-encoded data in `records[].data`. If the decoded value is a JSON object, the service inserts it as one row. If it is an array of JSON objects, the service inserts one row per object. If it is UTF-8 TSV text and `columns` is present, the service inserts one row per TSV line using those column names. If it is UTF-8 TSV text without `columns`, the service inserts one row with the decoded text in `data`. Other decoded formats return `400`. Successful Firehose inserts return `{requestId,timestamp}`.

URL ingest uses query parameters:

```text
POST /v1/tables/events?url=https%3A%2F%2Fexample.com%2Fevents.jsonl
```

The request stays open until the native RawTree URL import finishes. Success returns
`200` with JSON such as `{"inserted":1000}`; `inserted` is
`null` if RawTree does not provide a row count. Errors return a normal HTTP error
response. There is no progress event stream.

Optionally pass `query_id` with a URL import to correlate it with RawTree query
logs. If omitted, RawTree generates the ID. In both cases, the ID is returned in
the `X-ClickHouse-Query-Id` response header, matching the query API. It is not added
to the JSON body.

Transforms are not supported with URL inserts. If you use `?url=`, transform the data before hosting it.

Use an API key, a permitted workload token, or a user bearer token. Database-role keys support only the operations listed in [Authentication](/docs/reference/authentication#existing-database-roles).

Parameters:

| Field                        | Location | Type   | Required | Notes                                                                             |
| ---------------------------- | -------- | ------ | -------- | --------------------------------------------------------------------------------- |
| `url`                        | query    | string | No       | Optional source URL. Mutually exclusive with request body.                        |
| `query_id`                   | query    | string | No       | Optional query ID for correlating a URL import with ClickHouse query logs.        |
| `columns`                    | query    | string | No       | Optional comma-separated column names for TSV data when using transform=firehose. |
| `deduplicate_insert`         | query    | string | No       | Optional ClickHouse insert deduplication setting: enable or disable.              |
| `insert_deduplication_token` | query    | string | No       | Optional custom ClickHouse insert deduplication token.                            |

Request:

```bash
# Insert data into a table (auto-creates table if needed). URL imports wait for completion and return JSON.
curl -X POST "https://api.rawtree.com/v1/tables/events?database=analytics" \
  -H "Authorization: Bearer $RAWTREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "action": "page_view",
  "region": "eu",
  "user": {
    "id": 42
  }
}'
```

Expected response: **HTTP 200**.

```json
{
  "read_rows": "0",
  "read_bytes": "0",
  "written_rows": "1",
  "written_bytes": "57",
  "total_rows_to_read": "0",
  "result_rows": "0",
  "result_bytes": "0",
  "elapsed_ns": "1000000"
}
```

Errors: `400`, `401`, `413`, `429`. See [API errors](/docs/reference/errors).

DELETE `/v1/tables/{table}` [#delete-v1tablestable]

Delete a table. Requires `admin` permission.

Use an API key, a permitted workload token, or a user bearer token. Database-role keys support only the operations listed in [Authentication](/docs/reference/authentication#existing-database-roles).

Request:

```bash
# Delete a table.
curl -X DELETE "https://api.rawtree.com/v1/tables/events?database=analytics" \
  -H "Authorization: Bearer $RAWTREE_API_KEY"
```

Expected response: **HTTP 200**.

```json
{
  "deleted": true
}
```

Errors: `400`, `401`, `403`. See [API errors](/docs/reference/errors).
