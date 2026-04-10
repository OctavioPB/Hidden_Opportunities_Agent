"""
Shared base for all data source modules.

Provides the DB query helper and the production annotation decorator
that adds the 'in_production' note to every returned record.
"""

import sqlite3
from typing import Any

import config
from src.db.schema import get_connection


def query(sql: str, params: tuple = ()) -> list[dict]:
    """Run a SELECT and return rows as plain dicts."""
    conn = get_connection()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def annotate(records: list[dict], integration_note: str) -> list[dict]:
    """
    Attach a '_production_integration' key to every record.

    In the UI this is surfaced as the 'In Production' tooltip explaining
    which real API endpoint would provide this data.
    """
    for r in records:
        r["_production_integration"] = integration_note
    return records
