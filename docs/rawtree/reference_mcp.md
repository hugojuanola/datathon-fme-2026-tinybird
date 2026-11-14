# MCP server (/docs/reference/mcp)



MCP server [#mcp-server]

MCP is an open protocol that lets AI applications use external tools.
RawTree Cloud offers a hosted MCP server. An open-source package also supports local servers.
Use them to query and ingest data, inspect tables and logs, or manage database and service resources.

Hosted MCP server [#hosted-mcp-server]

RawTree Cloud hosts a Streamable HTTP MCP server at:

```text
https://mcp.rawtree.com/mcp
```

You do not need to install anything or run a local process.
When you connect, your MCP client opens the RawTree Cloud sign-in page.
Sign in and approve access with OAuth.
You do not need to create or copy an API key.

Codex [#codex]

```bash
codex mcp add rawtree --url https://mcp.rawtree.com/mcp
```

Codex prompts you to complete OAuth when it first connects. You can also start the flow explicitly with `codex mcp login rawtree`.

Claude Code [#claude-code]

```bash
claude mcp add --transport http rawtree https://mcp.rawtree.com/mcp
```

Run `/mcp` in Claude Code and select `rawtree` to complete OAuth.

Claude [#claude]

In Claude web or desktop, open **Settings > Connectors > Add custom connector** and enter:

```text
https://mcp.rawtree.com/mcp
```

Cursor [#cursor]

Open the command palette and choose **Cursor Settings > MCP > Add new global MCP server**.

```json
{
  "mcpServers": {
    "rawtree": {
      "url": "https://mcp.rawtree.com/mcp"
    }
  }
}
```

For another OAuth-capable client, add the endpoint as a remote or Streamable HTTP MCP server.
The client discovers the service's authorization server automatically.

<a id="choose-rawtree-resources" />

Choose database and service resources [#choose-database-and-service-resources]

One OAuth connection works across every organization, cluster, and database your service identity can access.
Each tool call sets its resource context; the MCP URL does not:

* Organization tools take `organization`.
* Cluster tools take `organization` and a cluster name or ID, depending on the operation.
* Data, table, log, and API-key tools take `organization` and `cluster`. `database` is optional and uses the cluster's default database when omitted.

Start with `list-organizations`.
Then use `list-clusters` and `list-databases` to find the names available to the signed-in user.

The OAuth connection grants broad service access, including destructive operations.
Tools that delete, provision, or change resources require explicit confirmation when supported.
Revoke the connection at any time from **Profile > OAuth apps**.

Available tools [#available-tools]

The server exposes database and service operations. The service API enforces the signed-in user's membership and resource access on every call.

| Area             | Tools                                                                                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Data             | `run-query`, `insert-json`, `insert-from-url`                                                                                                           |
| Tables and logs  | `list-tables`, `create-table`, `describe-table`, `delete-table`, `list-logs`                                                                            |
| Databases        | `list-databases`, `delete-database`                                                                                                                     |
| Organizations    | `list-organizations`, `list-organization-members`, `add-organization-member`, `update-organization-member`, `remove-organization-member`                |
| Clusters         | `list-clusters`, `get-cluster`, `list-cluster-sizes`, `verify-cluster-s3-access`, `create-cluster`, `update-cluster`, `pause-cluster`, `resume-cluster` |
| Apps             | `list-apps`, `install-app`, `uninstall-app`                                                                                                             |
| API keys         | `list-api-keys`, `create-api-key`, `delete-api-key`                                                                                                     |
| Service accounts | `list-service-accounts`, `create-service-account`                                                                                                       |

Service accounts [#service-accounts]

`list-service-accounts` and `create-service-account` require an explicit
`organization` name and an OAuth connection for an organization admin. API keys
cannot manage service accounts. No cluster or database is required.

Creation takes a `name`, optional `description`, and optional `role` (`member` by
default, or `admin`). Names are immutable and unique within the organization:
use 1–128 lowercase letters or digits separated by single hyphens. Descriptions
accept up to 2000 UTF-8 bytes without null characters. Creation returns an
identity without credentials; API key permissions are configured separately.
Listing returns the account IDs, organization IDs, names, descriptions, and roles.

Hosted MCP with an API key [#hosted-mcp-with-an-api-key]

Browser login may not be available for a server, CI job, or headless agent.
In these cases, send a service API key as a Bearer token instead of using OAuth.

Create a key with the least permission that fits the task:

```bash
rtree key create --name mcp --permission read_write
```

| Task                                           | Permission   |
| ---------------------------------------------- | ------------ |
| Query data, inspect tables, and read logs      | `read_only`  |
| Insert and query data                          | `read_write` |
| Insert only                                    | `write_only` |
| Manage databases or API keys, or delete tables | `admin`      |

Claude Code [#claude-code-1]

```bash
claude mcp add --transport http rawtree https://mcp.rawtree.com/mcp \
  --header "Authorization: Bearer rt_xxxxxxxxx"
```

API-key calls may omit `organization`, `cluster`, and `database`.
Omitted values use the key's bound cluster and default database.
Explicit resource values must match the key's binding.
User-level tools such as `list-organizations` require OAuth.

Local MCP server [#local-mcp-server]

The hosted server uses the open-source [`@rawtree/mcp`](https://github.com/rawtreedb/rawtree-mcp) package from npm.
Run the package locally if your client cannot connect to a hosted MCP server.
You can also run it locally to develop the server.
Local clients authenticate with a service API key.

Claude Code [#claude-code-2]

```bash
claude mcp add rawtree \
  -e RAWTREE_API_KEY=rt_xxxxxxxxx \
  -- npx -y @rawtree/mcp
```

Codex [#codex-1]

```bash
codex mcp add rawtree \
  --env RAWTREE_API_KEY=rt_xxxxxxxxx \
  -- npx -y @rawtree/mcp
```

The package also supports self-hosted Streamable HTTP. See the [RawTree MCP repository](https://github.com/rawtreedb/rawtree-mcp) for server options and development setup.

Next steps [#next-steps]

* [Agents quickstart](/docs/quickstart/agents)
* [Ingest data](/docs/guides/ingest/ingest-data)
* [Query data](/docs/guides/query/query-data)
* [Authentication](/docs/reference/authentication)
