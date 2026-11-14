# Optimize queries (/docs/guides/query/optimize-queries)



Optimize queries [#optimize-queries]

Measure query work before you change a query. Compare equivalent results on the
same data.

Query best practices [#query-best-practices]

Use this checklist before you run a query on a large table.

* [Select only the paths that the result needs](#1-select-only-required-paths).
* [Add time or key filters when the result needs a subset](#2-add-a-time-filter).
* [Add `LIMIT` while you explore rows](#3-bound-exploratory-queries).
* [Aggregate data in SQL before you return rows to a client](#4-aggregate-before-you-return-rows).
* [Add `ORDER BY` when row order matters](#3-bound-exploratory-queries).
* [Use `EXPLAIN indexes = 1` to inspect index use](#5-inspect-index-use).
* [Compare `statistics.rows_read` and `statistics.bytes_read` for equivalent queries](#6-compare-query-statistics).
* [Check `dynamicType` when a path contains mixed types](#check-mixed-types).

Before you begin [#before-you-begin]

* Use the `analytics` database. Create it with the [database API](/docs/reference/api/databases#post-v1databases) if it does not exist.
* Use a `requests` table with `event_time`, `service`, and `duration_ms` paths.
* Send `event_time` as Unix time in seconds.

1\. Select only required paths [#1-select-only-required-paths]

Name the paths that the result needs.

```sql test
SELECT service, duration_ms FROM requests LIMIT 20
```

2\. Add a time filter [#2-add-a-time-filter]

Filter on a time range to reduce the rows that the query reads.

```sql test
SELECT count() FROM requests WHERE event_time >= toUnixTimestamp(now() - INTERVAL 1 DAY)
```

3\. Bound exploratory queries [#3-bound-exploratory-queries]

Use `LIMIT` while you inspect rows. Add `ORDER BY` when row order matters.

```sql test
SELECT service, duration_ms FROM requests ORDER BY event_time DESC LIMIT 100
```

4\. Aggregate before you return rows [#4-aggregate-before-you-return-rows]

Group data in SQL instead of returning every event to the client.

```sql test
SELECT service, count() AS requests, avg(duration_ms) AS mean_duration FROM requests GROUP BY service ORDER BY requests DESC LIMIT 20
```

5\. Inspect index use [#5-inspect-index-use]

Use `EXPLAIN indexes = 1` to inspect the plan.

```sql test
EXPLAIN indexes = 1 SELECT count() FROM requests WHERE event_time >= toUnixTimestamp(now() - INTERVAL 1 DAY)
```

6\. Compare query statistics [#6-compare-query-statistics]

Compare `statistics.rows_read` and `statistics.bytes_read` for equivalent
filtered and unfiltered queries.

Check mixed types [#check-mixed-types]

Use `dynamicType` to inspect a field before you compare, sort, or aggregate mixed values.
Choose a conversion or exact extraction that matches the field's meaning.
Inspect `hints` for runtime type-compatibility warnings about values that an operation skips or replaces.

See [Query fields with mixed types](/docs/guides/query/mixed-type-fields) for examples of type inspection, conversion, and warning checks.

Check the result [#check-the-result]

The filtered query must read fewer rows than the unfiltered query.
The verifier compares the `rows_read` values.

Next steps [#next-steps]

* [Sorting keys](/docs/concepts/sorting-keys)
* [Query data](/docs/guides/query/query-data)
* [Dynamic fields](/docs/concepts/dynamic-fields)
