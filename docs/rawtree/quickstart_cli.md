# CLI (/docs/quickstart/cli)



Quickstart with the CLI [#quickstart-with-the-cli]

The `rtree` CLI accesses RawTree through the service API from your terminal.
This quickstart uses RawTree Cloud.

1\) Install [#1-install]

```bash
curl -fsSL https://rawtree.com/install.sh | bash
```

2\) Log in [#2-log-in]

```bash
rtree login
```

```bash test
rtree status
```

In an agent session or another shell without a terminal on stdin, `rtree login`
uses JSON automatically.
It prints a `device_approval_required` event with an approval link to stderr.
It then waits for you to open the link and approve in a browser.
Read that event while the command is running.

After approval, the CLI selects resources automatically when there is only one
choice. Otherwise, it returns JSON with `needs` and the available choices on
stdout, then exits with code `2`. Rerun with the requested flags, or supply all
three if you already know them:

```bash
rtree login --org team-alpha --cluster production --database analytics
```

Each retry requires approval again. Credentials are saved only when login
completes. See the [CLI reference](/docs/reference/cli#authentication) for
the JSON responses.

3\) Create and select a database [#3-create-and-select-a-database]

```bash test
rtree database create analytics
rtree database use analytics
```

4\) Insert data [#4-insert-data]

```bash test
rtree insert --table events \
  --data '[{"action":"click","user":"alice","value":42}]'
```

You can also ingest files and public URLs:

```bash test title="Insert a local JSONL file"
rtree insert --table events --file ./events.jsonl
```

```bash
rtree insert --table events --url https://example.com/events.jsonl
```

5\) Query data [#5-query-data]

```bash test
rtree query "SELECT action, count() AS total FROM events GROUP BY action ORDER BY total DESC LIMIT 10"
```

Next steps [#next-steps]

* [Agents quickstart](/docs/quickstart/agents)
* [CLI reference](/docs/reference/cli)
