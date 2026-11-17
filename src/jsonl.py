"""
Shared JSONL log helpers.

Every demo-mode integration (email, Slack, CRM, WhatsApp, calendar…) appends
records to a `logs/*.jsonl` file and reads them back for the UI. These two
functions are the single implementation of that pattern.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one record to a JSONL file, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path: Path, newest_first: bool = False) -> list[dict[str, Any]]:
    """
    Return all records of a JSONL file (oldest first by default).
    A missing file yields []; blank or corrupt lines are skipped.
    """
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if newest_first:
        records.reverse()
    return records
