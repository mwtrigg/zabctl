"""Shared utilities for Zabbix API resource modules."""

from __future__ import annotations

import datetime


def parse_time(value: str) -> int:
    """Parse an ISO 8601 string or Unix epoch string to an integer timestamp."""
    value = value.strip()
    if value.isdigit():
        return int(value)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(value, fmt).replace(tzinfo=datetime.UTC)
            return int(dt.timestamp())
        except ValueError:
            continue
    raise ValueError(f"Cannot parse time: {value!r}")


def parse_sort(sort_by: str) -> tuple[str, str]:
    """Parse 'field' or 'field:desc' into (field, ORDER)."""
    if ":" in sort_by:
        field, order = sort_by.rsplit(":", 1)
        return field, order.upper()
    return sort_by, "ASC"
