"""Thin RawTree HTTP client shared by the live loop and the offline scripts.

Reads TEAM_ID / RAWTREE_API_KEY / RAWTREE_API_URL from the environment or the repo's .env.
The key is only ever placed in the Authorization header: it is never logged or printed.
"""
from __future__ import annotations

import io
import os
import threading
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_env()
API = os.environ.get("RAWTREE_API_URL", "https://api.rawtree.com")
TEAM = os.environ["TEAM_ID"]
_local = threading.local()


def _http() -> requests.Session:
    """One keep-alive session per thread (requests.Session is not thread-safe)."""
    if not hasattr(_local, "session"):
        s = requests.Session()
        s.headers["Authorization"] = f"Bearer {os.environ['RAWTREE_API_KEY']}"
        _local.session = s
    return _local.session


def query(sql: str, timeout: float = 40) -> list[dict[str, Any]]:
    """Run SQL and return the rows as dicts."""
    r = _http().post(f"{API}/v1/query", json={"sql": sql}, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"query failed: HTTP {r.status_code}: {r.text[:300]}")
    return r.json()["data"]


def query_tsv(sql: str, timeout: float = 60):
    """Run SQL and return a pandas DataFrame (TSV transport: much lighter than JSON for bulk pulls)."""
    import pandas as pd

    r = _http().post(f"{API}/v1/query", json={"sql": sql, "format": "TSVWithNames"}, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"query failed: HTTP {r.status_code}: {r.text[:300]}")
    return pd.read_csv(io.BytesIO(r.content), sep="\t", quoting=3, keep_default_na=False, na_values=["\\N"])


def insert(table: str, rows: list[dict[str, Any]], timeout: float = 5) -> None:
    """Batch insert JSON rows into one of our team tables (submissions, scratch)."""
    r = _http().post(f"{API}/v1/tables/{table}", params={"database": TEAM}, json=rows, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"insert failed: HTTP {r.status_code}: {r.text[:300]}")
