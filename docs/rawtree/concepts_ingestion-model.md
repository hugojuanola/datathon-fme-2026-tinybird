# Ingestion model (/docs/concepts/ingestion-model)



Ingestion model [#ingestion-model]

Ingestion turns source records into rows in a RawTree table. You select a
cluster, database, and destination table. RawTree accepts JSON without an
upfront column definition, while permissions still control where you can write.

From a payload to a table [#from-a-payload-to-a-table]

RawTree parses and stores rows. RawTree Cloud and RawTree BYOC supply the
insert API, source integrations, and table-creation orchestration described here.
SQL ingestion and the insert API have separate request contracts.

A normal JSON insert sends one object or a collection of objects. Each object
becomes a row. The service creates a missing table when the caller has permission
to use automatic table creation. A key restricted to database roles can insert
into existing tables, but it does not receive automatic table-creation rights.

A later insert can introduce fields that earlier rows do not contain. Existing
rows do not need a rewrite to acquire those fields. A known field absent from
an earlier row returns `NULL` when queried. Values at the same path can have
different types. See [Raw tables](/docs/concepts/raw-tables) and
[Dynamic fields](/docs/concepts/dynamic-fields).

A table's schema describes the fields RawTree can expose. It is not a promise
that every row contains each field or uses the same type.

Ingestion paths [#ingestion-paths]

| Path             | What happens                                                                           |
| ---------------- | -------------------------------------------------------------------------------------- |
| JSON body insert | The service forwards ordinary JSON to RawTree for parsing and insertion.               |
| URL import       | The database reads a public source URL. The request waits for the import to finish.    |
| Transform        | A built-in preprocessor extracts or reshapes records before insertion.                 |
| App endpoint     | A supported protocol, such as OpenTelemetry, maps incoming data to table rows.         |
| Connector        | A managed process reads an external source and delivers records to a configured table. |

These paths share tables, but their response and retry contracts differ.
Transforms do not apply to URL imports. Native OpenTelemetry exports can report
partial success, including the number of rejected records. See
[Apps, connectors, and transforms](/docs/concepts/apps-connectors-and-transforms).

What an insert result means [#what-an-insert-result-means]

For ordinary JSON inserts, the database reports summary counters such as
`written_rows`. The compatibility field `inserted` contains the numeric row
count, or `null` when that count is unavailable. A reported count can describe
a deduplicated request without adding new stored rows.

The response describes that insert request. It does not report completion of
every replica or downstream workflow. Queries, connector delivery, and workflow
runs have their own outcomes.

An unsuccessful upload can still create a table or write some rows. A timeout
or lost response can also occur after the database accepts data. Failure does
not imply rollback.

Retries and duplicate rows [#retries-and-duplicate-rows]

Ordinary JSON uploads stream to the database. The API does not retain a complete
payload for automatic replay. The sender owns the payload and retry decision.
Temporary failures can include a retry delay. Invalid data and permission
errors need correction before another attempt.

A retry can write the same records again. Ordinary JSON body inserts disable
insert deduplication by default. The API exposes `deduplicate_insert` and
`insert_deduplication_token` for deliberate retry handling. A stable token must
identify the same intended insert, not unrelated batches.

Insert deduplication is an engine mechanism with configuration and retention
limits. It does not establish permanent row-level uniqueness or make a series
of requests atomic. Applications that require unique business events need an
explicit event identity and duplicate-handling policy.

Batches and visibility [#batches-and-visibility]

Batch size affects request overhead, memory use, and the amount of data that
needs a retry. The request-body limit bounds each upload. For compressed
uploads, the limit applies after decompression.

Replication and background work can continue independently of a client
request. A table that is not yet available on the destination replica can
produce a temporary insert failure. See
[Storage and compute](/docs/concepts/storage-and-compute).

Related [#related]

* [Ingest data](/docs/guides/ingest/ingest-data)
* [Insert API](/docs/reference/api/tables#post-v1tablestable)
* [Limits](/docs/reference/limits)
* [Queries and results](/docs/concepts/queries-and-results)
