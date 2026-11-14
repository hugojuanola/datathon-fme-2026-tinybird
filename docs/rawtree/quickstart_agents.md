# Agents (/docs/quickstart/agents)



Quickstart for agents [#quickstart-for-agents]

Use this page when a coding agent, terminal agent, or CI worker needs to operate RawTree without extra context.

Fastest path: hosted MCP [#fastest-path-hosted-mcp]

For an interactive agent, connect the RawTree Cloud hosted MCP server and sign in with OAuth. No API key or local process is required.

```bash
codex mcp add rawtree --url https://mcp.rawtree.com/mcp
```

Use `https://mcp.rawtree.com/mcp` as a remote or Streamable HTTP server in other MCP clients.
See the [MCP server reference](/docs/reference/mcp) for setup instructions for Claude Code, Claude, Cursor, headless clients, and local servers.

CLI and unattended agents [#cli-and-unattended-agents]

Use the CLI path when OAuth browser login is unavailable or the agent needs to run without interaction.

1\) Install the RawTree skill [#1-install-the-rawtree-skill]

Install the RawTree skill to give your agent CLI, API, SQL, logs, and error-handling patterns.

```bash
npx skills add rawtreedb/agent-skills
```

2\) Provide credentials [#2-provide-credentials]

Use a cluster-wide API key when OAuth browser login is unavailable, such as in CI or another unattended environment.
Create the key in cluster settings in the [RawTree Cloud dashboard](https://rawtree.com/login) or with the CLI:

```bash
rtree key create --name my-agent --permission read_write
```

See [CLI reference / API keys](/docs/reference/cli#api-keys) for the full key commands.

Prefer the least permission that can complete the job.

```bash
export RAWTREE_API_KEY=rt_...
export RAWTREE_DATABASE=analytics
export RAWTREE_ORG=team_alpha
```

Recommended permissions:

| Task                                           | Permission   |
| ---------------------------------------------- | ------------ |
| Insert and query data                          | `read_write` |
| Insert only                                    | `write_only` |
| Query and inspect logs                         | `read_only`  |
| Manage databases or API keys, or delete tables | `admin`      |

3\) Verify context [#3-verify-context]

```bash
rtree status --json
```

The response includes the resolved database, organization, authentication state, and dashboard URL.

4\) Ingest data [#4-ingest-data]

```bash
rtree insert --table events \
  --data '[{"action":"click","user":"alice"},{"action":"view","user":"bob"}]' \
  --json
```

Tables are created automatically when data is inserted for the first time.

5\) Query with SQL [#5-query-with-sql]

```bash
rtree query --json \
  "SELECT action, count() AS total FROM events GROUP BY action ORDER BY total DESC LIMIT 10"
```

Start with read queries and use `LIMIT` while iterating. The Query API also
accepts selected write and management statements with the required permissions.
See [SQL statements](/docs/reference/sql/statements).

6\) Check API request logs [#6-check-api-request-logs]

Use `GET /v1/logs` or the platform Logs screen to inspect request paths, HTTP
statuses, timing, client source, and structured errors. Use the Queries screen
for SQL execution history.

Starter prompt [#starter-prompt]

```text
You are operating a RawTree database.

Use the configured RawTree MCP tools. If MCP is unavailable, use
RAWTREE_API_KEY, RAWTREE_DATABASE, and RAWTREE_ORG from the environment.

Goals:
1. Ingest the provided data into table "events".
2. Query the table with read-only SQL.
3. Use LIMIT while exploring data.
4. Check service request logs from the last hour if insert or query fails.
5. Return the commands you ran and the final result.
```

Next steps [#next-steps]

* [Ingest data](/docs/guides/ingest/ingest-data)
* [Query data](/docs/guides/query/query-data)
* [MCP server](/docs/reference/mcp)
* [CLI reference](/docs/reference/cli)
