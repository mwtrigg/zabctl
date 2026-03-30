"""
Output formatting for zabctl.

Formats: table, json, jsonl, yaml, wide.
The JSON envelope is the canonical agent format:
  {"data": [...], "meta": {"count": N, "server": "...", "api_version": "...", "command": "..."}}
"""

from __future__ import annotations

import json
import sys
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

VALID_FORMATS = ("table", "json", "jsonl", "yaml", "wide")


def _extract_field(record: dict[str, Any], field_path: str) -> Any:
    """
    Extract a value from a record using a dotted path with optional array index.
    Examples: "host", "interfaces[0].ip"
    """
    parts = field_path.replace("[", ".").replace("]", "").split(".")
    val: Any = record
    for part in parts:
        if val is None:
            return None
        if isinstance(val, list):
            try:
                val = val[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val


def format_output(
    *,
    data: list[dict[str, Any]],
    output_format: str,
    command: str,
    server: str | None,
    api_version: str = "unknown",
    columns: list[str] | None = None,
    wide_columns: list[str] | None = None,
    no_headers: bool = False,
    field: str | None = None,
) -> None:
    """
    Format and print data to stdout.

    Args:
        data: List of record dicts.
        output_format: One of table, json, jsonl, yaml, wide.
        command: The command string for the meta envelope (e.g. "get hosts").
        server: The Zabbix server URL for the meta envelope.
        api_version: The Zabbix API version string.
        columns: Ordered list of column names for table/wide output.
        wide_columns: Additional columns shown only in "wide" mode.
        no_headers: Suppress table headers.
        field: If set, extract this field from each record and print one value per line.
    """
    # --field: extract and print a single field, one value per line
    if field is not None:
        for record in data:
            val = _extract_field(record, field)
            if val is not None:
                print(val)
        return

    if output_format == "json":
        envelope = {
            "data": data,
            "meta": {
                "count": len(data),
                "server": server or "",
                "api_version": api_version,
                "command": command,
            },
        }
        print(json.dumps(envelope, default=str))

    elif output_format == "jsonl":
        for record in data:
            print(json.dumps(record, default=str))

    elif output_format == "yaml":
        envelope = {
            "data": data,
            "meta": {
                "count": len(data),
                "server": server or "",
                "api_version": api_version,
                "command": command,
            },
        }
        print(yaml.dump(envelope, default_flow_style=False, allow_unicode=True), end="")

    elif output_format in ("table", "wide"):
        _format_table(
            data=data,
            output_format=output_format,
            columns=columns or [],
            wide_columns=wide_columns or [],
            no_headers=no_headers,
        )

    else:
        print(
            f"error: unknown output format '{output_format}' — "
            f"use one of: {', '.join(VALID_FORMATS)}",
            file=sys.stderr,
        )
        sys.exit(5)


def _format_table(
    *,
    data: list[dict[str, Any]],
    output_format: str,
    columns: list[str],
    wide_columns: list[str],
    no_headers: bool,
) -> None:
    active_columns = list(columns)
    if output_format == "wide" and wide_columns:
        active_columns = active_columns + wide_columns

    if not active_columns and data:
        active_columns = list(data[0].keys())

    table = Table(show_header=not no_headers, header_style="bold")
    for col in active_columns:
        table.add_column(col)

    for record in data:
        row = [str(_extract_field(record, col) or "") for col in active_columns]
        table.add_row(*row)

    console.print(table)


def format_error(message: str, exit_code: int = 1) -> None:
    """Print an error message to stderr and exit."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(exit_code)
