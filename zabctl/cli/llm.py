"""
zabctl llm command group — agent bootstrapping and discoverability.

All output from this group is always JSON, regardless of the global --output setting.
Agents should call `zabctl llm capabilities` on first use.
"""

from __future__ import annotations

import json

import click

from zabctl import __version__
from zabctl.config.loader import ZabctlConfig


@click.group("llm")
def llm() -> None:
    """Agent interface — self-describing command surface (output is always JSON)."""


@llm.command("capabilities")
@click.pass_obj
def llm_capabilities(cfg: ZabctlConfig) -> None:
    """Return the full command surface as JSON for agent bootstrapping."""
    _pagination_flags = [
        {"name": "--limit", "description": "Maximum number of records to return"},
        {"name": "--sort-by", "description": "Sort by a Zabbix field for this resource (e.g. field, field:desc for descending). Valid fields vary by resource — check the Zabbix API docs for the method's sortfield parameter."},
        {"name": "--filter", "description": "Extra Zabbix API key=value param (repeatable escape hatch)"},
    ]

    payload = {
        "version": __version__,
        "commands": [
            {
                "name": "get hosts",
                "description": "List Zabbix hosts",
                "flags": [
                    {"name": "--group", "description": "Filter by host group name"},
                    {"name": "--status", "description": "Filter by monitoring status (monitored|unmonitored)"},
                    {"name": "--search", "description": "Search string matched against host name"},
                    *_pagination_flags,
                ],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": True,
                "stdin_accepts": None,
            },
            {
                "name": "get host <id|name>",
                "description": "Show a single Zabbix host by id or technical name",
                "flags": [],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": False,
                "stdin_accepts": None,
                "note": "Single-object lookup; does not accept piped ids yet (planned)",
            },
            {
                "name": "get items <host>",
                "description": "List items for a host",
                "flags": [
                    {"name": "--key", "description": "Filter by item key pattern"},
                    {"name": "--type", "description": "Filter by item type (numeric)"},
                    {"name": "--status", "description": "Filter by item status (enabled|disabled)"},
                    *_pagination_flags,
                ],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": True,
                "stdin_accepts": "host",
            },
            {
                "name": "get triggers",
                "description": "List Zabbix triggers",
                "flags": [
                    {"name": "--severity", "description": "Filter by severity (not_classified|information|warning|average|high|disaster or 0–5)"},
                    {"name": "--host", "description": "Filter by host name"},
                    {"name": "--status", "description": "Filter by trigger status (enabled|disabled)"},
                    *_pagination_flags,
                ],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": True,
                "stdin_accepts": None,
            },
            {
                "name": "get problems",
                "description": "List active problems (Zabbix problem.get — the live problem list, not the event log)",
                "flags": [
                    {"name": "--severity", "description": "Filter by severity (not_classified|information|warning|average|high|disaster or 0–5)"},
                    {"name": "--host", "description": "Filter by host name"},
                    {"name": "--since", "description": "Show problems since this time (ISO 8601 or Unix epoch)"},
                    {"name": "--acknowledged", "description": "Show only acknowledged problems (default: show all, both acknowledged and unacknowledged)"},
                    *_pagination_flags,
                ],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": True,
                "stdin_accepts": None,
            },
            {
                "name": "get templates",
                "description": "List Zabbix templates",
                "flags": [
                    {"name": "--search", "description": "Search string matched against template name"},
                    *_pagination_flags,
                ],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": True,
                "stdin_accepts": None,
            },
            {
                "name": "get template <id|name>",
                "description": "Show a single template by id or name",
                "flags": [],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": False,
                "stdin_accepts": None,
                "note": "Single-object lookup; does not accept piped ids yet (planned)",
            },
            {
                "name": "get latestdata <host>",
                "description": "Show the most recent value for every monitored item on a host",
                "flags": [*_pagination_flags],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": True,
                "stdin_accepts": "host",
            },
            {
                "name": "get groups",
                "description": "List Zabbix host groups",
                "flags": [*_pagination_flags],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": True,
                "stdin_accepts": None,
            },
            {
                "name": "get events",
                "description": "List Zabbix events (raw event log — use get problems for the live active-problem list)",
                "flags": [
                    {"name": "--host", "description": "Filter by host name"},
                    {"name": "--since", "description": "Show events since this time (ISO 8601 or Unix epoch)"},
                    {"name": "--until", "description": "Show events until this time (ISO 8601 or Unix epoch)"},
                    *_pagination_flags,
                ],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": True,
                "stdin_accepts": None,
            },
            {
                "name": "get users",
                "description": "List Zabbix users",
                "flags": [*_pagination_flags],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": True,
                "stdin_accepts": None,
            },
            {
                "name": "get user <id|username>",
                "description": "Show a single Zabbix user by userid or username",
                "flags": [],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": False,
                "stdin_accepts": None,
                "note": "Single-object lookup; does not accept piped ids yet (planned)",
            },
            {
                "name": "get usergroups",
                "description": "List Zabbix user groups",
                "flags": [*_pagination_flags],
                "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
                "pipeable": True,
                "stdin_accepts": None,
            },
            {
                "name": "auth login",
                "description": "Authenticate to the Zabbix server and verify connectivity",
                "flags": [
                    {"name": "--username", "description": "Zabbix username (overrides config/env)"},
                    {"name": "--password", "description": "Zabbix password"},
                ],
                "output_formats": ["table"],
                "pipeable": False,
                "stdin_accepts": None,
            },
            {
                "name": "auth logout",
                "description": "Invalidate the current session token (no-op for API token auth)",
                "flags": [],
                "output_formats": ["table"],
                "pipeable": False,
                "stdin_accepts": None,
            },
            {
                "name": "auth status",
                "description": "Show current authentication configuration and test live connectivity",
                "flags": [],
                "output_formats": ["table"],
                "pipeable": False,
                "stdin_accepts": None,
            },
            {
                "name": "context list",
                "description": "List all configured contexts",
                "flags": [],
                "output_formats": ["table"],
                "pipeable": False,
                "stdin_accepts": None,
            },
            {
                "name": "context use <name>",
                "description": "Switch the active context in the config file",
                "flags": [],
                "output_formats": ["table"],
                "pipeable": False,
                "stdin_accepts": None,
            },
        ],
        "pipeline_flags": {
            "--field": "Extract a single field from jsonl output for piping (e.g. host, interfaces[0].ip)",
            "--stdin-field": "Field name to map stdin records to for this command",
            "--from-stdin": "Explicitly read input records from stdin (bypasses TTY detection)",
            "--batch-size": "When fanning out from stdin, group into batches for API efficiency (default: 10)",
        },
        "exit_codes": {
            "0": "success",
            "1": "general error",
            "2": "not found",
            "3": "auth failure",
            "4": "connection error",
            "5": "invalid arguments",
        },
        "notes": [
            "All output is machine-parseable — prefer --output json or jsonl for agent use.",
            "Agents: call 'zabctl llm capabilities' on first use to discover commands.",
            "Token auth (ZABCTL_API_TOKEN env var) is preferred for automation.",
            "Exit codes are stable across versions.",
        ],
    }
    print(json.dumps(payload, indent=2))


@llm.command("pipeline")
@click.pass_obj
def llm_pipeline(cfg: ZabctlConfig) -> None:
    """Return pipeline composition patterns and examples as JSON."""
    payload = {
        "description": "zabctl supports Unix-style pipelining without jq or external tools.",
        "flags": {
            "--field PATH": {
                "description": "Extract one field from each jsonl record; output is newline-delimited values.",
                "example": "zabctl get hosts -o jsonl --field host",
                "path_syntax": "Supports dot notation and array indexing: host, interfaces[0].ip",
            },
            "--stdin-field NAME": {
                "description": "Read newline-delimited values from stdin and map each to this field name for lookup.",
                "example": "zabctl get hosts -o jsonl --field host | zabctl get items --stdin-field host",
            },
            "--from-stdin": {
                "description": "Explicitly read jsonl records from stdin (bypasses TTY detection; recommended for agent use).",
            },
            "--batch-size N": {
                "description": "Group stdin values into batches of N for API efficiency.",
                "default": 10,
            },
        },
        "tty_detection": (
            "If stdin is not a TTY, zabctl automatically reads it as jsonl. "
            "Use --from-stdin to force this behaviour in agent contexts where TTY state is ambiguous."
        ),
        "examples": [
            {
                "description": "Get all items for every host in a group",
                "command": "zabctl get hosts --group 'Linux Servers' -o jsonl --field host | zabctl get items --stdin-field host",
            },
            {
                "description": "Get latest data for hosts matching a search",
                "command": "zabctl get hosts --search web -o jsonl --field host | zabctl get latestdata --stdin-field host",
            },
            {
                "description": "Acknowledge all active critical problems",
                "command": "zabctl get problems --severity critical -o jsonl --field eventid | zabctl acknowledge --stdin-field eventid --message 'Auto-ack by agent'",
            },
            {
                "description": "Extract just IPs from hosts for external tooling",
                "command": "zabctl get hosts -o jsonl --field interfaces[0].ip",
            },
        ],
    }
    print(json.dumps(payload, indent=2))


@llm.command("schema")
@click.argument("command_path", metavar="COMMAND")
@click.pass_obj
def llm_schema(cfg: ZabctlConfig, command_path: str) -> None:
    """Return the output schema for a command (e.g. 'get hosts')."""
    schemas: dict[str, object] = {
        "get hosts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hostid": {"type": "string"},
                    "host": {"type": "string", "description": "Technical host name"},
                    "name": {"type": "string", "description": "Visible host name"},
                    "status": {
                        "type": "string",
                        "enum": ["0", "1"],
                        "description": "0=monitored, 1=unmonitored",
                    },
                    "interfaces": {"type": "array", "items": {"type": "object"}},
                    "groups": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
        "get items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "itemid": {"type": "string"},
                    "hostid": {"type": "string"},
                    "key_": {"type": "string"},
                    "name": {"type": "string"},
                    "lastvalue": {"type": "string"},
                    "lastclock": {
                        "type": "string",
                        "description": "Unix timestamp of last value",
                    },
                    "units": {"type": "string"},
                    "type": {"type": "string"},
                    "status": {"type": "string", "enum": ["0", "1"]},
                },
            },
        },
        "get triggers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "triggerid": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "description": "0=not classified … 5=disaster",
                    },
                    "status": {"type": "string"},
                    "value": {"type": "string", "description": "0=ok, 1=problem"},
                    "lastchange": {"type": "string"},
                    "hosts": {"type": "array"},
                },
            },
        },
        "get problems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "eventid": {"type": "string"},
                    "objectid": {"type": "string", "description": "Trigger id"},
                    "severity": {"type": "string", "description": "0=not classified … 5=disaster"},
                    "name": {"type": "string"},
                    "clock": {"type": "string", "description": "Unix timestamp"},
                    "acknowledged": {"type": "string", "enum": ["0", "1"], "description": "0=no, 1=yes"},
                    "hosts": {"type": "array"},
                },
            },
        },
        "get groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "groupid": {"type": "string"},
                    "name": {"type": "string"},
                },
            },
        },
        "get events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "eventid": {"type": "string"},
                    "source": {"type": "string"},
                    "object": {"type": "string"},
                    "objectid": {"type": "string"},
                    "clock": {"type": "string", "description": "Unix timestamp"},
                    "value": {"type": "string"},
                    "acknowledged": {"type": "string"},
                    "name": {"type": "string"},
                    "severity": {"type": "string"},
                },
            },
        },
    }

    if command_path not in schemas:
        import sys

        available = list(schemas.keys())
        print(
            json.dumps(
                {
                    "error": f"unknown command '{command_path}'",
                    "available": available,
                }
            )
        )
        sys.exit(5)

    print(
        json.dumps({"command": command_path, "schema": schemas[command_path]}, indent=2)
    )
