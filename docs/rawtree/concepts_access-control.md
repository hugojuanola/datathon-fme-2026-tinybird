# Access control (/docs/concepts/access-control)



Access control [#access-control]

RawTree separates identity from permission. An identity answers who acts.
A credential proves that identity or carries delegated access. Authorization
determines which operations and data that credential can use.

Users, roles, grants, row policies, and settings profiles are RawTree database
constructs inherited from ClickHouse. SQL statements define them, and the
database enforces them during query execution.

RawTree Cloud and RawTree BYOC add sign-in, organization membership, service
accounts, API keys, and workload federation. The service connects these
identities and credentials to database permissions.

Organization membership, database roles, and workload settings have different
purposes. Access to one layer does not imply control of every other layer.

Human access and organization membership [#human-access-and-organization-membership]

A signed-in user acts through a session. User OAuth access tokens delegate
access to an application, subject to the grant and supported routes.
Organization membership determines which organization resources the user can
reach. The `admin` and `member` membership levels govern platform operations.

Organization membership is separate from a database role. An organization
administrator can manage members and cluster configuration. A database role
contains SQL privileges, such as permission to read a table.

A database role does not make its holder an organization administrator.
Conversely, a row policy assigned to one database role does not restrict every
signed-in user.

API keys and service accounts [#api-keys-and-service-accounts]

An API key belongs to an organization and a cluster. Its stored default
database is a fallback for requests, not a restriction to that database.
The service supports two access models for keys:

| Access model         | Permission boundary                                                                       |
| -------------------- | ----------------------------------------------------------------------------------------- |
| Permission-based key | A cluster-wide permission such as `read_only`, `write_only`, `read_write`, or `admin`.    |
| Database-role key    | Existing database roles whose grants determine accessible databases, tables, and columns. |

An admin API key can manage supported database resources and keys in its
cluster. It does not become a user session or gain organization, membership,
billing, or cluster-management access.

A service account is an organization-owned identity for automation. It can own
API keys and act as the principal of a workload federation rule. Its keys use
their own permissions or database roles. Ownership does not expand those rights.

Service-account keys survive removal of the human who created them. Deleting
the service account revokes its keys. Personal keys instead depend on the
owner's organization membership. Credential lifecycle and data permissions
are separate considerations.

Workload identity federation [#workload-identity-federation]

Federation exchanges a trusted provider's signed workload identity for a
short-lived service access token. An organization administrator defines the
issuer and a cluster rule with allowed audiences, claim conditions, and access.

The rule selects a user or service account and either a permission level or
existing database roles. Its conditions determine which workloads can
authenticate. They do not filter table rows.

A workload token uses the rule's organization and cluster. It does not provide
a dashboard session or authenticate hosted MCP and OTLP gRPC connections.
See [Authentication](/docs/reference/authentication#workload-identity-federation)
for supported transports and token lifecycle.

Query identity in the database [#query-identity-in-the-database]

For queries submitted through the service, the credential determines the database
user. RawTree enforces that user's grants.

| Credential                                 | Database identity                                                                                                                                  |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Signed-in user session or user OAuth token | `user:<user UUID>`, shared by that person's reads and writes.                                                                                      |
| API key with database roles                | `api_key:<key UUID>`, with the key's assigned roles.                                                                                               |
| Permission-based API key                   | Shared organization users: `ro_<organization ID>` for Query API reads and `rw_<organization ID>` for writes. Hyphens in the ID become underscores. |

A service account's API key follows the same mapping as other keys.
Key ownership does not create a separate database user for the service account.

Inspect query identity [#inspect-query-identity]

`system.query_log` records the database user in `user`. For distributed execution,
`initial_user` identifies the database user who submitted the original query.
With a permission-based key, `user` alone cannot identify the key or its owner.
The API key list exposes ownership through `principal_type` and `principal_id`.

Workload federation selects database permissions through its rule. For these
requests, `system.query_log.log_comment` can include the user or service-account
attribution. Organization-owned workflows use organization database users and
record the workflow and run IDs in `log_comment`.

Set `RAWTREE_DATABASE` to the database you use for queries.

<SnippetTabs label="Inspect query identities">
  <SnippetTab value="API">
    ```bash test
    # Inspect the database identities of recent completed queries on this replica.
    # Query log entries can appear after a short delay.
    curl -X POST "https://api.rawtree.com/v1/query?database=$RAWTREE_DATABASE" \
      -H "Authorization: Bearer $RAWTREE_API_KEY" \
      -H "Content-Type: application/json" \
      -d @- <<'JSON'
    {"sql": "SELECT event_time, user, initial_user, query_id FROM system.query_log WHERE event_time >= now() - INTERVAL 1 HOUR AND type = 'QueryFinish' AND is_initial_query = 1 ORDER BY event_time DESC, query_id LIMIT 20"}
    JSON
    ```
  </SnippetTab>

  <SnippetTab value="CLI">
    ```bash test
    # Inspect the database identities of recent completed queries on this replica.
    # Query log entries can appear after a short delay.
    rtree query --database "$RAWTREE_DATABASE" --api-url https://api.rawtree.com --json \
      "SELECT event_time, user, initial_user, query_id FROM system.query_log WHERE event_time >= now() - INTERVAL 1 HOUR AND type = 'QueryFinish' AND is_initial_query = 1 ORDER BY event_time DESC, query_id LIMIT 20"
    ```
  </SnippetTab>

  <SnippetTab value="SQL">
    ```sql test
    -- Inspect the database identities of recent completed queries on this replica.
    -- Query log entries can appear after a short delay.
    SELECT event_time, user, initial_user, query_id
    FROM system.query_log
    WHERE event_time >= now() - INTERVAL 1 HOUR
      AND type = 'QueryFinish'
      AND is_initial_query = 1
    ORDER BY event_time DESC, query_id
    LIMIT 20;
    ```
  </SnippetTab>
</SnippetTabs>

<a id="roles-and-grants" />

Database roles and grants [#database-roles-and-grants]

The service provisions a database user for each database-role API key and
assigns its selected roles. RawTree enforces those roles' grants and policies.
The service manages this database user even though the Query API does not accept
`CREATE USER`. The service account or user account that owns the key remains a
separate service identity.

A role is a named set of database privileges. Grants can give it access to
selected tables or columns. Multiple keys can use the same role, and changes
to its grants affect those keys.

Database-role keys use existing roles. They do not receive privileged access
repair or automatic table-creation rights. Their grants authorize database
operations, not platform management or metadata APIs.

The public Query API supports a restricted set of role and grant statements.
It does not support `REVOKE`. The
[role reference](/docs/reference/sql/statements/role) and
[grant reference](/docs/reference/sql/statements/grant) define the supported forms.

Row policies [#row-policies]

Row policies filter `SELECT` results for existing database roles. Matching
permissive policies combine with **OR**. Matching restrictive policies combine
with **AND**. A restrictive policy needs a matching permissive policy before
it can return rows.

> Apply policies to every role that requires row filtering. A policy assigned
> to one role does not restrict permission-based keys, user sessions, or other
> roles. Readers without a matching policy can retain their existing access.

The engine configuration `users_without_row_policies_can_read_rows` controls
behavior for readers without a policy. It is an operator setting, not a
permission assigned by creating a policy. Policies filter reads.
They do not constrain inserts or protect data from callers who can modify it.
Read-only roles are the appropriate basis for restricted readers.

<a id="settings-profiles" />

Settings profiles and workloads [#settings-profiles-and-workloads]

A settings profile supplies defaults and constraints for selected settings on
named database roles. It can assign a `workload` or set
`use_concurrency_control`. `READONLY` and `CONST` constrain setting changes.
A profile does not grant table access.

[Workload scheduling](/docs/concepts/workload-scheduling) controls competition
for server resources. It complements access control: the permission to execute
a query and the resources it can use are separate decisions.

Which control solves which problem? [#which-control-solves-which-problem]

| Problem                                          | Use                         |
| ------------------------------------------------ | --------------------------- |
| Give an app broad read or write access           | A permission-based API key  |
| Grant a key access to selected tables or columns | A database role and `GRANT` |
| Filter rows for one role                         | A row policy                |
| Choose or lock a role's workload                 | A settings profile          |
| Limit work competing for server resources        | Workload scheduling         |

<a id="next-steps" />

Related [#related]

* [Resource model](/docs/concepts/resource-model)
* [Authentication](/docs/reference/authentication)
* [Restrict an API key](/docs/guides/secure/restrict-api-key-access)
* [Apply row-level security](/docs/guides/secure/row-level-security)
* [Assign a workload with a settings profile](/docs/guides/operate/settings-profiles)
