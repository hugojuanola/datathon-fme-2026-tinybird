# Errors (/docs/reference/errors)



Errors [#errors]

Service API errors in RawTree Cloud and RawTree BYOC normally use this JSON body:

```json
{
  "error": "not_found",
  "message": "The requested resource was not found.",
  "hint": "Check the resource identifier."
}
```

The JSON field is `error`, not `code`. Its value is the backend error code.
The backend also attaches the code to structured request details.

The singular `hint` gives guidance for the failed API request.
It can concern authentication, permissions, request syntax, or other errors.
The plural `hints` in query results contains
[runtime type-compatibility warnings](/docs/concepts/dynamic-fields#runtime-type-compatibility-warnings),
which can accompany a successful query.

Other response formats [#other-response-formats]

Some endpoints use a different error format:

* OAuth protocol errors use `error` and `error_description`, without `hint`.
* JSON table inserts without a transform can return the database's native HTTP status, body, and exception headers.
* Native app endpoints can use their protocol's error format. See [OpenTelemetry](/docs/reference/api/apps/opentelemetry), [Prometheus](/docs/reference/api/apps/prometheus), and [Splunk](/docs/reference/api/apps/splunk).
* Streaming queries can report an exception after HTTP `200`, or the connection can close before completion.

Check the endpoint's response format before parsing an error.
For [streaming queries](/docs/reference/api/query#query-response-format), consume the complete response and check for exceptions.

Error codes [#error-codes]

The following codes apply to the standard service error body.

| Error code                                            | HTTP status | Meaning                                                                   |
| ----------------------------------------------------- | ----------: | ------------------------------------------------------------------------- |
| [`bad_request`](#bad_request)                         |         400 | The request or input is invalid.                                          |
| [`request_body_incomplete`](#request_body_incomplete) |         400 | The server could not read the complete request body.                      |
| [`request_body_timeout`](#request_body_timeout)       |         408 | The server did not receive the complete request body before its deadline. |
| [`payload_too_large`](#payload_too_large)             |         413 | A request body or formatter output exceeds its size limit.                |
| [`request_timeout`](#request_timeout)                 |         408 | The request exceeded its time limit.                                      |
| [`unprocessable_entity`](#unprocessable_entity)       |         422 | The server cannot process the request content.                            |
| [`unauthorized`](#unauthorized)                       |         401 | The request lacks valid authentication.                                   |
| [`forbidden`](#forbidden)                             |         403 | The authenticated caller cannot perform the request.                      |
| [`payment_required`](#payment_required)               |         402 | The organization cannot perform the request under its current plan.       |
| [`authorization_pending`](#authorization_pending)     |         428 | Authorization is not complete.                                            |
| [`service_unavailable`](#service_unavailable)         |         503 | A required service is unavailable.                                        |
| [`cluster_paused`](#cluster_paused)                   |         409 | The cluster is paused.                                                    |
| [`upstream_unavailable`](#upstream_unavailable)       |         503 | No healthy cluster upstream is available.                                 |
| [`not_found`](#not_found)                             |         404 | The requested resource does not exist.                                    |
| [`conflict`](#conflict)                               |         409 | The request conflicts with the current resource state.                    |
| [`rawtree_error`](#rawtree_error)                     |         400 | RawTree rejected the query or operation.                                  |
| [`internal_error`](#internal_error)                   |         500 | An unexpected server error occurred.                                      |
| [`rate_limit_exceeded`](#rate_limit_exceeded)         |         429 | The request rate exceeds an endpoint limit.                               |

`bad_request` [#bad_request]

**HTTP status:** `400`

**Meaning:** The request contains invalid input.

**Common causes:** A required parameter is missing, or a value fails route validation.

**What to do:** Correct the input. Follow the response `message` and `hint`.

`request_body_incomplete` [#request_body_incomplete]

**HTTP status:** `400`

**Meaning:** The server could not read the complete request body.

**Common causes:** The upload connection closed or the body ended before the server received it.

**What to do:** Check the upload connection and client timeout settings.

`request_body_timeout` [#request_body_timeout]

**HTTP status:** `408`

**Meaning:** The server timed out while it read the request body.

**Common causes:** The client did not send the complete body before the upload deadline.

**What to do:** Send the complete request body within the upload deadline.

`payload_too_large` [#payload_too_large]

**HTTP status:** `413`

**Meaning:** A request body or formatted SQL output exceeds its size limit.

**Common causes:** A query body exceeds 50 MiB, a table-insert body exceeds 100 MiB, or formatted SQL exceeds 100 MiB.

**What to do:** Reduce the body size, split an insert, or format a smaller SQL selection. See [Limits](/docs/reference/limits).

`request_timeout` [#request_timeout]

**HTTP status:** `408`

**Meaning:** Query execution or SQL formatting exceeded its time limit.

**Common causes:** A query exceeded its effective `max_execution_time`, or SQL formatting exceeded 30 seconds.

**What to do:** [Optimize the query](/docs/guides/query/optimize-queries) or format a smaller SQL selection. Check the response `hint` for the effective timeout.

`unprocessable_entity` [#unprocessable_entity]

**HTTP status:** `422`

**Meaning:** The server received the content but could not process it.

**Common causes:** JSON fields have invalid data, or a PromQL query is unsupported.

**What to do:** Correct the content. Follow the response `message` and `hint`.

`unauthorized` [#unauthorized]

**HTTP status:** `401`

**Meaning:** The request does not have valid authentication.

**Common causes:** The request has no valid API key or access token.

**What to do:** Send valid credentials in the `Authorization` header. Follow the response `hint`.

`forbidden` [#forbidden]

**HTTP status:** `403`

**Meaning:** The authenticated caller cannot perform the requested operation.

**Common causes:** The API key or database role does not have the required permission.

**What to do:** Check the key permission and database role grants named in the response `hint`.

`payment_required` [#payment_required]

**HTTP status:** `402`

**Meaning:** The organization's current billing state blocks the request.

**Common causes:** Trial credits are depleted or expired, the spending limit is reached, or the subscription is inactive.

**What to do:** Follow the response `hint` to update billing or the spending limit.

`authorization_pending` [#authorization_pending]

**HTTP status:** `428`

**Meaning:** The authorization flow is not complete.

**Common causes:** The user has not completed the pending authorization request.

**What to do:** Complete authorization, then retry the request. OAuth token endpoints use their own protocol errors and status codes.

`service_unavailable` [#service_unavailable]

**HTTP status:** `503`

**Meaning:** A service required for the request is unavailable.

**Common causes:** A dependent service is unavailable, the SQL formatter is busy, or an insert upload stops making progress.

**What to do:** Follow the response `hint`. Retry when the service is available.

`cluster_paused` [#cluster_paused]

**HTTP status:** `409`

**Meaning:** The cluster is paused and cannot serve data requests.

**Common causes:** The request targets a paused cluster.

**What to do:** Resume the cluster before sending data requests.

`upstream_unavailable` [#upstream_unavailable]

**HTTP status:** `503`

**Meaning:** No healthy cluster upstream is available.

**Common causes:** The cluster has no healthy upstream, or the service cannot reach the database.

**What to do:** Check cluster status. Retry when the cluster is ready.

`not_found` [#not_found]

**HTTP status:** `404`

**Meaning:** The requested resource does not exist.

**Common causes:** A resource identifier does not match an existing resource.

**What to do:** Check the identifier and follow the response `hint`.

`conflict` [#conflict]

**HTTP status:** `409`

**Meaning:** The request conflicts with the current resource state.

**Common causes:** The requested change is not valid for the resource's current state.

**What to do:** Follow the response `message` and `hint`, then resolve the conflict.

`rawtree_error` [#rawtree_error]

**HTTP status:** `400`

**Meaning:** RawTree rejected a query or database operation.

**Common causes:** SQL syntax is invalid, a table does not exist, a grant is missing, or the query result exceeds its size limit.

**What to do:** Correct the SQL or resource name. Check the database role grants when the response reports access denied.

`internal_error` [#internal_error]

**HTTP status:** `500`

**Meaning:** The server could not complete the request because of an internal error.

**Common causes:** An unexpected backend operation failed.

**What to do:** Try again or contact support.

`rate_limit_exceeded` [#rate_limit_exceeded]

**HTTP status:** `429`

**Meaning:** The request rate exceeds the limit for its endpoint.

**Common causes:** Too many queries share a database, or too many inserts target one table. OAuth endpoints also impose request-rate limits.

**What to do:** Wait for `retry-after` when present, then reduce the request rate.
See [rate-limit responses](/docs/reference/limits#rate-limit-responses) for query and insert headers.
OAuth responses use `error_description` and can omit those headers.

Authentication challenges [#authentication-challenges]

Standard HTTP `401` responses include `WWW-Authenticate: Bearer`.

For OAuth authorization, the challenge can identify the protected resource
metadata endpoint:

```text
WWW-Authenticate: Bearer resource_metadata="https://api.rawtree.com/.well-known/oauth-protected-resource"
```

Retry behavior [#retry-behavior]

An error or closed connection does not prove that a write had no effect.
An insert can write rows before it fails, and timed-out distributed DDL can still finish.
Check query history or the destination state before retrying a write.
Use supported [insert deduplication](/docs/reference/api/tables#post-v1tablestable) when retries must avoid duplicate rows.

Examples [#examples]

This query returns a `rawtree_error` because the table does not exist:

```sql test expect-error="not found"
SELECT * FROM missing_events
```

A query that names a missing column also returns a `rawtree_error`:

```sql test expect-error="Unknown expression identifier"
SELECT missing_column
```
