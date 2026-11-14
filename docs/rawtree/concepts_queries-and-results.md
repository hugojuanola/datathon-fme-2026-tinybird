# Queries and results (/docs/concepts/queries-and-results)



Queries and results [#queries-and-results]

A query expresses the data you want through SQL. RawTree evaluates it against
the tables your credential can access. The returned rows are only one part of
the outcome: types, statistics, hints, and errors explain what the engine did.

Database scope and permissions [#database-scope-and-permissions]

Each Query API request selects a database within a cluster. An API key can supply a
default database when the request omits one. That default resolves unqualified
table names. It does not restrict the key to that database.

Permissions remain separate from name resolution. A permission-based key has
cluster-wide access at its permission level. Database-role credentials use
their grants to determine accessible databases, tables, and columns. See
[Access control](/docs/concepts/access-control).

Reads and supported changes [#reads-and-supported-changes]

RawTree supports SQL for reads, writes, and database administration.
RawTree Cloud and RawTree BYOC expose a narrower interface through the Query API.
An API rejection describes that interface, not the database's complete SQL support.
See [ClickHouse compatibility and API scope](/docs/reference/clickhouse-compatibility).

The Query API accepts one statement per request. Read operations include
`SELECT`, `WITH`, `EXPLAIN`, and `DESCRIBE`.

The same endpoint also accepts a restricted set of writes and management
statements. Examples include `INSERT INTO ... SELECT`, table creation,
projection operations, and role management. Each operation has its own
permission and validation rules.

A statement that starts with `SELECT` is not necessarily read-only:
`CACHE INTO` creates a stored cache destination and requires write
management permission. The endpoint is not an unrestricted database console.
See the [SQL reference](/docs/reference/sql) and
[Query API](/docs/reference/api/query#post-v1query) for supported forms.

Read the whole result [#read-the-whole-result]

The default JSON response separates the data from execution information.

| Field        | Meaning                                                                                 |
| ------------ | --------------------------------------------------------------------------------------- |
| `meta`       | Names and types of the result columns.                                                  |
| `data`       | Returned rows.                                                                          |
| `rows`       | Number of returned rows.                                                                |
| `statistics` | Execution time, rows read, and bytes read. Insert queries can also report rows written. |
| `hints`      | Optional runtime type-compatibility warnings about incompatible `Dynamic` values.       |

A small result can require a large scan. `LIMIT` bounds the result rows, but
an aggregate or sort can still read substantial data before producing them.
Statistics help distinguish result size from work done.

Successful execution and intended meaning [#successful-execution-and-intended-meaning]

A successful query can substitute `NULL` or default results for incompatible
values, or exclude them from an aggregate. Its `hints` field can report these
cases as runtime type-compatibility warnings.

A warning does not always mean that a result row was removed.
Some operations can skip incompatible values without a warning.
See [Runtime type-compatibility warnings](/docs/concepts/dynamic-fields#runtime-type-compatibility-warnings)
for the behavior of scalar functions, comparisons, and aggregates.

The query's intended type determines whether to convert values, select one
stored type, or count incompatible values separately. Comparisons, grouping,
ordering, and joins all depend on that choice. See
[Dynamic fields](/docs/concepts/dynamic-fields).

SQL result order requires an explicit `ORDER BY`. A table's sorting key does
not guarantee the order of returned rows.

Limits, streaming, and cancellation [#limits-streaming-and-cancellation]

Execution-time, result-size, and request-rate limits bound query work. The
[Limits reference](/docs/reference/limits) describes the limits exposed by the
service. Query settings and permitted overrides depend on the operation.

Other output formats return their native bodies instead of the default JSON
envelope. Streaming results can begin before execution finishes. An HTTP `200`
at the start of a stream does not establish success: an exception or broken
connection can leave an incomplete result.

A supplied `query_id` identifies an execution for cancellation and correlation.
Closing the client connection does not confirm cancellation on the server.
Cancellation has its own result and permission checks. Cancelling a write does
not undo rows already written.

Observe before optimizing [#observe-before-optimizing]

`EXPLAIN` describes the query plan. Execution statistics show its actual work.
Query history and request logs help connect a request with its outcome.
Compare the same data range when assessing a change, since new data and caches
can change the result of a measurement.

[Adaptive optimization](/docs/concepts/adaptive-optimization) can improve
repeated workloads, but it does not choose the business meaning of mixed data.

Related [#related]

* [Query data](/docs/guides/query/query-data)
* [Optimize queries](/docs/guides/query/optimize-queries)
* [Errors](/docs/reference/errors)
