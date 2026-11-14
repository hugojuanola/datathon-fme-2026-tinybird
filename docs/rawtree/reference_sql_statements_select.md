# SELECT (/docs/reference/sql/statements/select)



SELECT [#select]

The Query API accepts read queries that start with `SELECT` or `WITH`. Each
request contains one statement. It also accepts selected write and management
statements. See [SQL statements](/docs/reference/sql/statements) for those forms.
These interface limits are separate from RawTree's full SQL capabilities.

Syntax [#syntax]

```sql
SELECT <expressions> [FROM <table>] [WHERE <condition>]
  [GROUP BY <expressions>] [ORDER BY <expressions>] [LIMIT <number>]
```

```sql
WITH <expression> AS <name>
SELECT <expressions>
```

The Query API also accepts top-level `EXPLAIN` and `DESCRIBE` statements. See
their references for examples.

Examples [#examples]

Return a scalar value.

```sql test
SELECT 1 AS value
```

Use a common table expression.

```sql test
WITH 1 AS value SELECT value
```

`SHOW` statements are not accepted by the Query API.

```sql test expect-error="Unsupported query."
SHOW TABLES
```

Related [#related]

* [Optimize queries](/docs/guides/query/optimize-queries)
* [EXPLAIN](/docs/reference/sql/statements/explain)
* [DESCRIBE](/docs/reference/sql/statements/describe)
