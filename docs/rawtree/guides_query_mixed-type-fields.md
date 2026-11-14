# Query fields with mixed types (/docs/guides/query/mixed-type-fields)



Query fields with mixed types [#query-fields-with-mixed-types]

JSON paths can hold different types in different rows. Inspect each type before
you choose a conversion.

Before you begin [#before-you-begin]

* Use the `analytics` database. Create it with the [database API](/docs/reference/api/databases#post-v1databases) if it does not exist.
* Set `RAWTREE_DATABASE` to `analytics` for the API and CLI examples.
* Use an `events` table with a `value` path and a `tags` path.

1\. Inspect the stored types [#1-inspect-the-stored-types]

List each value and its concrete type.

```sql test
SELECT value, dynamicType(value) AS value_type FROM events ORDER BY value_type
```

2\. Convert compatible values [#2-convert-compatible-values]

Convert values to `Int64` when that conversion matches your data.

```sql test
SELECT value::Int64 AS value_number FROM events
```

Use `accurateCastOrNull` when invalid values must return `NULL`.

```sql test
SELECT accurateCastOrNull(value, 'Int64') AS value_number FROM events
```

3\. Extract one exact type [#3-extract-one-exact-type]

Use `.:Int64` to select only values stored as `Int64`.

```sql test
SELECT __raw_data.value.:Int64 AS exact_integer FROM events
```

4\. Inspect arrays [#4-inspect-arrays]

Check the type before you apply array functions.

```sql test
SELECT dynamicType(tags) AS tags_type, tags FROM events
```

When an indexed or sorting-key path uses a cast, check the query plan for index
use. `accurateCastOrNull` and exact-type extraction can prevent that use.

Check the result [#check-the-result]

The `value_type` result shows `Int64` and `String` for the sample values.
The `tags_type` result shows the array type for array values.

Inspect `hints` even when a query succeeds. These runtime type-compatibility
warnings can identify incompatible values that an operation skips or replaces
with `NULL` or a default result.

<SnippetTabs label="Inspect query type warnings">
  <SnippetTab value="API">
    ```bash test
    # Inspect the hints field in the JSON result.
    # With values 42, "42", and null, the total is 42.
    # The warning identifies the String values excluded by sum.
    curl -X POST \
      "https://api.rawtree.com/v1/query?database=$RAWTREE_DATABASE" \
      --header "Authorization: Bearer $RAWTREE_API_KEY" \
      --header "Content-Type: application/json" \
      -d @- <<'JSON'
    {"sql": "SELECT sum(value) AS total FROM events"}
    JSON
    ```
  </SnippetTab>

  <SnippetTab value="CLI">
    ```bash test
    # Inspect the hints field in the JSON result.
    # With values 42, "42", and null, the total is 42.
    # The warning identifies the String values excluded by sum.
    rtree query --database "$RAWTREE_DATABASE" --json \
      "SELECT sum(value) AS total
    FROM events"
    ```
  </SnippetTab>

  <SnippetTab value="SQL">
    ```sql test
    -- Inspect the hints field in the JSON result.
    -- With values 42, "42", and null, the total is 42.
    -- The warning identifies the String values excluded by sum.
    SELECT sum(value) AS total
    FROM analytics.events
    FORMAT JSON;
    ```
  </SnippetTab>
</SnippetTabs>

Use `dynamicType` to inspect the types named in the warning. Choose a conversion
or exact extraction that matches the field's meaning. Count values that the
chosen conversion excludes.

<SnippetTabs label="Convert values and count exclusions">
  <SnippetTab value="API">
    ```bash test
    # Convert numeric strings when they represent numbers.
    # Count non-null values that fail conversion.
    # With values 42, "42", and null, total is 84 and invalid_values is 0.
    curl -X POST \
      "https://api.rawtree.com/v1/query?database=$RAWTREE_DATABASE" \
      --header "Authorization: Bearer $RAWTREE_API_KEY" \
      --header "Content-Type: application/json" \
      -d @- <<'JSON'
    {"sql": "WITH accurateCastOrNull(value, 'Int64') AS number SELECT sum(number) AS total, countIf(value IS NOT NULL AND number IS NULL) AS invalid_values FROM events"}
    JSON
    ```
  </SnippetTab>

  <SnippetTab value="CLI">
    ```bash test
    # Convert numeric strings when they represent numbers.
    # Count non-null values that fail conversion.
    # With values 42, "42", and null, total is 84 and invalid_values is 0.
    rtree query --database "$RAWTREE_DATABASE" --json \
      "WITH accurateCastOrNull(value, 'Int64') AS number
    SELECT
        sum(number) AS total,
        countIf(value IS NOT NULL AND number IS NULL) AS invalid_values
    FROM events"
    ```
  </SnippetTab>

  <SnippetTab value="SQL">
    ```sql test
    -- Convert numeric strings when they represent numbers.
    -- Count non-null values that fail conversion.
    -- With values 42, "42", and null, total is 84 and invalid_values is 0.
    WITH accurateCastOrNull(value, 'Int64') AS number
    SELECT
        sum(number) AS total,
        countIf(value IS NOT NULL AND number IS NULL) AS invalid_values
    FROM analytics.events
    FORMAT JSON;
    ```
  </SnippetTab>
</SnippetTabs>

Some operations can skip incompatible types without a hint.
Use explicit counts to check which values contribute to the result.
See [Runtime type-compatibility warnings](/docs/concepts/dynamic-fields#runtime-type-compatibility-warnings)
for comparison defaults and other limits.

Next steps [#next-steps]

* [Dynamic fields](/docs/concepts/dynamic-fields)
* [Optimize queries](/docs/guides/query/optimize-queries)
