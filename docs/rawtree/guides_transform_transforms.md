# Transforms (/docs/guides/transform/transforms)



Transforms [#transforms]

A transform changes a payload before RawTree stores its rows. RawTree Cloud and
RawTree BYOC run these built-in preprocessors in the insert service.

Many telemetry and cloud services send one large JSON object that contains the real events inside an array. That wrapper object is useful for delivery, but it is not always the shape you want to query. A transform tells the service which array contains the real rows and which wrapper fields should be copied onto each row.

Without a transform, RawTree stores the JSON object you send. With a transform, the service reads the JSON object, extracts the nested records, and stores each extracted record as its own row.

Example [#example]

CloudWatch Logs sends payloads shaped like this:

```json
{
  "owner": "123456789012",
  "logGroup": "/aws/lambda/api",
  "logStream": "2024/01/15/[$LATEST]abcdef",
  "logEvents": [
    { "id": "1", "timestamp": 1705312800000, "message": "started" },
    { "id": "2", "timestamp": 1705312800100, "message": "finished" }
  ]
}
```

If you insert that JSON without a transform, the service inserts one row: the wrapper object with a nested `logEvents` array.

If you insert it with `--transform cloudwatch-logs`, the service inserts two rows, one for each log event:

```json
{
  "id": "1",
  "timestamp": 1705312800000,
  "message": "started",
  "owner": "123456789012",
  "logGroup": "/aws/lambda/api",
  "logStream": "2024/01/15/[$LATEST]abcdef"
}
```

```json
{
  "id": "2",
  "timestamp": 1705312800100,
  "message": "finished",
  "owner": "123456789012",
  "logGroup": "/aws/lambda/api",
  "logStream": "2024/01/15/[$LATEST]abcdef"
}
```

Now you can query the log events directly:

```sql test
SELECT timestamp, message, logGroup
FROM cloudwatch_logs
ORDER BY timestamp
LIMIT 10;
```

When to use transforms [#when-to-use-transforms]

Use a transform when all of these are true:

* Your source format is one of the supported formats below.
* One JSON object contains many records inside a nested array.
* You want to query those records as table rows.

Do not use a transform when your data is already one event per JSON object or one event per JSONL line. Insert that data normally.

The service supports built-in transforms only. Custom transform code is not currently supported; transform the data before insert if you need a custom shape.

How to insert with a transform [#how-to-insert-with-a-transform]

Use `--transform` with inline JSON, JSON files, or JSONL files.

```bash
rtree insert --table traces \
  --data '{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"api"}}]},"scopeSpans":[{"scope":{"name":"http"},"spans":[{"name":"GET /health","spanId":"abc"}]}]}' \
  --transform otlp-traces
```

The API accepts the transform name as a query parameter on a JSON body insert.

```bash
curl -X POST "https://api.rawtree.com/v1/tables/traces?transform=otlp-traces" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"api"}}]},"scopeSpans":[{"scope":{"name":"http"},"spans":[{"name":"GET /health","spanId":"abc"}]}]}'
```

After insert, query the destination table as usual.

```bash
rtree query "SELECT * FROM traces LIMIT 10"
```

Transforms are not supported with URL inserts. If you use `?url=`, transform the data before hosting it.

Supported transforms [#supported-transforms]

| Transform         | Input shape                                                                                          | Output rows                   |
| ----------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------- |
| `otlp-traces`     | OTLP export with `resourceSpans`, or one resource span object with `resource` and `scopeSpans`       | One row per span              |
| `otlp-logs`       | OTLP export with `resourceLogs`, or one resource log object with `resource` and `scopeLogs`          | One row per log record        |
| `otlp-metrics`    | OTLP export with `resourceMetrics`, or one resource metric object with `resource` and `scopeMetrics` | One row per data point        |
| `cloudwatch-logs` | CloudWatch Logs payload with `logEvents`                                                             | One row per log event         |
| `cloudtrail`      | CloudTrail payload with `Records`                                                                    | One row per CloudTrail record |
| `firehose`        | AWS Firehose HTTP endpoint payload with `records[].data`                                             | One row per decoded record    |

Unknown transform names return a `400` response with the list of supported names.

Native OpenTelemetry endpoints [#native-opentelemetry-endpoints]

OpenTelemetry SDKs and collectors can send native OTLP to the service without adding a `transform` query parameter. Native OTLP uses the same `otlp-traces`, `otlp-logs`, and `otlp-metrics` transforms described below.

See the [OpenTelemetry guide](/docs/integrations/opentelemetry) for endpoints, authentication, SDK environment variables, Collector config, custom table headers, and a smoke test.

OpenTelemetry output [#opentelemetry-output]

The OpenTelemetry transforms flatten OTLP `attributes` arrays into each emitted row. The transform flattens both resource attributes and record attributes from spans, log records, and metric data points. Attribute values such as `stringValue`, `intValue`, `boolValue`, and `doubleValue` are unwrapped into their inner values. Complex attribute values such as `arrayValue` and `kvlistValue` keep their OTLP wrapper object. Emitted rows do not keep the original `attributes` array.

For traces and logs, the transform also adds `scope.name` when the source scope includes a name.

For metrics, the transform emits one row per data point and adds metric metadata:

| Field                | Description                                                                                     |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| `metric.name`        | The OTLP metric name                                                                            |
| `metric.type`        | The OTLP metric type, such as `gauge`, `sum`, `histogram`, `summary`, or `exponentialHistogram` |
| `metric.unit`        | The metric unit when present                                                                    |
| `metric.description` | The metric description when present                                                             |
| `scope.name`         | The instrumentation scope name when present                                                     |

Result shapes [#result-shapes]

The exact output columns depend on the source fields. Each transform starts with the nested record it unwraps, flattens that record's `attributes` array into top-level fields, then merges selected wrapper fields into the row.

JSON compatibility and protobuf ingestion [#json-compatibility-and-protobuf-ingestion]

JSON ingestion and explicit `otlp-*` JSON transforms preserve their existing
shape rules: omitted protocol fields stay omitted, supplied default values stay
present, timestamp strings and numbers keep their supplied representation, and
an explicitly empty scope name is preserved. Integer normalization still applies
to schema-defined integer attributes and measurements; intentional strings are
not converted.

Native HTTP protobuf and gRPC are adapted to OTLP JSON before entering
those same transforms. The adapter retains decoded protobuf defaults, emits
nanosecond timestamps as exact decimal strings, and puts exemplar measurements
at `exemplars[].asInt` or `exemplars[].asDouble`. Selected zero measurements and
optional histogram `sum`, `min`, and `max` values retain their presence.

Protobuf does not distinguish omitted ordinary scalars from explicitly supplied
defaults. Protobuf rows can therefore contain additional default fields, such as
`flags: 0`, empty strings, and empty arrays, that a JSON sender omitted.
Zero counts and empty scope names are retained too. Absent optional values are
not invented. Field presence and numeric-versus-string timestamp choices need
not be identical across transports. JSON behavior is not changed
to force that equality. These ingestion rules do not rewrite existing rows.

`otlp-traces` [#otlp-traces]

Input can be a full OTLP export with `resourceSpans`, or a single resource span object with `resource` and `scopeSpans`.

For each item in `scopeSpans[].spans[]`, the service inserts one row. The row starts with the span object itself, then the transform flattens span attributes such as `model`, adds resource attributes such as `service.name`, and adds `scope.name` when the source scope has a name.

Example output row from a span named `GET /health`:

```json
{
  "spanId": "abc",
  "name": "GET /health",
  "model": "claude-haiku",
  "service.name": "api",
  "scope.name": "http"
}
```

`otlp-logs` [#otlp-logs]

Input can be a full OTLP export with `resourceLogs`, or a single resource log object with `resource` and `scopeLogs`.

For each item in `scopeLogs[].logRecords[]`, the service inserts one row. The row starts with the log record object itself, then the transform flattens log record attributes such as `user.email`, adds resource attributes such as `service.name`, and adds `scope.name` when the source scope has a name.

Example output row from an INFO log record:

```json
{
  "timeUnixNano": "1700000000000000000",
  "severityText": "INFO",
  "body": { "stringValue": "request started" },
  "user.email": "user@example.com",
  "service.name": "api",
  "scope.name": "logger"
}
```

`otlp-metrics` [#otlp-metrics]

Input can be a full OTLP export with `resourceMetrics`, or a single resource metric object with `resource` and `scopeMetrics`.

For every metric data point under `gauge`, `sum`, `histogram`, `summary`, or `exponentialHistogram`, the service inserts one row. The row starts with the data point object itself, then the transform flattens data point attributes, adds resource attributes, optional `scope.name`, and metric fields such as `metric.name`, `metric.type`, `metric.unit`, and `metric.description`.

Example output row from a `cpu.usage` gauge data point:

```json
{
  "timeUnixNano": "1700000000000000000",
  "asDouble": 42.5,
  "host.name": "node-1",
  "scope.name": "runtime",
  "metric.name": "cpu.usage",
  "metric.type": "gauge",
  "metric.unit": "%"
}
```

`cloudwatch-logs` [#cloudwatch-logs]

Input must contain a top-level `logEvents` array.

For each item in `logEvents[]`, the service inserts one row. The row starts with the log event object itself, then the transform adds top-level CloudWatch fields such as `owner`, `logGroup`, `logStream`, and `messageType`.

Example output row from a CloudWatch log event:

```json
{
  "id": "37199704885633600550210639780",
  "timestamp": 1705312800000,
  "message": "START RequestId: abc-123",
  "owner": "123456789012",
  "logGroup": "/aws/lambda/my-function",
  "logStream": "2024/01/15/[$LATEST]abcdef",
  "messageType": "DATA_MESSAGE"
}
```

`cloudtrail` [#cloudtrail]

Input must contain a top-level `Records` array.

For each item in `Records[]`, the service inserts the CloudTrail record object itself. The transform does not add wrapper fields for this transform.

Example output row from a CloudTrail `GetObject` record:

```json
{
  "eventVersion": "1.08",
  "eventTime": "2024-01-15T10:30:00Z",
  "eventSource": "s3.amazonaws.com",
  "eventName": "GetObject",
  "awsRegion": "us-east-1",
  "sourceIPAddress": "203.0.113.42",
  "userIdentity": { "type": "IAMUser", "userName": "alice" }
}
```

If a flattened OpenTelemetry record attribute has the same key as an existing span, log record, or metric data point field, the transform keeps the existing record field. If the unwrapped record or its flattened attributes already contain a field with the same name as a merged wrapper field, the merged value is the value inserted for that column. For example, OpenTelemetry `scope.name` comes from the scope wrapper, and CloudWatch `logGroup` comes from the top-level wrapper.

AWS output [#aws-output]

The `cloudwatch-logs` transform unwraps `logEvents`. Each emitted row keeps the log event fields and also includes these wrapper fields when present:

| Field         | Description                                |
| ------------- | ------------------------------------------ |
| `owner`       | AWS account owner from the wrapper payload |
| `logGroup`    | CloudWatch log group                       |
| `logStream`   | CloudWatch log stream                      |
| `messageType` | CloudWatch message type                    |

The `cloudtrail` transform unwraps the top-level `Records` array. CloudTrail records are inserted as the emitted rows without additional wrapper fields.

`firehose` [#firehose]

Use `firehose` when AWS Firehose delivers to the service through an HTTP endpoint.

Configure the Firehose endpoint URL with the target table and transform:

```text
https://api.rawtree.com/v1/tables/events?database=analytics&transform=firehose
```

Set the Firehose access key to your cluster API key. The service reads that key from the `X-Amz-Firehose-Access-Key` header.

Each Firehose `records[].data` value must be base64-encoded data. If the decoded value is a JSON object, the service inserts it as one row. If it is an array of JSON objects, the service inserts one row per object. If it is UTF-8 TSV text and `columns` is present, the service inserts one row per TSV line using those column names. If it is UTF-8 TSV text without `columns`, the service inserts one row with the decoded text in a `data` field. Other decoded formats return `400`.

The service returns the Firehose response shape:

```json
{
  "requestId": "firehose-request-id",
  "timestamp": 1710000000000
}
```

Empty results [#empty-results]

A transform can emit zero rows if the input JSON does not contain the expected wrapper arrays. For example, `otlp-traces` requires spans under `resourceSpans` or `scopeSpans`, and `cloudtrail` requires a `Records` array.

If an insert succeeds but inserts fewer rows than expected, check the source shape and query the table with `SELECT * FROM <table> LIMIT 10`.
