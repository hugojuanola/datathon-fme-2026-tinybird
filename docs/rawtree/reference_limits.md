# Limits (/docs/reference/limits)



Limits [#limits]

These limits describe service interfaces in RawTree Cloud and RawTree BYOC.
RawTree database settings also control query execution and results.

Query and insert limits [#query-and-insert-limits]

| Request or setting                     | Default                                               | Result when exceeded                                                                 |
| -------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Table insert body                      | 104,857,600 bytes (100 MiB)                           | HTTP `413`, error `payload_too_large`.                                               |
| Insert requests                        | 1,000 requests per second per table within a database | HTTP `429`, error `rate_limit_exceeded`.                                             |
| Query request body                     | 52,428,800 bytes (50 MiB)                             | HTTP `413`, error `payload_too_large`.                                               |
| Query result (`max_result_bytes`)      | 104,857,600 bytes (100 MiB)                           | HTTP `400`, error `rawtree_error`, with the default overflow behavior.               |
| Query execution (`max_execution_time`) | 30 seconds                                            | HTTP `408`, error `request_timeout`, for execution timeouts mapped by the Query API. |
| Query requests                         | 10,000 requests per second per database               | HTTP `429`, error `rate_limit_exceeded`.                                             |

Body limits apply after request decompression. Splitting an insert into smaller
requests can avoid the body limit, but each request counts toward the rate limit.
An insert error does not guarantee that no rows were written.
See [table inserts](/docs/reference/api/tables#post-v1tablestable) before retrying an upload.

The Query API supplies `max_execution_time` and `max_result_bytes` as database
settings. SQL `SETTINGS` can change these defaults where database permissions allow it.
Database constraints and service transport timeouts still apply.

The database checks result size while it processes blocks. This value does not
describe the final encoded HTTP response size.
See [`max_result_bytes`](/docs/reference/sql/settings/session#max_result_bytes)
and [`max_execution_time`](/docs/reference/sql/settings/session#max_execution_time) for their database semantics.

For [`JSONEachRowWithProgress`](/docs/reference/api/query#query-response-format),
a failure after HTTP headers arrives in the response stream or closes the connection.
HTTP `200` alone does not confirm a successful query.

Rate-limit responses [#rate-limit-responses]

The table and database limits are shared across callers that use the same resource
within an organization and cluster. Changing credentials does not create a separate allowance.
The limiter replenishes capacity at the listed rate and permits bursts up to that capacity.

Successful query and table-insert responses include rate-limit headers when rate limiting is enabled.
Rejected requests return HTTP `429` with `rate_limit_exceeded` and these headers.
Other errors can omit the rate-limit headers.

| Header                  | Meaning                                                           |
| ----------------------- | ----------------------------------------------------------------- |
| `x-ratelimit-limit`     | Maximum request allowance for the resource.                       |
| `x-ratelimit-remaining` | Remaining allowance after this request.                           |
| `x-ratelimit-reset`     | Seconds until the allowance fully recovers, not a Unix timestamp. |
| `retry-after`           | Seconds to wait before retrying a rate-limited request.           |

Wait for `retry-after` before retrying, then reduce the request rate.
Some temporary insert failures also include `retry-after`. Inspect the status and error body.

SQL formatter limits [#sql-formatter-limits]

[`POST /v1/query-format`](/docs/reference/api/query#post-v1query-format) parses SQL without executing it.
Its limits are separate from query execution and ingestion limits.

| Limit                          | Value                 | Result when exceeded                     |
| ------------------------------ | --------------------- | ---------------------------------------- |
| Request body                   | 50 MiB                | HTTP `413`, error `payload_too_large`.   |
| Formatted output               | 100 MiB               | HTTP `413`, error `payload_too_large`.   |
| Formatting time                | 30 seconds            | HTTP `408`, error `request_timeout`.     |
| Concurrent formatting requests | 2 per backend process | HTTP `503`, error `service_unavailable`. |

The concurrency allowance stays occupied until the response finishes or the client disconnects.
The formatter returns an error instead of partial formatted SQL.

Related [#related]

* [Optimize queries](/docs/guides/query/optimize-queries)
* [Errors](/docs/reference/errors)
* [Apps API reference](/docs/reference/api/apps) for protocol-specific behavior.
