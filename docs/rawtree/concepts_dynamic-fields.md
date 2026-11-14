# Dynamic fields (/docs/concepts/dynamic-fields)



Dynamic fields [#dynamic-fields]

A JSON leaf path in a raw table normally has the `Dynamic` type. Each row
retains a concrete value type at that path. One row can contain a number,
another a string, and another no value.

This flexibility removes the need to choose one column type before ingestion.
It also makes the intended meaning of a field part of query design. The number
`42` and the string `"42"` need not mean the same thing.

<a id="inspect-stored-types" />

Stored types and missing values [#stored-types-and-missing-values]

`dynamicType` identifies the concrete type for a value.

```sql test
SELECT value, dynamicType(value) AS value_type FROM events ORDER BY value_type
```

A known path absent from a row and an explicit JSON `null` both read as `NULL`.
An entirely unknown path produces `UNKNOWN_IDENTIFIER`. These are different
situations: missing data in a known field is not a missing field definition.

A `Dynamic` wrapper is not an ordinary nullable column. For presence checks,
`countIf(value IS NOT NULL)` expresses the intended count. `count(value)` can
count the wrapper even when its stored value is null. `count()` counts rows.

<a id="convert-or-extract-a-type" />

Conversion and exact extraction [#conversion-and-exact-extraction]

A cast converts compatible values to a chosen type. For example, a numeric
string can participate in a numeric calculation after conversion.

```sql test
SELECT value::Int64 AS value_number FROM events
```

A strict cast can fail for incompatible values. It can also convert a missing
value to a target default, such as zero or an empty string. Those defaults can
create false matches or combine unrelated rows in a group.

Exact extraction selects one stored type instead of converting other types.
A stored numeric string does not become an integer through this expression:

```sql test
SELECT __raw_data.value.:Int64 AS exact_integer FROM events
```

A nonmatching type returns `NULL` when the target supports nulls. Some targets
that cannot be nullable return their default instead. Exact extraction and
conversion therefore answer different questions.

`accurateCastOrNull` expresses tolerant conversion. It returns `NULL` for
incompatible or out-of-range values, so the query can handle them explicitly.

```sql test
SELECT accurateCastOrNull(value, 'Int64') AS value_number FROM events
```

Comparisons, grouping, and ordering [#comparisons-grouping-and-ordering]

Operations on dynamic fields can dispatch by concrete type. A comparison that
works for numeric variants need not interpret string variants numerically.
A successful comparison is not proof that every type participated as intended.

Grouping and distinct operations do not supply a universal conversion rule.
Compatible numeric variants can normalize, while a numeric value and its
string representation remain different values. A shared business identity
requires an explicit common type.

Ordering also depends on the stored types and engine behavior. A mixed field
does not automatically define a useful business order. Numeric scores, dates,
and identifiers need the appropriate conversion before sorting or aggregation.
Null placement is a separate choice.

<a id="arrays-and-nulls" />

Joins and arrays [#joins-and-arrays]

Dynamic join keys are disabled by default. Converting both sides to the same
concrete type makes their intended relationship explicit. Missing or invalid
keys need separate handling, since converting both to an empty string can
create false matches.

Array values retain element types. A field can contain arrays in some rows and
scalars or nulls in others.

```sql test
SELECT dynamicType(tags) AS tags_type, tags FROM events
```

Array operations can omit incompatible variants. An empty array also produces
no rows in an ordinary `ARRAY JOIN`. These outcomes affect row counts, not just
formatting.

<a id="hints-and-performance" />

Runtime type-compatibility warnings [#runtime-type-compatibility-warnings]

Query hints are runtime type-compatibility warnings. They report cases where
RawTree skips incompatible `Dynamic` values or substitutes `NULL` or default
results while continuing execution.

Scalar functions emit hints when they handle an incompatible concrete type.
For example, `length(value)` can return `NULL` for integer values while
processing strings. With `dynamic_throw_on_type_mismatch = 0`, the default,
the function uses `NULL` or its defined default for supported mismatch cases.
Set `dynamic_throw_on_type_mismatch = 1` to raise an exception for those scalar
mismatches. This setting does not control aggregate skipping.

Numeric/string comparisons can also produce hints. With the default setting,
comparing a string value to a number returns `false` for equality and ordering
comparisons, but `true` for `!=`. A message about skipped rows does not always
mean the result excludes those rows. A `SELECT` expression can retain the row
with a default result, while a `WHERE` condition can exclude it.

Aggregates can skip types that their signatures do not support. For values
`1`, `2`, `3`, `"hello"`, and `"world"`, `sum(value)` returns `6` and `avg(value)`
returns `2`. Each emits a hint about incompatible `String` values.
`count(value)` accepts those types and returns `5` without a hint.
Missing values and ordinary `NULL` handling do not themselves produce these warnings.

Some aggregate paths with multiple arguments can skip incompatible types
without a hint. An absent hint does not prove that every value contributed
to the result. Inspect the stored types and choose whether to convert values,
select one type, or count excluded values explicitly.

The JSON result exposes warnings in its optional `hints` field.
Query logging also records them in `system.query_log.hints`.
See [Query response format](/docs/reference/api/query#query-response-format) for the
field contract and [Query fields with mixed types](/docs/guides/query/mixed-type-fields#check-the-result)
for examples.

Type conversion and performance [#type-conversion-and-performance]

Conversion can also affect index use. The correct type semantics come first.
The query plan and execution statistics then show whether a predicate can skip
data. No general rule says that every cast disables optimization.

Related [#related]

* [Raw tables](/docs/concepts/raw-tables)
* [Queries and results](/docs/concepts/queries-and-results)
* [Query fields with mixed types](/docs/guides/query/mixed-type-fields)
* [Optimize queries](/docs/guides/query/optimize-queries)
