# Authentication (/docs/reference/authentication)



Authentication [#authentication]

RawTree Cloud and RawTree BYOC authenticate service API requests with bearer
credentials. The service manages API keys and organization identities. RawTree
uses SQL users, roles, and grants to enforce database access.

```text
Authorization: Bearer rt_...
```

Use `rtree login` for interactive CLI workflows. Use API keys or workload identity federation for agents, scripts, services, and CI.

Credentials across interfaces [#credentials-across-interfaces]

The [OpenAPI specification](https://rawtree.com/openapi.json) lists the service HTTP contracts.
Its security schemes distinguish API keys (`apiKeyAuth`), first-party sessions (`bearerAuth`), and user OAuth (`oauth2`).
A Bearer header can carry different credential types. The method determines which types it accepts.

| Interface                                        | Credentials                                                                    | Scope                                                                                        |
| ------------------------------------------------ | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Service HTTP API                                 | API key, user session, user OAuth, or workload token, as allowed by the method | Data methods and management methods have different permissions                               |
| CLI                                              | `rtree login`, API key, or workload federation                                 | Login creates a first-party user session. API keys and workload tokens remain cluster-scoped |
| TypeScript SDK                                   | API key or a supported access token supplied to the client                     | The SDK uses the HTTP API and inherits its restrictions                                      |
| Hosted MCP                                       | User OAuth, API key, or an MCP-targeted workload token                         | User OAuth can reach the user's resources. Keys and workload tokens select one cluster       |
| Local MCP                                        | Credentials configured for the local server                                    | The underlying HTTP API still checks permissions                                             |
| OTLP/HTTP, Prometheus, and Splunk data endpoints | Credentials accepted by the HTTP data API                                      | App installation and read or write permission are required                                   |
| OTLP/gRPC                                        | Cluster API key                                                                | User sessions, user OAuth, and workload tokens are not accepted                              |
| Direct RawTree connection                        | Database user and its configured authentication method                         | Native database grants and settings apply                                                    |

See [MCP](/docs/reference/mcp), [CLI](/docs/reference/cli), and [TypeScript SDK](/docs/reference/sdk) for client setup.
Service credentials do not become native database passwords. The service resolves the database identity for each request.

User sessions and OAuth [#user-sessions-and-oauth]

The dashboard and `rtree login` use first-party user sessions. These sessions follow the user's organization membership.
An administrator can manage that organization's resources. A member has the access allowed by each method.
The dashboard sends its session cookie. API clients can send the session token in the `Authorization: Bearer` header.
Cookie requests that change state must include an accepted `Origin`.

External clients use OAuth Authorization Code with PKCE (`S256`) and the `full_access` scope.
Use the authorization-server metadata at `https://api.rawtree.com/.well-known/oauth-authorization-server` to discover its endpoints.
OAuth permission remains subject to organization membership and method restrictions.
Billing, identity administration, OAuth grant management, and service-account deletion require a first-party session where enforced.

```bash
# List organizations with a user session or user OAuth access token.
curl -X GET 'https://api.rawtree.com/v1/organizations' \
  -H "Authorization: Bearer $RAWTREE_USER_TOKEN"
```

For data requests with a user token, pass `organization`, `cluster`, and `database` names.
API keys and workload tokens already select an organization and cluster. Their default database can be changed per request.

Create an API key [#create-an-api-key]

```bash
rtree key create --name my-agent --permission read_write
```

Every API key belongs to one organization and one cluster. It is not tied to a
database. For keys created with `permission`, that permission applies to every
current and future database in the cluster. Keys created with `database_roles`
are limited by those roles' grants.

Choose the database on each data-plane request with `?database=<name>` or the
`x-rawtree-database` header. If neither is provided, the service uses the API key's
stored default database. Creating a key stores the database selected on that
request; if no database is selected, the service stores the logical `default`
database. On the shared cluster, the service maps the logical name to the
organization's isolated `rt_<organization_id>_<database>` namespace.

Expiration [#expiration]

Set `expires_at` when calling `POST /v1/keys` to create an expiring key:

```json
{
  "name": "reporting",
  "permission": "read_only",
  "expires_at": "2027-01-01T00:00:00Z"
}
```

The timestamp must be in the future and include a timezone (RFC 3339). Omit
`expires_at` or set it to `null` for a key that never expires. Existing keys have
no expiration. This applies to both permission-based and database-role keys.
Creation and list responses include `expires_at` as a UTC timestamp or `null`.

At or after expiration, new requests fail authentication (HTTP 401 or gRPC
UNAUTHENTICATED), including when the key is cached. Requests already authenticated
may finish. Expired keys remain visible and can be deleted. Expiration is fixed
at creation; create a replacement key to choose a different expiration.

Permissions [#permissions]

| Permission   | List databases | Insert | Query / logs | Delete table | Manage databases | Manage API keys |
| ------------ | -------------: | -----: | -----------: | -----------: | ---------------: | --------------: |
| `admin`      |            Yes |    Yes |          Yes |          Yes |              Yes |             Yes |
| `read_write` |            Yes |    Yes |          Yes |           No |               No |              No |
| `write_only` |             No |    Yes |           No |           No |               No |              No |
| `read_only`  |            Yes |     No |          Yes |           No |               No |              No |

`TRUNCATE TABLE` requires write permission: `admin`, `read_write`, or `write_only`.
It removes all rows while preserving the table. Database-role keys cannot truncate through the Query API.

API keys can read full details for their bound organization and cluster with
`GET /v1/organizations` and `GET /v1/clusters`. Each returns one entry using the
same response schema as user credentials, including organization plan
metadata and cluster status, resources, and storage configuration. Organization
membership `role` is `null` for API keys; users retain their membership role.
User credentials list all accessible resources. An explicit `organization` must
match the API key's organization name.

API keys cannot read account, membership, billing, or cluster-management
endpoints. An `admin` API key can manage databases and API keys in its own cluster.

Existing database roles [#existing-database-roles]

To restrict a key to selected database grants, send `database_roles` instead
of `permission` when creating the key. Use an administrator API key for this request.

```bash
curl -X POST 'https://api.rawtree.com/v1/keys?database=analytics' \
  --header "Authorization: Bearer $RAWTREE_API_KEY" \
  --header "Content-Type: application/json" \
  -d '{"name":"event-pipeline","database_roles":["analytics_reader","events_writer"]}'
```

The response contains the new key's ID and token.

```json
{
  "id": "<key-id>",
  "token": "rt_..."
}
```

Save the `token` value as `ROLE_API_KEY` and the `id` value as `ROLE_KEY_ID`.

Provide exactly one access field. `database_roles` accepts 1–32 distinct names
of roles that already exist on the key's cluster. Assigning roles requires an
organization administrator or an admin API key. Role names are case-sensitive.

The service creates a separate RawTree user for the key and activates those roles
before it returns the token. The role grants determine which databases, tables,
and columns the key can access. Grant changes apply to keys that use those roles.
[Row policies](/docs/concepts/access-control) assigned to those roles filter
the rows they can read; use read-only roles for row-restricted keys.

Select the database on each query request, or use the key's stored default.
This request selects `analytics` explicitly.

```bash
curl -X POST 'https://api.rawtree.com/v1/query?database=analytics' \
  --header "Authorization: Bearer $ROLE_API_KEY" \
  --header "Content-Type: application/json" \
  -d '{"sql":"SELECT action FROM events"}'
```

Database-role keys support SQL reads, query formatting, query cancellation, and inserts into existing tables.
They can discover their organization and cluster, list and describe tables, and list or invoke handlers when database grants allow it.
They do not grant other service management access. Inserts do not automatically create tables.
Role creation and grant management happen separately from key creation.

Custom-key create/list responses contain `database_roles` and omit `permission`.
Permission-based keys continue to use the `permission` field.
Deleting a custom key removes its database user and preserves the assigned roles.

Create a data role through the Query API [#create-a-data-role-through-the-query-api]

Send the role and grant as separate `POST /v1/query` requests. Create the key
with `POST /v1/keys` and `database_roles`. Dropping and recreating a role
removes its grants. See
[restrict an API key](/docs/guides/secure/restrict-api-key-access), the
[access-control concepts](/docs/concepts/access-control), and the
[role and grant references](/docs/reference/sql/statements/role).

Workload identity federation [#workload-identity-federation]

Exchange your provider's signed workload identity token for a short-lived service
access token. No interactive login, client registration, or API key is
needed by the workload.

An organization admin first adds an identity provider under **Identity providers**,
then a federation policy under **Federation policies** on the target cluster. Select
the identity provider, allowed audience, exact claim
conditions, a user or service-account principal, and either an API permission or
existing database roles. Conditions restrict which workloads may authenticate;
they do not filter data rows. Database grants and row policies control data access.

Exchange the assertion at the shared API endpoint:

```bash
curl -X POST "https://api.rawtree.com/oauth/token" \
  --data-urlencode 'grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer' \
  --data-urlencode "federation_rule_id=$RAWTREE_FEDERATION_RULE_ID" \
  --data-urlencode "assertion=$PROVIDER_ID_TOKEN"
```

The response contains `access_token`, `token_type: "Bearer"`, `expires_in` and
`scope`. Use the access token in the `Authorization: Bearer` header on `/v1/query`
and other HTTP API requests permitted by the policy. The policy determines the
organization and cluster, so these are not additional exchange parameters.

Tokens last at most 15 minutes and never outlive the provider assertion. Each
assertion can be exchanged once per identity provider configuration. Obtain a fresh assertion
to renew access or retry a failed exchange; there is no refresh token. Assertions
must include `iss`, `sub`, `aud`, `iat` and `exp`, have a lifetime of at most one
hour, and satisfy every rule condition. Database-role exchanges require more than
30 seconds remaining to provision the database credential.

Disabling, editing or deleting the rule invalidates its existing access tokens.
Editing the identity provider, removing the mapped user from the organization or deleting
the service account also prevents further access. Requests already authenticated
may finish. Workload tokens do not sign into the dashboard or authenticate OTLP gRPC connections.

Workload tokens for hosted MCP [#workload-tokens-for-hosted-mcp]

For hosted MCP, include its resource origin in the exchange:

```bash
# Exchange a fresh provider assertion for an MCP access token.
curl -X POST 'https://api.rawtree.com/oauth/token' \
  --data-urlencode 'grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer' \
  --data-urlencode "federation_rule_id=$RAWTREE_FEDERATION_RULE_ID" \
  --data-urlencode "assertion=$PROVIDER_ID_TOKEN" \
  --data-urlencode 'resource=https://mcp.rawtree.com'
```

Send the returned token as Bearer authentication to `https://mcp.rawtree.com/mcp`.
The resource is the origin, without `/mcp`. If you omit it, the exchange returns an API token that hosted MCP rejects.
The federation rule still controls the principal, cluster, database, and permissions. It does not grant user-level management access.

Test with GitHub Actions [#test-with-github-actions]

Add the GitHub identity provider. It uses the issuer URL
`https://token.actions.githubusercontent.com` with OIDC discovery.
Configure a dedicated rule for the repository and workflow you intend to trust.
Match GitHub's actual `sub` or immutable repository/owner claims; subject formats
can vary between repositories. See [GitHub's OIDC reference](https://docs.github.com/en/actions/reference/security/oidc).

The repository includes a [manual demo workflow](https://github.com/rawtreedb/rawtree-platform/blob/main/.github/workflows/workload-federation-demo.yml)
and its [Python script](https://github.com/rawtreedb/rawtree-platform/blob/main/scripts/workload-federation/github.py).
Copy both into the repository trusted by your rule, or run the workflow in that
repository if they are already present. Configure the `workload-federation-demo` GitHub environment with permitted
branches and variables `RAWTREE_URL`, `RAWTREE_FEDERATION_RULE_ID` and
`RAWTREE_AUDIENCE`. Match the environment subject in your rule. The job requires
`id-token: write`; its destination comes from trusted environment configuration. The script requests a
GitHub token, exchanges it, and runs `SELECT 42 AS value`. It prints the result and
keeps both tokens out of its output. CI runs this same script against a real
GitHub token and the candidate service build.

A 400 `invalid_grant` means the assertion could not be accepted: check the issuer,
audience, required claims, signing keys, expiry and whether it was already used.
A 401 on a subsequent API request indicates an expired or revoked credential.
A permission error means authentication succeeded but the rule or database role
does not allow the requested operation.

Recommendations [#recommendations]

* Use `read_write` for agents that ingest and query.
* Use `read_only` for dashboards, audits, and validation jobs.
* Use `write_only` for event producers.
* Use `admin` only for database lifecycle, key management, and destructive data operations.

Environment variables [#environment-variables]

```bash
export RAWTREE_API_KEY=rt_...
export RAWTREE_DATABASE=analytics
export RAWTREE_ORG=team_alpha
```

The CLI reads `RAWTREE_API_KEY` before saved local credentials.
