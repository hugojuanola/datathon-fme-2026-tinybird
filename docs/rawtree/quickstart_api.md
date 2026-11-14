# API (/docs/quickstart/api)



Quickstart with the API [#quickstart-with-the-api]

Use the service API for HTTP access from an application, script, or agent.
It sends inserts and supported SQL to RawTree. The examples use the same base
URL for RawTree Cloud and RawTree BYOC across regions.

Base URL:

```text
https://api.rawtree.com
```

1\) Set an API key [#1-set-an-api-key]

Create an API key from the UI or CLI, then pass it as a bearer token.

```bash
export API_KEY=rt_...
```

```text
Authorization: Bearer rt_...
```

2\) Ingest data [#2-ingest-data]

```bash test
curl -X POST "https://api.rawtree.com/v1/tables/events" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '[
    {"action":"click","user":"alice","value":42},
    {"action":"view","user":"bob","value":10}
  ]'
```

Native row counters in the response (excerpt):

```json
{ "read_rows": "2", "written_rows": "2" }
```

The response includes the database's summary fields, with counters encoded as
strings. Use `written_rows` for the reported insert count. See the
[insert response reference](/docs/reference/api/tables#post-v1tablestable) for the other fields.

3\) Query data [#3-query-data]

```bash test
curl -X POST "https://api.rawtree.com/v1/query" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT action, count() AS total FROM events GROUP BY action ORDER BY total DESC LIMIT 10"}'
```

4\) Check recent API requests [#4-check-recent-api-requests]

```bash test
START_TIME="2026-04-24T10:00:00Z"
END_TIME="2026-04-24T11:00:00Z"

curl "https://api.rawtree.com/v1/logs?start_time=$START_TIME&end_time=$END_TIME&limit=50" \
  -H "Authorization: Bearer $API_KEY"
```

Next steps [#next-steps]

* [API reference](/docs/reference/api)
* [Authentication](/docs/reference/authentication)
* [Query data](/docs/guides/query/query-data)
