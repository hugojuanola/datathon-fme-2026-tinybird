# Query data (/docs/guides/query/query-data)



Query data [#query-data]

This guide uses read queries through the RawTree Cloud or RawTree BYOC Query API.
RawTree also supports SQL for writes and administration. The API exposes
[selected statement forms](/docs/reference/sql/statements), each with its own limits.

RawTree uses SQL for analytics over ingested unstructured data.

Start with a small query [#start-with-a-small-query]

```bash
rtree query "SELECT * FROM events LIMIT 10"
```

Use `LIMIT` while exploring a table.

Aggregate events [#aggregate-events]

```bash
rtree query "
  SELECT action, count() AS total
  FROM events
  GROUP BY action
  ORDER BY total DESC
  LIMIT 10
"
```

Query nested fields [#query-nested-fields]

Use dot notation for nested fields.

```bash
rtree query "
  SELECT user.id, count() AS total
  FROM events
  GROUP BY user.id
  ORDER BY total DESC
  LIMIT 10
"
```

Read original rows [#read-original-rows]

RawTree stores the original JSON object for each inserted row in the virtual `__raw_data` column. Query it when you need to debug ingestion, check inferred fields, or recover the source payload.

```sql test
SELECT __raw_data FROM events LIMIT 10;
```

You can also use dot notation on `__raw_data` to inspect fields inside the original object.

```sql test
SELECT __raw_data.user.id, __raw_data.event FROM events LIMIT 10;
```

Return machine-readable output [#return-machine-readable-output]

```bash
rtree query --json "SELECT action, count() AS total FROM events GROUP BY action LIMIT 10"
```

The API response includes column metadata, rows, statistics, and optional `hints`.
Query hints are [runtime type-compatibility warnings](/docs/concepts/dynamic-fields#runtime-type-compatibility-warnings).
Inspect them even when the query succeeds.

API query [#api-query]

```bash test
curl -X POST "https://api.rawtree.com/v1/query" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT * FROM events LIMIT 10"}'
```

Build an endpoint from a query [#build-an-endpoint-from-a-query]

Query API requests accept `{"sql":"..."}`. If your application exposes an analytical endpoint, build the final SQL in your application code, then send it in the `sql` field.

This example returns daily action counts for a time window. There is no caller-provided `LIMIT`; the endpoint is bounded by the time window and grouped output.

```ts
const RAWTREE_API_URL = "https://api.rawtree.com";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const start = url.searchParams.get("start");
  const end = url.searchParams.get("end");

  if (!start || !end) {
    return Response.json(
      { error: "start and end query parameters are required" },
      { status: 400 }
    );
  }

  const sql = `
    SELECT
      toDate(event_time) AS day,
      action,
      count() AS events,
      uniq(user) AS users
    FROM events
    WHERE event_time >= toDateTime('${start}')
      AND event_time < toDateTime('${end}')
    GROUP BY day, action
    ORDER BY day ASC, events DESC
  `;

  const response = await fetch(`${RAWTREE_API_URL}/v1/query`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.RAWTREE_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ sql }),
  });

  return Response.json(await response.json(), { status: response.status });
}
```

This assumes `start` and `end` arrive in the expected datetime format. For user-controlled dimensions, prefer allowlists before putting values into SQL.

Query rules [#query-rules]

* Send query requests as `{"sql":"SELECT ..."}`.
* The Query API accepts reads and selected write and management statements.
  These include table changes, inserts from queries, roles, policies, and workloads.
  See [SQL statements](/docs/reference/sql/statements) for supported forms.
* Use dot notation for nested fields, for example `user.id`.
* Use `__raw_data` when you need the original inserted JSON object.
* Treat parameterization as application code: build the final SQL string before sending it.
* Use casts when data needs a specific type, for example `value::Float64`, `toString(user)`, or `CAST(id AS UInt64)`.
* Add `LIMIT` while exploring raw rows. Aggregated endpoints can be bounded by time windows and grouping instead.
* Inspect logs when a query fails. API errors include a `message` and a singular
  `hint` with guidance for the failed request. See [Errors](/docs/reference/errors).

See [SQL reference](/docs/reference/sql) for syntax, functions, aggregate functions, and data types.
