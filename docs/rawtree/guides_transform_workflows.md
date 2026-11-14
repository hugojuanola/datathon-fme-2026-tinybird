# SQL workflows (/docs/guides/transform/workflows)



SQL workflows [#sql-workflows]

RawTree Cloud and RawTree BYOC manage workflow definitions, schedules, and sinks
when the workflow service is enabled. RawTree executes the saved SQL.
These schedules are separate from database workload scheduling.

A workflow evaluates read-only SQL or `INSERT INTO ... SELECT` on demand or on a cron schedule.
For read queries, every returned row is a
match; use `WHERE` or `HAVING` in the SQL to express the condition. Each execution
sends one array containing all returned rows to each sink. An empty result
sends nothing. Repeated results and duplicate rows are sent again; consumers own
any deduplication or alerting policy.

To insert query results directly into an existing table on each run, use:

```sql test
INSERT INTO workflow_alerts
SELECT customer_id, count() AS total
FROM events
GROUP BY customer_id
HAVING total > 100
```

The insert follows the [Query API's limits](/docs/reference/api): the target must
already exist in the selected user database. URL table functions and
`INSERT ... VALUES` are rejected; `SETTINGS` clauses are handled by RawTree.
Insert runs return no matching rows and do not send events to sinks.
Logs report `written_rows` on successful evaluations; query failures are recorded
as errors.

Each run lasts as long as its query. Queries follow the Query API's
`max_execution_time` unless the SQL sets its own, so a long `INSERT ... SELECT`
can raise it:

```sql test
INSERT INTO daily_rollup
SELECT customer_id, count() AS total
FROM events
GROUP BY customer_id
SETTINGS max_execution_time = 240
```

Inserts are stopped after 30 minutes, including when the SQL sets
`max_execution_time = 0`. Read queries return their rows in a single response
and are limited to 180 seconds. Scheduled queries for the same workflow do not
overlap, so choose an interval longer than the query takes. Editing a workflow
while an insert is running does not stop that run: it completes with the
definition it started with, and the next run uses the new definition.

The dashboard automatically previews saved read queries. Insert SQL runs only
when you select **Run query**, request an explicit API run, or when the schedule fires; opening a workflow or
cancelling an edit does not execute an insert. **Run query** writes real rows.

Every run executes the insert again, so rows can be inserted repeatedly. A failed
or interrupted execution may have written rows before its outcome became known.
SQL runs are attempted once per execution; inserts are not exactly-once.

Workflows require an enabled workflow service. The [public API reference](/docs/reference/api/workflows)
documents workflow management, logs, and metrics. Organization administrators can
create, run, edit, pause, and delete workflows. Organization members can view
their configuration, including HTTP sink URLs. Header values are never returned.

Schedule a workflow [#schedule-a-workflow]

A workflow's `schedule` sets when it runs automatically. Schedules use cron
syntax and are always evaluated in UTC; there is no per-workflow time zone and no
daylight saving time adjustment. To run at 09:00 in a zone that is UTC+2, schedule
it at 07:00.

```json
"schedule": { "cron": "30 7 * * 1-5", "enabled": true }
```

A cron has five fields, or six when you need second precision. The optional
seconds field goes first:

| Field        | Values                                | Required                   |
| ------------ | ------------------------------------- | -------------------------- |
| Second       | `0`–`59`                              | Only in the six-field form |
| Minute       | `0`–`59`                              | Yes                        |
| Hour         | `0`–`23`                              | Yes                        |
| Day of month | `1`–`31`                              | Yes                        |
| Month        | `1`–`12`                              | Yes                        |
| Day of week  | `0`–`7`, where `0` and `7` are Sunday | Yes                        |

A five-field cron runs at second `0`. Each field accepts:

* `*` for every value.
* A number, such as `5`.
* A range, such as `9-17`.
* A step: `*/15` for every 15th value, or `5/10` for every 10th value starting at 5.
* A comma-separated list of the above, such as `0,30` or `1-5,10`.

Names such as `MON` or `JAN`, shortcuts such as `@hourly`, and the `?`, `L`, and
`#` operators are not supported.

| Cron             | Runs (UTC)                               |
| ---------------- | ---------------------------------------- |
| `* * * * * *`    | Every second                             |
| `*/10 * * * * *` | Every 10 seconds                         |
| `*/5 * * * *`    | Every 5 minutes                          |
| `0 * * * *`      | At the start of every hour               |
| `30 7 * * 1-5`   | At 07:30, Monday through Friday          |
| `0 0 1 * *`      | At 00:00 on the first day of every month |
| `0 9-17/2 * * *` | At 09:00, 11:00, 13:00, 15:00, and 17:00 |
| `0 0 13 * 5`     | At 00:00 on every Friday the 13th        |

When both day of month and day of week are restricted, a run happens only on
days that match both. `0 0 13 * 5` runs on Fridays that fall on the 13th, not on
every Friday and every 13th. Many cron implementations run on either day.

The dashboard describes the schedule in words as you type it, and the API
returns the next run time in `schedule.next_run_at`.

Scheduled ticks are skipped while the previous scheduled run is active unless
delivery overlap is enabled. With delivery overlap, a new run can start while an
earlier run waits for its sinks. If the earlier scheduled query is still
executing, the new run fails with `evaluation_already_running`. Choose an interval
longer than the query takes. If the workflow service is unavailable when a run is
due, the missed run starts late
only within a short window: the gap between consecutive runs, at least 10
seconds and at most one day. Older missed runs are skipped rather than replayed.

Set `enabled` to `false` to pause a schedule; it keeps its cron and resumes with
`{"schedule": {"enabled": true}}`. Set `schedule` to `null` for a manual-only
workflow with no automatic runs. Omitting `schedule` from an update keeps it as
it is. A new workflow without a `schedule` runs every second.

Run a workflow explicitly [#run-a-workflow-explicitly]

Start one execution of a saved workflow with no request body:

```bash
curl -X POST "$RAWTREE_URL/v1/workflows/$WORKFLOW_ID/runs?organization=$ORGANIZATION&cluster=$CLUSTER" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Idempotency-Key: $REQUEST_ID"
```

Set `REQUEST_ID` to a fresh UUID for each intended execution. The optional
`Idempotency-Key` accepts 1–128 visible ASCII characters without spaces.
The API returns `202 Accepted` with `id`, `workflow_id`, `query_id`, and
`source: "manual"` after the execution service accepts the run. `query_id` uses
`workflow:{workflow_id}:{run_id}`. Search `system.query_log` for that ID after
the query runs. Acceptance does not mean SQL or sink delivery has completed. Use the
[runs endpoint](/docs/reference/api/workflows) to list
execution status and the workflow's Logs to inspect SQL and sink delivery events.

Explicit runs work with manual-only, active, paused, or absent schedules and leave scheduling
unchanged. They execute the saved SQL and configured sinks with the same
permissions and limits as scheduled runs. Organization admins and admin API keys
can start them. The saved revision is pinned when the request is accepted; if it
changes before execution, the run fails with `workflow_definition_changed`.

An explicit run can overlap another manual or scheduled execution of the same
workflow. Each run executes independently. Up to two workflow evaluations can
run concurrently per cluster; additional runs wait up to five seconds for capacity
before failing with `workflow_capacity_unavailable`.

Retry with the same key to recover the same execution, including after a timeout
or completion. Keys are scoped to the workflow, and deduplication lasts while
Temporal retains that execution's history. A new key, or a request without a key,
starts another execution. Run acceptance deduplication does not guarantee
exactly-once SQL writes or sink delivery.

List manual and scheduled executions together with
`GET /v1/workflows/{workflow_id}/runs?organization=...&cluster=...`.
Pages default to 20 runs and accept `limit` from 1 to 100. Pass `next_cursor` as
`cursor` to continue; `next_cursor: null` marks the end. The page limit does not
cap the total number of runs you can retrieve.

Temporal supplies this execution history. Active runs appear first, newest
started first, followed by finished runs, newest finished first. Newly started
runs and status changes can take a short time to appear. History is available
for as long as Temporal retains it; pagination is not a frozen snapshot of runs
that are still changing. A run stays `running` until every sink reports how its
delivery ended, so `completed` means every sink received its rows. Inspect Logs
for each delivery attempt.

Configure sinks [#configure-sinks]

Sinks are optional. Open the **Sinks** tab in the workflow editor to add up to
five sinks:

* **HTTP** sends the event to a webhook. Enter a URL and optional custom headers.
  The URL and header values are encrypted at rest. URLs are visible in the
  workflow list and API responses; header values are write-only. On edit,
  leave the URL blank and configured header values blank to preserve them.
  URLs and header values cannot contain `{{`, `%`, or `${`: these are reserved
  by the delivery configuration. Percent-encoded URLs are not currently supported.
* **Table** inserts the returned rows to a RawTree table. Select its
  database and table; the service creates and manages the scoped write-only sink key
  under the hood.
* **Slack** posts a message with the returned rows to a Slack channel. Select a
  connected workspace and a channel. See [Post results to Slack](#post-results-to-slack).

The equivalent API request is:

Replace `placeholder` with the sink's bearer token.

```bash
curl -X POST "$RAWTREE_URL/v1/workflows?organization=$ORGANIZATION&cluster=$CLUSTER" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
  {
    "name": "high-volume-customers",
    "query": {
      "database": "default",
      "sql": "WITH accurateCastOrNull(customer_id, 'String') AS customer_key SELECT customer_key AS customer_id, count() AS total FROM events WHERE customer_key IS NOT NULL GROUP BY customer_key HAVING total > 100"
    },
    "schedule": {"cron": "*/5 * * * * *", "enabled": true},
    "sinks": [
      {
        "type": "http",
        "settings": {
          "url": "https://example.com/events",
          "headers": {"Authorization": "Bearer placeholder"}
        }
      },
      {
        "type": "table",
        "settings": {
          "database": "default",
          "table": "workflow_alerts"
        }
      }
    ]
  }
JSON
```

Each sink keeps `id` and `type` at the top level. Type-specific fields belong in
`settings`; flattened fields are rejected. HTTP responses return
`settings.url_configured` and `settings.header_names`, never the URL or header values.
Table responses return `settings.database` and `settings.table`.

When updating an existing HTTP sink, omit `settings`, `settings.url`, or
`settings.headers` to preserve the corresponding saved values. In a supplied
headers map, `null` preserves the stored value for the same case-insensitive
name, omitted names are removed, and `{}` clears all headers.

Every sink has a stable ID. Omit `id` when adding a sink; the service
assigns one. Preserve that ID when editing. PATCH replaces the sink list when
`sinks` is supplied; omitting it preserves the existing list. Send `"sinks": []`
to remove all sinks.

Post results to Slack [#post-results-to-slack]

A Slack sink posts one message per execution to a channel. The message names
the workflow, links to it in the dashboard, and previews the returned rows as one
JSON object per line:

```text
Workflow high-volume-customers returned 2 rows.
{"customer_id":"customer-a","total":101}
{"customer_id":"customer-b","total":125}
Sent by RawTree
```

The preview shows up to 100 rows and truncates very long rows. When it cannot
fit every row, the footer reads `Showing 100 of 150 rows`. To get every row,
add an HTTP or table sink next to the Slack sink.

Connect a Slack workspace [#connect-a-slack-workspace]

An organization administrator connects Slack once per workspace. Open the
organization's **Settings**, go to **Integrations**, and select
**Add Slack workspace**. Slack asks you to approve the RawTree app. Connect
more workspaces the same way; each workflow sink picks one.

The channel picker lists public channels and the private channels the RawTree
app is a member of. To post to a private channel, invite the RawTree app to it
in Slack first.

Disconnecting a workspace stops delivery to every sink that uses it. Those
sinks record failed deliveries in Logs until you point them at another
workspace or remove them. A sink cannot be saved against a disconnected
workspace.

Configure a Slack sink through the API [#configure-a-slack-sink-through-the-api]

A Slack sink takes the workspace's `integration_id` and exactly one of
`channel_id` or `channel_name`:

```json
{
  "type": "slack",
  "settings": {
    "integration_id": "0f8b6c4e-5d1a-4b7e-9c3f-2a1d8e6b4c90",
    "channel_name": "#alerts"
  }
}
```

Channel IDs look like `C0123456789`. A channel name, with or without `#`, is
resolved to its ID when the sink is saved, so renaming the channel in Slack
later does not break the sink. Responses return `settings.integration_id`,
`settings.channel_id`, and `settings.channel_name`. To reuse a connected
workspace, read `integration_id` from an existing Slack sink.

When updating a Slack sink, omitted settings keep their saved values. Each
Slack sink in a workflow must target a different workspace and channel pair.

Event format and delivery [#event-format-and-delivery]

HTTP and table sinks receive the plain JSON array returned by the SQL:

```json
[
  {"customer_id": "customer-a", "total": 101},
  {"customer_id": "customer-b", "total": 125}
]
```

Two matching rows and two sinks produce two requests, each containing
that complete array. A table sink inserts both rows in one request.

The service hands these results to its managed Vector data plane. Vector uses durable
disk buffers and retries retryable HTTP failures. HTTP requests include
`X-RawTree-Event-Id`, `X-RawTree-Sink-Id`, and an `Idempotency-Key` of
`rawtree/event_id/sink_id`. Delivery is at-least-once, so receivers should
deduplicate using that key. Table sinks use the same key as the insert
deduplication token, so a retried delivery does not insert the rows again.

Slack has no idempotency key, so Slack sinks retry only when the service knows the
message was not posted, such as when Slack is rate limiting or unreachable.
When the outcome is unknown, for example after a timeout or a server error,
The service records `slack_delivery_unconfirmed` and does not retry, so the
message may be missing from the channel.

Each run attempts SQL once. A query or handoff failure is recorded
in Logs; the next scheduled run evaluates independently. Once accepted by Vector,
sink retries reuse the buffered array without executing SQL again.
Retries stop one hour after the handoff: the next retryable failure is
recorded with `sink_retry_expired` and the event is dropped. A sink delivers
its events in order, so an event that keeps failing delays later events for
that sink until it succeeds or expires.
Delivery IDs are scoped to the execution and sink, so the next execution
has a new ID even when its rows are identical.

The API rejects explicit private, loopback, link-local, and metadata addresses
unless the operator has allowed the exact origin. Delivery also checks resolved
IP addresses and does not follow redirects. Vector owns buffering and retries;
The service's delivery endpoint performs and observes each sink request.
Pausing a workflow stops new scheduled evaluations. Explicit runs remain available.

Inspect a workflow's lifecycle [#inspect-a-workflows-lifecycle]

The editor has four tabs:

| Tab      | What it shows                                                           |
| -------- | ----------------------------------------------------------------------- |
| SQL      | The exact SQL sent through the Query API and its native result or error |
| Settings | Schedule and enabled state                                              |
| Sinks    | HTTP, table, and Slack delivery targets                                 |
| Logs     | Saved evaluations, returned rows, handoffs, and sink attempts           |

Logs become available after saving a workflow. Choose a time range, refresh to
see new activity, or load older records. Expand a returned row to inspect its data. Expand correlation IDs to connect an evaluation run, logical match,
and delivery attempt. Retries keep the same match event ID but get separate
attempt IDs. Each sink attempt includes its type, HTTP status when
available, duration, and a safe failure code.

```text
Evaluation started → evaluation result / returned rows
                                      ↓
                              Vector handoff accepted
                                      ↓
                              Sink attempt
                               ↙             ↘
                         Accepted       Failed → retry, if retryable
```

An accepted Vector handoff is **not** a successful sink delivery. A
successful delivery means the sink returned a 2xx response, not that
its application finished processing the event. A timeout leaves delivery
uncertain; the receiver may have accepted the event before the timeout.

The same history is available through the scoped API:

```bash
curl "$RAWTREE_URL/v1/workflows/$WORKFLOW_ID/logs?organization=$ORGANIZATION&cluster=$CLUSTER&limit=100" \
  -H "Authorization: Bearer $SESSION_TOKEN"
```

The response contains `logs`, `from`, `to`, and `next_cursor`. Pass the returned
`from`, `to`, and `next_cursor` as `cursor` for a stable older page. `from` and
`to` are Unix milliseconds; requests default to the last 24 hours and support
ranges up to seven days, including older historical ranges. `limit` is 1–200.

History is best-effort observability, not an exactly-once audit ledger.
Writes may be delayed, duplicated, or dropped
during overload or outages. A process crash can leave a started operation
without a recorded result. Execution and delivery do not depend on these logs.

Webhook URLs, headers, and receiver response bodies are not included. Returned
rows are recorded on `workflow.matched` events and are visible to
members of the owning organization. Payloads larger than 16 KiB are omitted
from history with `payload_omitted: true`; the sink still receives the
full event. Each sink event is delivered in a separate request so every
attempt has an unambiguous result.
