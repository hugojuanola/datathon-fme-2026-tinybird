# CLI (/docs/reference/cli)



CLI reference [#cli-reference]

The `rtree` CLI accesses RawTree through the RawTree Cloud or RawTree BYOC service API.

Install [#install]

```bash
curl -fsSL https://rawtree.com/install.sh | bash
```

Common options [#common-options]

The root command and subcommands accept these options:

| Option                | Description                                  |
| --------------------- | -------------------------------------------- |
| `--api-key <API_KEY>` | Override the saved key or `RAWTREE_API_KEY`. |
| `--api-url <API_URL>` | Override the saved URL or `RAWTREE_API_URL`. |
| `--org <ORG>`         | Select an organization.                      |
| `--cluster <CLUSTER>` | Select a cluster.                            |
| `--json`              | Print machine-readable output.               |
| `-h`, `--help`        | Print command help.                          |

The root command also accepts `-v` and `--version`. The `--database` option is
available only on commands that use a database.

Environment variables [#environment-variables]

| Variable           | Description           |
| ------------------ | --------------------- |
| `RAWTREE_API_KEY`  | API key or JWT.       |
| `RAWTREE_API_URL`  | API URL.              |
| `RAWTREE_ORG`      | Default organization. |
| `RAWTREE_CLUSTER`  | Default cluster.      |
| `RAWTREE_DATABASE` | Default database.     |

An explicit option takes priority over its environment variable. The environment
variable takes priority over saved configuration.

Commands [#commands]

Authentication [#authentication]

| Command        | Arguments and command-specific options                                 |
| -------------- | ---------------------------------------------------------------------- |
| `rtree login`  | `--no-browser`, `--timeout-seconds <SECONDS>`, `--database <DATABASE>` |
| `rtree logout` | —                                                                      |
| `rtree status` | —                                                                      |

`rtree login` starts device approval. Use `--no-browser` to print the approval
link without opening it. `--timeout-seconds` sets the wait time. The default is
300 seconds.

Use `--api-key` to save an API key without device approval. Use `--org`,
`--cluster`, and `--database` to save resource defaults.

When standard input is not a terminal, login prints JSON automatically. Use
`--json` to select JSON output explicitly. Other commands need `--json` for JSON
output.

Browser login writes an event to standard error before it polls for approval:

```json
{"event":"device_approval_required","verification_uri":"<approval page>","verification_uri_complete":"<approval link>","user_code":"ABCD-EFGH","expires_in":600}
```

Open `verification_uri_complete` to approve the request. If a resource selection
has multiple choices, login prints a JSON response and exits with code `2`:

```json
{"needs":"org","orgs":["team-alpha","team-beta"]}
{"needs":"cluster","organization":"team-alpha","clusters":["production","staging"]}
{"needs":"database","organization":"team-alpha","cluster":"production","databases":["analytics","billing"]}
```

Repeat login with the requested option. Keep the values selected in earlier
steps. A successful login writes its result to standard output.

Databases [#databases]

| Command                 | Arguments |
| ----------------------- | --------- |
| `rtree database list`   | —         |
| `rtree database create` | `<NAME>`  |
| `rtree database use`    | `<NAME>`  |
| `rtree database delete` | `<NAME>`  |

`database use` sets the default database. `database delete` deletes that
database and its data.

API keys [#api-keys]

| Command            | Arguments and command-specific options                                                                              |
| ------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `rtree key list`   | —                                                                                                                   |
| `rtree key create` | Required: `--name <NAME>`, `--permission <PERMISSION>`; optional: `--database <DATABASE>`, `--expires-at <RFC3339>` |
| `rtree key delete` | `<ID_OR_TOKEN>`                                                                                                     |

Key permissions are `admin`, `read_write`, `write_only`, and `read_only`.
`--database` sets the new key's default database. Omit `--expires-at` for a key
that does not expire.

Organizations [#organizations]

| Command                     | Arguments          |
| --------------------------- | ------------------ |
| `rtree organization list`   | —                  |
| `rtree organization create` | `<NAME>`           |
| `rtree organization use`    | `<NAME>`           |
| `rtree organization rename` | `<OLD> <NEW_NAME>` |
| `rtree organization delete` | `<NAME>`           |

Clusters [#clusters]

| Command                | Arguments and command-specific options                                                                                                                                     |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rtree cluster list`   | —                                                                                                                                                                          |
| `rtree cluster sizes`  | —                                                                                                                                                                          |
| `rtree cluster create` | Required: `--name <NAME>`, `--replicas <REPLICAS>`, `--min-size <CPU_CORES:MEMORY_GIB>`; optional: `--max-size <CPU_CORES:MEMORY_GIB>`, `--idle-timeout-minutes <MINUTES>` |
| `rtree cluster use`    | `<NAME>`                                                                                                                                                                   |
| `rtree cluster status` | `<NAME_OR_ID>`                                                                                                                                                             |
| `rtree cluster update` | `<NAME_OR_ID>`; optional: `--name <NAME>`, `--idle-timeout-minutes <MINUTES>`                                                                                              |
| `rtree cluster stop`   | `<NAME_OR_ID>`                                                                                                                                                             |
| `rtree cluster resume` | `<NAME_OR_ID>`                                                                                                                                                             |
| `rtree cluster delete` | `<NAME_OR_ID>`                                                                                                                                                             |

Tables [#tables]

| Command                | Arguments and command-specific options                                                |
| ---------------------- | ------------------------------------------------------------------------------------- |
| `rtree table list`     | Optional: `--database <DATABASE>`                                                     |
| `rtree table describe` | `<TABLE>`; optional: `--database <DATABASE>`                                          |
| `rtree table create`   | `<TABLE>`; optional: `--database <DATABASE>`, `--sorting-key <SORTING_KEY>`           |
| `rtree table update`   | `<TABLE>`; required: `--sorting-key <SORTING_KEY>`; optional: `--database <DATABASE>` |

The sorting key is a comma-separated list of SQL expressions. Quote it in the
shell when it contains shell metacharacters.

Workflows [#workflows]

| Command                  | Arguments and command-specific options                                                                                                                                                          |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rtree workflow list`    | —                                                                                                                                                                                               |
| `rtree workflow get`     | `<ID>`                                                                                                                                                                                          |
| `rtree workflow create`  | Required: `--name <NAME>`, `--sql <SQL>`; optional: `--database <DATABASE>`, `--interval-seconds` accepts seconds or `null`, `--disabled`, repeatable `--sink <JSON>`                           |
| `rtree workflow update`  | `<ID>`; optional: `--name <NAME>`, `--sql <SQL>`, `--database <DATABASE>`, `--interval-seconds` accepts seconds or `null`, `--enable`, `--disable`, repeatable `--sink <JSON>`, `--clear-sinks` |
| `rtree workflow delete`  | `<ID>`                                                                                                                                                                                          |
| `rtree workflow run`     | `<ID>`; optional: `--idempotency-key <KEY>`                                                                                                                                                     |
| `rtree workflow runs`    | `<ID>`; optional: `--limit <LIMIT>`, `--cursor <CURSOR>`                                                                                                                                        |
| `rtree workflow cancel`  | `<ID> <RUN_ID>`                                                                                                                                                                                 |
| `rtree workflow logs`    | `<ID>`; optional: `--since`, `--until`, `--start-time`, `--end-time`, `--limit`, `--cursor`                                                                                                     |
| `rtree workflow metrics` | `<ID>`; optional: `--since`, `--until`, `--start-time`, `--end-time`                                                                                                                            |

Use either a relative time such as `1h` or RFC 3339 timestamps for workflow
logs and metrics. Use `--enable` or `--disable` to change a workflow's state.
Use `--clear-sinks` to remove all sinks.

Logs [#logs]

`rtree logs` accepts these filters:

* `--search`, `--methods`, `--status-codes`, `--levels`, `--sources`
* `--user-agent`, `--host`, `--paths`
* `--min-duration-ms`, `--max-duration-ms`
* `--since`, `--until`, `--start-time`, `--end-time`
* `--limit`, `--offset`

Query and format [#query-and-format]

| Command        | Arguments and command-specific options                                                                         |
| -------------- | -------------------------------------------------------------------------------------------------------------- |
| `rtree query`  | Optional `[SQL]`, `--sql <SQL>` or `-q` (alias `--query`); optional `--database <DATABASE>`, `--limit <LIMIT>` |
| `rtree format` | Optional `[SQL]`, `--sql <SQL>` or `-q` (alias `--query`); optional `--database <DATABASE>`                    |

Use `-` as the SQL value to read from standard input. `query --limit` appends a
`LIMIT` clause.

```bash test
rtree query "SELECT 1"
```

```bash test
rtree format "SELECT 1"
```

Service accounts [#service-accounts]

Organization admins can create and list service accounts after `rtree login`:

```bash
rtree service-account create build-jobs --org team-alpha --description "CI workloads"
rtree service-account create deployment --org team-alpha --role admin
rtree service-account list --org team-alpha --json
```

The role defaults to `member`. Names are immutable and unique within the
organization: use 1–128 lowercase letters or digits separated by single hyphens.
Descriptions accept up to 2000 UTF-8 bytes without null characters.

These commands use the usual organization selection and require no cluster or
database. API keys cannot create or list service accounts. Creation returns an
identity without credentials; API key permissions are configured separately.
With `--json`, creation returns the account object and listing returns
`{"service_accounts":[...]}`.

Insert [#insert]

`rtree insert` requires `--table <TABLE>` and one of these data sources:

| Option          | Description                                  |
| --------------- | -------------------------------------------- |
| `--data <DATA>` | Inline JSON data.                            |
| `--file <FILE>` | A JSON or JSONL file.                        |
| `--url <URL>`   | A public URL that serves JSON or JSONL data. |

Use `--database <DATABASE>` to select the database. Use `--transform <TRANSFORM>`
to apply a predefined transform. See [Transforms](/docs/guides/transform/transforms)
for supported names and input shapes.

Utilities [#utilities]

| Command             | Arguments and command-specific options |
| ------------------- | -------------------------------------- |
| `rtree ping`        | Check server connectivity.             |
| `rtree docs`        | Fetch and display API documentation.   |
| `rtree open`        | Optional: `--database <DATABASE>`      |
| `rtree update`      | Update the CLI to the latest release.  |
| `rtree completions` | `<SHELL>`                              |
| `rtree help`        | Optional: `<COMMAND>`                  |

Related [#related]

* [API reference](/docs/reference/api)
* [Authentication](/docs/reference/authentication)
