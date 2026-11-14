# SQL statements (/docs/reference/sql/statements)



SQL statements [#sql-statements]

These pages describe the SQL interface exposed by RawTree Cloud and RawTree
BYOC. RawTree has a broader SQL model than this API permits. See
[ClickHouse compatibility and API scope](/docs/reference/clickhouse-compatibility).

`POST /v1/query` accepts one SQL statement per request. Access-control and
scheduling statements require an administrator API key. Select the target
database with the request's database selection; row policies use that selected
database when their table is unqualified.

Supported statement families [#supported-statement-families]

| Statement                                                              | Reference                                                            |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `CREATE ROLE`, `DROP ROLE`                                             | [Role](/docs/reference/sql/statements/role)                          |
| `GRANT SELECT`, `GRANT INSERT`                                         | [Grant](/docs/reference/sql/statements/grant)                        |
| `CREATE ROW POLICY`, `DROP ROW POLICY`                                 | [Row policy](/docs/reference/sql/statements/row-policy)              |
| `CREATE SETTINGS PROFILE`, `DROP SETTINGS PROFILE`                     | [Settings profile](/docs/reference/sql/statements/settings-profile)  |
| `CREATE WORKLOAD`, `DROP WORKLOAD`, `CREATE RESOURCE`, `DROP RESOURCE` | [Workload](/docs/reference/sql/statements/workload)                  |
| `SELECT`, `WITH`                                                       | [SELECT](/docs/reference/sql/statements/select)                      |
| `EXPLAIN`                                                              | [EXPLAIN](/docs/reference/sql/statements/explain)                    |
| `DESCRIBE`                                                             | [DESCRIBE](/docs/reference/sql/statements/describe)                  |
| `ALTER TABLE`                                                          | [ALTER TABLE](/docs/reference/sql/statements/alter-table)            |
| `CREATE NAMED COLLECTION`                                              | [Named collections](/docs/reference/sql/statements/named-collection) |
| `KILL MUTATION`                                                        | [KILL MUTATION](/docs/reference/sql/statements/kill-mutation)        |
| `CREATE TABLE`                                                         | [CREATE TABLE](/docs/reference/sql/statements/create-table)          |
| `INSERT ... SELECT`                                                    | [INSERT ... SELECT](/docs/reference/sql/statements/insert-select)    |

The parser validates supported forms before the service sends them to RawTree.
Unsupported forms return a client error with a hint for the accepted grammar.

Related [#related]

* [Access-control concepts](/docs/concepts/access-control)
* [Workload scheduling concepts](/docs/concepts/workload-scheduling)
