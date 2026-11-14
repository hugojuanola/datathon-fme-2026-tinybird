# SQL workflows (/docs/concepts/sql-workflows)



SQL workflows [#sql-workflows]

SQL workflows are service-managed jobs in RawTree Cloud and RawTree BYOC,
where enabled. RawTree executes their SQL. The service stores definitions,
starts runs, and delivers results to sinks. A workflow schedule is separate
from the database workload scheduler, which allocates query resources.

A SQL workflow turns a query into repeatable work. It evaluates saved SQL on
demand or on a schedule. Read results can go to external destinations or other
RawTree tables. An insert query can write directly to an existing table.

Definition, schedule, run, and sink [#definition-schedule-run-and-sink]

| Object   | Meaning                                                 |
| -------- | ------------------------------------------------------- |
| Workflow | The saved SQL, its configuration, and its destinations. |
| Schedule | The rule that starts automatic executions.              |
| Run      | One execution, with its own status and query identity.  |
| Sink     | A destination for the rows returned by a read query.    |

Saving a workflow, accepting a run, finishing SQL, and completing delivery are
separate events. A run's status and logs connect those events.

Workflows belong to an organization and cluster. Their database scope and
permissions determine which data they can use. The workflow service must be
enabled in the environment.

Reads and inserts have different effects [#reads-and-inserts-have-different-effects]

For a read query, each returned row is a match. The SQL's filters and
aggregation determine those matches. A nonempty result goes to the configured
sinks. An empty result sends nothing.

Each execution evaluates the query again. The same rows can match on several
runs, and each run can send them again. The SQL or receiving application owns
any rule about alert suppression or already-processed events.

An `INSERT INTO ... SELECT` workflow writes results into an existing table.
It returns no matching rows for sinks. Each run attempts the insert again, so
repeated execution can produce duplicate rows. A failed or interrupted insert
can leave rows already written.

Scheduled and explicit executions [#scheduled-and-explicit-executions]

Schedules use cron in UTC. Pausing a schedule stops new scheduled evaluations,
but explicit runs remain available. A manual-only workflow has no active
schedule.

Scheduled executions normally avoid overlap. Optional delivery overlap permits
a new run while an earlier run waits for sinks, but not overlapping scheduled
SQL evaluations. Explicit runs can overlap other runs, subject to cluster
capacity limits.

A missed schedule does not imply unlimited catch-up. The service can recover
recent missed runs within its catch-up window and skip older ones. Recurring
jobs therefore need an intentional data window or progress-tracking strategy.

An explicit run request can use an idempotency key to recover the same accepted
execution after a retry. That protects run creation within the service's
retention period. It does not make SQL writes or sink delivery exactly-once.

Result delivery [#result-delivery]

HTTP and table sinks receive an array of result rows. A Slack sink sends a
message with a bounded preview. A query can succeed while one of its sinks
fails, so delivery has its own status.

HTTP and table delivery uses managed buffers and retries retryable failures.
Delivery can occur more than once. HTTP receivers can use the supplied
idempotency key to identify a repeated delivery. Table sinks use an insert
deduplication token.

Slack has a different retry policy. When an outcome is uncertain, the service can
record an unconfirmed delivery instead of repeating a message that might
already exist.

Each run attempts SQL once. Sink retries reuse that run's result rather than
executing the SQL again. A later run has a new delivery identity even if its
rows are identical. Retryable delivery also has an expiry limit.

Observe the full lifecycle [#observe-the-full-lifecycle]

Run acceptance does not establish query success. A handoff to the delivery
service does not establish sink success. Even a successful HTTP delivery only
means the receiver accepted the request, not that its application finished
processing it.

Runs and logs expose query execution and sink outcomes. Metrics summarize
executions, matches, deliveries, and errors. These distinctions help separate a
query problem from a delivery problem.

Related [#related]

* [SQL workflows guide](/docs/guides/transform/workflows)
* [Workflows API](/docs/reference/api/workflows)
* [Queries and results](/docs/concepts/queries-and-results)
* [Monitor usage](/docs/guides/operate/monitor-usage)
