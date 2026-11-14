#!/usr/bin/env python3
"""Tiny RawTree query helper (stdlib only, no install needed).

    python3 scripts/rt.py "SELECT count() FROM shop.requests"
    python3 scripts/rt.py -f queries/some.sql          # read SQL from a file
    python3 scripts/rt.py --json "SELECT ..."          # raw JSON rows (one per line)
    python3 scripts/rt.py --stats "SELECT ..."         # also print rows/bytes read + hints
    echo "SELECT 1" | python3 scripts/rt.py -

Reads TEAM_ID / RAWTREE_API_KEY / RAWTREE_API_URL from the environment or the repo's .env.
The literal `team_NN` inside the SQL is replaced by $TEAM_ID, so the starter queries run as-is.
Read-only by default: anything that is not SELECT/WITH/EXPLAIN/DESCRIBE needs --write.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def query(sql: str, timeout: float = 120) -> dict:
    """Run SQL through POST /v1/query and return the full JSON envelope (meta, data, rows, statistics, hints)."""
    load_env()
    api = os.environ.get("RAWTREE_API_URL", "https://api.rawtree.com")
    req = urllib.request.Request(
        f"{api}/v1/query",
        data=json.dumps({"sql": sql}).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['RAWTREE_API_KEY']}",
            "Content-Type": "application/json",
            "User-Agent": "datathon-agent/rt.py",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"HTTP {e.code}: {body}") from None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sql", nargs="?", help="SQL text, or '-' to read it from stdin")
    ap.add_argument("-f", "--file", help="read the SQL from a file")
    ap.add_argument("--json", action="store_true", help="print rows as JSON lines instead of a table")
    ap.add_argument("--stats", action="store_true", help="print statistics and hints to stderr")
    ap.add_argument("--write", action="store_true", help="allow non-read statements (INSERT, CREATE, ALTER, TRUNCATE...)")
    ap.add_argument("--width", type=int, default=60, help="max cell width in table mode (default 60)")
    args = ap.parse_args()

    if args.file:
        sql = Path(args.file).read_text()
    elif args.sql == "-" or args.sql is None:
        sql = sys.stdin.read()
    else:
        sql = args.sql
    load_env()
    sql = sql.strip().rstrip(";").replace("team_NN", os.environ.get("TEAM_ID", "team_NN"))

    body = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    first = body.lstrip("( \n\t").split(None, 1)[0].upper() if body.strip() else ""
    if first not in {"SELECT", "WITH", "EXPLAIN", "DESCRIBE", "DESC"} and not args.write:
        raise SystemExit(f"refusing to run a {first} statement without --write")

    out = query(sql)
    rows = out.get("data", [])
    if args.json:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
    elif rows:
        cols = list(rows[0].keys())
        cells = [[_cell(r.get(c), args.width) for c in cols] for r in rows]
        widths = [max(len(c), *(len(row[i]) for row in cells)) for i, c in enumerate(cols)]
        print("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
        print("  ".join("-" * w for w in widths))
        for row in cells:
            print("  ".join(v.ljust(w) for v, w in zip(row, widths)))
    else:
        print("(no rows)")
    if args.stats:
        print(json.dumps({"rows": out.get("rows"), "statistics": out.get("statistics"), "hints": out.get("hints")}), file=sys.stderr)
    elif out.get("hints"):
        print(f"hints: {json.dumps(out['hints'])}", file=sys.stderr)


def _cell(v, width: int) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= width else s[: width - 1] + "…"


if __name__ == "__main__":
    main()
