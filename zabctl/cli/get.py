"""
zabctl get commands.

All get subcommands share pipeline flags (--field, --stdin-field, --from-stdin, --batch-size)
and respect the global --output / -o flag from ctx.obj.
"""

from __future__ import annotations

import json
import sys
from itertools import islice
from typing import Any

import click
import httpx

from zabctl.api.client import (
    ZabbixAPIError,
    ZabbixAuthError,
    ZabbixClient,
    ZabbixNotFoundError,
)
from zabctl.api.resources import (
    events,
    groups,
    hosts,
    items,
    problems,
    templates,
    triggers,
    usergroups,
    users,
)
from zabctl.config.loader import ZabctlConfig
from zabctl.output.formatter import format_error, format_output

# Common option sets reused across commands.
_PIPELINE_OPTIONS = [
    click.option("--field", default=None, metavar="PATH", help="Extract one field per record."),
    click.option("--stdin-field", default=None, metavar="NAME", help="Read values from stdin, map to this field."),
    click.option("--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin."),
    click.option("--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out."),
]

_OUTPUT_OPTIONS = [
    click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers."),
    click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format."),
]

_PAGINATION_OPTIONS = [
    click.option("--limit", default=None, type=int, help="Maximum number of records to return."),
    click.option("--sort-by", default=None, metavar="FIELD[:desc]", help="Sort by field (append :desc for descending)."),
    click.option(
        "--filter",
        "extra_filters",
        multiple=True,
        metavar="KEY=VALUE",
        help="Pass extra key=value params directly to the Zabbix API (repeatable).",
    ),
]


def _resolve_output(ctx_output: str, local_output: str | None) -> str:
    return local_output or ctx_output or "table"


def _resolve(cfg: ZabctlConfig, flag: str, explicit: Any, fallback: Any = None) -> Any:
    """Return the first non-None value from: explicit CLI flag → config defaults → fallback."""
    if explicit is not None:
        return explicit
    default = cfg.defaults.get(flag)
    if default is not None:
        return default
    return fallback


def _parse_extra_filters(extra_filters: tuple[str, ...]) -> dict[str, Any]:
    """Parse 'key=value' pairs into a dict. Values are JSON-decoded when possible."""
    result: dict[str, Any] = {}
    for item in extra_filters:
        if "=" not in item:
            raise click.BadParameter(f"--filter must be key=value, got: {item!r}")
        key, _, raw = item.partition("=")
        try:
            result[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            result[key.strip()] = raw
    return result


def _make_client(cfg: ZabctlConfig) -> ZabbixClient:
    """Build and authenticate a ZabbixClient, mapping errors to clean exit codes."""
    client = ZabbixClient(cfg)
    try:
        client.login()
    except ZabbixAuthError as exc:
        format_error(str(exc), exit_code=3)
    except httpx.ConnectError as exc:
        format_error(str(exc), exit_code=4)
    except httpx.TimeoutException:
        format_error(f"Connection to {cfg.server} timed out", exit_code=4)
    return client


def _handle_api_error(exc: Exception) -> None:
    """Map API/network exceptions to clean exit messages."""
    if isinstance(exc, ZabbixNotFoundError):
        format_error(str(exc), exit_code=2)
    elif isinstance(exc, ZabbixAuthError):
        format_error(str(exc), exit_code=3)
    elif isinstance(exc, httpx.ConnectError):
        format_error(str(exc), exit_code=4)
    elif isinstance(exc, httpx.TimeoutException):
        format_error("Request timed out", exit_code=4)
    elif isinstance(exc, ZabbixAPIError):
        format_error(f"Zabbix API error {exc.code}: {exc}", exit_code=1)
    else:
        format_error(str(exc), exit_code=1)


def _read_stdin_lines(from_stdin: bool) -> list[str] | None:
    """Read newline-delimited values from stdin when data is being piped in."""
    if from_stdin or not sys.stdin.isatty():
        return [line.strip() for line in sys.stdin if line.strip()]
    return None


def _batched(iterable: list[str], n: int) -> list[list[str]]:
    it = iter(iterable)
    batches = []
    while batch := list(islice(it, n)):
        batches.append(batch)
    return batches


@click.group("get")
def get() -> None:
    """Retrieve resources from Zabbix."""


# ---------------------------------------------------------------------------
# get hosts
# ---------------------------------------------------------------------------

@get.command("hosts")
@click.option("--group", default=None, help="Filter by host group name.")
@click.option("--status", default=None, type=click.Choice(["monitored", "unmonitored"]), help="Filter by monitoring status.")
@click.option("--search", default=None, help="Search string matched against host name.")
@click.option("--field", default=None, metavar="PATH", help="Extract one field per record.")
@click.option("--stdin-field", default=None, metavar="NAME", help="Read values from stdin, map to this field.")
@click.option("--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin.")
@click.option("--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out.")
@click.option("--limit", default=None, type=int, help="Maximum number of records to return.")
@click.option("--sort-by", default=None, metavar="FIELD[:desc]", help="Sort by a Zabbix field (append :desc for descending). Valid fields vary by resource.")
@click.option("--filter", "extra_filters", multiple=True, metavar="KEY=VALUE", help="Extra Zabbix API params (repeatable).")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def get_hosts(
    cfg: ZabctlConfig,
    group: str | None,
    status: str | None,
    search: str | None,
    field: str | None,
    stdin_field: str | None,
    from_stdin: bool,
    batch_size: int,
    limit: int | None,
    sort_by: str | None,
    extra_filters: tuple[str, ...],
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix hosts."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        extra = _parse_extra_filters(extra_filters)
        data = hosts.get_hosts(
            client,
            group=group,
            status=status,
            search=search,
            limit=_resolve(cfg, "limit", limit),
            sort_by=_resolve(cfg, "sort_by", sort_by),
            extra_params=extra or None,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=data,
        output_format=fmt,
        command="get hosts",
        server=cfg.server,
        api_version=client.api_version,
        columns=["hostid", "host", "name", "status", "interfaces[0].ip"],
        wide_columns=["groups[0].name"],
        no_headers=no_headers,
        field=field,
    )


# ---------------------------------------------------------------------------
# get host <id|name>
# ---------------------------------------------------------------------------

@get.command("host")
@click.argument("id_or_name")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.pass_obj
def get_host(cfg: ZabctlConfig, id_or_name: str, output: str | None, no_headers: bool) -> None:
    """Show a single Zabbix host by id or name."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        data = hosts.get_host(client, id_or_name)
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=[data],
        output_format=fmt,
        command="get host",
        server=cfg.server,
        api_version=client.api_version,
        columns=["host", "name", "status", "interfaces[0].ip", "groups[0].name"],
        no_headers=no_headers,
    )


# ---------------------------------------------------------------------------
# get items <host>
# ---------------------------------------------------------------------------

@get.command("items")
@click.argument("host", required=False)
@click.option("--key", default=None, help="Filter by item key pattern.")
@click.option("--type", "item_type", default=None, help="Filter by item type.")
@click.option("--status", default=None, type=click.Choice(["enabled", "disabled"]), help="Filter by item status.")
@click.option("--field", default=None, metavar="PATH", help="Extract one field per record.")
@click.option("--stdin-field", default=None, metavar="NAME", help="Read values from stdin, map to this field.")
@click.option("--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin.")
@click.option("--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out.")
@click.option("--limit", default=None, type=int, help="Maximum number of records to return.")
@click.option("--sort-by", default=None, metavar="FIELD[:desc]", help="Sort by a Zabbix field (append :desc for descending). Valid fields vary by resource.")
@click.option("--filter", "extra_filters", multiple=True, metavar="KEY=VALUE", help="Extra Zabbix API params (repeatable).")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def get_items(
    cfg: ZabctlConfig,
    host: str | None,
    key: str | None,
    item_type: str | None,
    status: str | None,
    field: str | None,
    stdin_field: str | None,
    from_stdin: bool,
    batch_size: int,
    limit: int | None,
    sort_by: str | None,
    extra_filters: tuple[str, ...],
    no_headers: bool,
    output: str | None,
) -> None:
    """List items for a host."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)

    hostnames = _fan_out_hosts(host, stdin_field, from_stdin)
    if not hostnames:
        format_error("Provide a host argument or pipe hostnames via --stdin-field host", exit_code=5)
        return

    extra = _parse_extra_filters(extra_filters)
    resolved_limit = _resolve(cfg, "limit", limit)
    resolved_sort = _resolve(cfg, "sort_by", sort_by)
    all_data: list[dict[str, Any]] = []
    for batch in _batched(hostnames, batch_size):
        for h in batch:
            try:
                all_data.extend(
                    items.get_items(
                        client,
                        h,
                        key=key,
                        item_type=item_type,
                        status=status,
                        limit=resolved_limit,
                        sort_by=resolved_sort,
                        extra_params=extra or None,
                    )
                )
            except Exception as exc:
                _handle_api_error(exc)
                return

    format_output(
        data=all_data,
        output_format=fmt,
        command="get items",
        server=cfg.server,
        api_version=client.api_version,
        columns=["key_", "name", "lastvalue", "units"],
        wide_columns=["itemid", "type", "status", "lastclock"],
        no_headers=no_headers,
        field=field,
    )


# ---------------------------------------------------------------------------
# get triggers
# ---------------------------------------------------------------------------

@get.command("triggers")
@click.option("--severity", default=None, help="Filter by severity (name or 0–5).")
@click.option("--host", default=None, help="Filter by host name.")
@click.option("--status", default=None, type=click.Choice(["enabled", "disabled"]), help="Filter by trigger status.")
@click.option("--field", default=None, metavar="PATH", help="Extract one field per record.")
@click.option("--stdin-field", default=None, metavar="NAME", help="Read values from stdin, map to this field.")
@click.option("--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin.")
@click.option("--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out.")
@click.option("--limit", default=None, type=int, help="Maximum number of records to return.")
@click.option("--sort-by", default=None, metavar="FIELD[:desc]", help="Sort by a Zabbix field (append :desc for descending). Valid fields vary by resource.")
@click.option("--filter", "extra_filters", multiple=True, metavar="KEY=VALUE", help="Extra Zabbix API params (repeatable).")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def get_triggers(
    cfg: ZabctlConfig,
    severity: str | None,
    host: str | None,
    status: str | None,
    field: str | None,
    stdin_field: str | None,
    from_stdin: bool,
    batch_size: int,
    limit: int | None,
    sort_by: str | None,
    extra_filters: tuple[str, ...],
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix triggers."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        extra = _parse_extra_filters(extra_filters)
        data = triggers.get_triggers(
            client,
            severity=severity,
            host=host,
            status=status,
            limit=_resolve(cfg, "limit", limit),
            sort_by=_resolve(cfg, "sort_by", sort_by),
            extra_params=extra or None,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=data,
        output_format=fmt,
        command="get triggers",
        server=cfg.server,
        api_version=client.api_version,
        columns=["description", "priority", "status", "value", "lastchange"],
        wide_columns=["triggerid", "hosts[0].host"],
        no_headers=no_headers,
        field=field,
    )


# ---------------------------------------------------------------------------
# get alerts
# ---------------------------------------------------------------------------

@get.command("problems")
@click.option("--severity", default=None, help="Filter by severity (name or 0–5).")
@click.option("--host", default=None, help="Filter by host name.")
@click.option("--since", default=None, help="Show problems since this time (ISO 8601 or Unix epoch).")
@click.option("--acknowledged", is_flag=True, default=False, help="Show only acknowledged problems (default: show all).")
@click.option("--field", default=None, metavar="PATH", help="Extract one field per record.")
@click.option("--stdin-field", default=None, metavar="NAME", help="Read values from stdin, map to this field.")
@click.option("--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin.")
@click.option("--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out.")
@click.option("--limit", default=None, type=int, help="Maximum number of records to return.")
@click.option("--sort-by", default=None, metavar="FIELD[:desc]", help="Sort by a Zabbix field (append :desc for descending). Valid fields vary by resource.")
@click.option("--filter", "extra_filters", multiple=True, metavar="KEY=VALUE", help="Extra Zabbix API params (repeatable).")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def get_problems(
    cfg: ZabctlConfig,
    severity: str | None,
    host: str | None,
    since: str | None,
    acknowledged: bool,
    field: str | None,
    stdin_field: str | None,
    from_stdin: bool,
    batch_size: int,
    limit: int | None,
    sort_by: str | None,
    extra_filters: tuple[str, ...],
    no_headers: bool,
    output: str | None,
) -> None:
    """List active problems (Zabbix problems API)."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    ack: bool | None = True if acknowledged else None
    try:
        extra = _parse_extra_filters(extra_filters)
        data = problems.get_alerts(
            client,
            severity=severity,
            host=host,
            since=since,
            acknowledged=ack,
            limit=_resolve(cfg, "limit", limit),
            sort_by=_resolve(cfg, "sort_by", sort_by),
            extra_params=extra or None,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=data,
        output_format=fmt,
        command="get problems",
        server=cfg.server,
        api_version=client.api_version,
        columns=["eventid", "name", "severity", "clock", "acknowledged"],
        wide_columns=["objectid", "r_eventid"],
        no_headers=no_headers,
        field=field,
    )


# ---------------------------------------------------------------------------
# get templates
# ---------------------------------------------------------------------------

@get.command("templates")
@click.option("--search", default=None, help="Search string matched against template name.")
@click.option("--field", default=None, metavar="PATH", help="Extract one field per record.")
@click.option("--limit", default=None, type=int, help="Maximum number of records to return.")
@click.option("--sort-by", default=None, metavar="FIELD[:desc]", help="Sort by a Zabbix field (append :desc for descending). Valid fields vary by resource.")
@click.option("--filter", "extra_filters", multiple=True, metavar="KEY=VALUE", help="Extra Zabbix API params (repeatable).")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def get_templates(
    cfg: ZabctlConfig,
    search: str | None,
    field: str | None,
    limit: int | None,
    sort_by: str | None,
    extra_filters: tuple[str, ...],
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix templates."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        extra = _parse_extra_filters(extra_filters)
        data = templates.get_templates(
            client,
            search=search,
            limit=_resolve(cfg, "limit", limit),
            sort_by=_resolve(cfg, "sort_by", sort_by),
            extra_params=extra or None,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=data,
        output_format=fmt,
        command="get templates",
        server=cfg.server,
        api_version=client.api_version,
        columns=["templateid", "name"],
        wide_columns=["description"],
        no_headers=no_headers,
        field=field,
    )


# ---------------------------------------------------------------------------
# get template <id|name>
# ---------------------------------------------------------------------------

@get.command("template")
@click.argument("id_or_name")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.pass_obj
def get_template(cfg: ZabctlConfig, id_or_name: str, output: str | None, no_headers: bool) -> None:
    """Show a single template by id or name."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        data = templates.get_template(client, id_or_name)
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=[data],
        output_format=fmt,
        command="get template",
        server=cfg.server,
        api_version=client.api_version,
        columns=["templateid", "name", "description"],
        no_headers=no_headers,
    )


# ---------------------------------------------------------------------------
# get latestdata <host>
# ---------------------------------------------------------------------------

@get.command("latestdata")
@click.argument("host", required=False)
@click.option("--stdin-field", default=None, metavar="NAME", help="Read values from stdin, map to this field.")
@click.option("--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin.")
@click.option("--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out.")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def get_latestdata(
    cfg: ZabctlConfig,
    host: str | None,
    stdin_field: str | None,
    from_stdin: bool,
    batch_size: int,
    no_headers: bool,
    output: str | None,
) -> None:
    """Show latest item values for a host."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)

    hostnames = _fan_out_hosts(host, stdin_field, from_stdin)
    if not hostnames:
        format_error("Provide a host argument or pipe hostnames via --stdin-field host", exit_code=5)
        return

    all_data: list[dict[str, Any]] = []
    for batch in _batched(hostnames, batch_size):
        for h in batch:
            try:
                all_data.extend(items.get_latestdata(client, h))
            except Exception as exc:
                _handle_api_error(exc)
                return

    format_output(
        data=all_data,
        output_format=fmt,
        command="get latestdata",
        server=cfg.server,
        api_version=client.api_version,
        columns=["key_", "name", "lastvalue", "units", "lastclock"],
        wide_columns=["itemid", "type"],
        no_headers=no_headers,
    )


# ---------------------------------------------------------------------------
# get groups
# ---------------------------------------------------------------------------

@get.command("groups")
@click.option("--field", default=None, metavar="PATH", help="Extract one field per record.")
@click.option("--limit", default=None, type=int, help="Maximum number of records to return.")
@click.option("--sort-by", default=None, metavar="FIELD[:desc]", help="Sort by a Zabbix field (append :desc for descending). Valid fields vary by resource.")
@click.option("--filter", "extra_filters", multiple=True, metavar="KEY=VALUE", help="Extra Zabbix API params (repeatable).")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def get_groups(
    cfg: ZabctlConfig,
    field: str | None,
    limit: int | None,
    sort_by: str | None,
    extra_filters: tuple[str, ...],
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix host groups."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        extra = _parse_extra_filters(extra_filters)
        data = groups.get_groups(
            client,
            limit=_resolve(cfg, "limit", limit),
            sort_by=_resolve(cfg, "sort_by", sort_by),
            extra_params=extra or None,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=data,
        output_format=fmt,
        command="get groups",
        server=cfg.server,
        api_version=client.api_version,
        columns=["groupid", "name"],
        no_headers=no_headers,
        field=field,
    )


# ---------------------------------------------------------------------------
# get events
# ---------------------------------------------------------------------------

@get.command("events")
@click.option("--host", default=None, help="Filter by host name.")
@click.option("--since", default=None, help="Show events since this time (ISO 8601 or Unix epoch).")
@click.option("--until", default=None, help="Show events until this time (ISO 8601 or Unix epoch).")
@click.option("--limit", default=None, type=int, help="Maximum number of records to return.")
@click.option("--sort-by", default=None, metavar="FIELD[:desc]", help="Sort by a Zabbix field (append :desc for descending). Valid fields vary by resource.")
@click.option("--filter", "extra_filters", multiple=True, metavar="KEY=VALUE", help="Extra Zabbix API params (repeatable).")
@click.option("--field", default=None, metavar="PATH", help="Extract one field per record.")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def get_events(
    cfg: ZabctlConfig,
    host: str | None,
    since: str | None,
    until: str | None,
    limit: int | None,
    sort_by: str | None,
    extra_filters: tuple[str, ...],
    field: str | None,
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix events."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        extra = _parse_extra_filters(extra_filters)
        data = events.get_events(
            client,
            host=host,
            since=since,
            until=until,
            limit=_resolve(cfg, "limit", limit),
            sort_by=_resolve(cfg, "sort_by", sort_by),
            extra_params=extra or None,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=data,
        output_format=fmt,
        command="get events",
        server=cfg.server,
        api_version=client.api_version,
        columns=["eventid", "clock", "name", "severity", "value"],
        wide_columns=["source", "object", "objectid", "acknowledged"],
        no_headers=no_headers,
        field=field,
    )


# ---------------------------------------------------------------------------
# get users
# ---------------------------------------------------------------------------

@get.command("users")
@click.option("--field", default=None, metavar="PATH", help="Extract one field per record.")
@click.option("--limit", default=None, type=int, help="Maximum number of records to return.")
@click.option("--sort-by", default=None, metavar="FIELD[:desc]", help="Sort by a Zabbix field (append :desc for descending). Valid fields vary by resource.")
@click.option("--filter", "extra_filters", multiple=True, metavar="KEY=VALUE", help="Extra Zabbix API params (repeatable).")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def get_users(
    cfg: ZabctlConfig,
    field: str | None,
    limit: int | None,
    sort_by: str | None,
    extra_filters: tuple[str, ...],
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix users."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        extra = _parse_extra_filters(extra_filters)
        data = users.get_users(
            client,
            limit=_resolve(cfg, "limit", limit),
            sort_by=_resolve(cfg, "sort_by", sort_by),
            extra_params=extra or None,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=data,
        output_format=fmt,
        command="get users",
        server=cfg.server,
        api_version=client.api_version,
        columns=["userid", "username", "name", "surname"],
        wide_columns=["roleid", "usrgrps[0].name"],
        no_headers=no_headers,
        field=field,
    )


# ---------------------------------------------------------------------------
# get user <id|name>
# ---------------------------------------------------------------------------

@get.command("user")
@click.argument("id_or_name")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.pass_obj
def get_user(cfg: ZabctlConfig, id_or_name: str, output: str | None, no_headers: bool) -> None:
    """Show a single Zabbix user by id or username."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        data = users.get_user(client, id_or_name)
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=[data],
        output_format=fmt,
        command="get user",
        server=cfg.server,
        api_version=client.api_version,
        columns=["userid", "username", "name", "surname", "roleid"],
        wide_columns=["usrgrps[0].name"],
        no_headers=no_headers,
    )


# ---------------------------------------------------------------------------
# get usergroups
# ---------------------------------------------------------------------------

@get.command("usergroups")
@click.option("--field", default=None, metavar="PATH", help="Extract one field per record.")
@click.option("--limit", default=None, type=int, help="Maximum number of records to return.")
@click.option("--sort-by", default=None, metavar="FIELD[:desc]", help="Sort by a Zabbix field (append :desc for descending). Valid fields vary by resource.")
@click.option("--filter", "extra_filters", multiple=True, metavar="KEY=VALUE", help="Extra Zabbix API params (repeatable).")
@click.option("--no-headers", is_flag=True, default=False, help="Suppress table headers.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def get_usergroups(
    cfg: ZabctlConfig,
    field: str | None,
    limit: int | None,
    sort_by: str | None,
    extra_filters: tuple[str, ...],
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix user groups."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        extra = _parse_extra_filters(extra_filters)
        data = usergroups.get_usergroups(
            client,
            limit=limit,
            sort_by=sort_by,
            extra_params=extra or None,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return
    format_output(
        data=data,
        output_format=fmt,
        command="get usergroups",
        server=cfg.server,
        api_version=client.api_version,
        columns=["usrgrpid", "name", "gui_access", "users_status"],
        wide_columns=["users[0].username"],
        no_headers=no_headers,
        field=field,
    )


# ---------------------------------------------------------------------------
# Stdin / pipeline helpers
# ---------------------------------------------------------------------------

def _fan_out_hosts(
    host_arg: str | None,
    stdin_field: str | None,
    from_stdin: bool,
) -> list[str]:
    """Return a list of hostnames from the CLI arg or from stdin."""
    if stdin_field or from_stdin or not sys.stdin.isatty():
        lines = _read_stdin_lines(from_stdin=True)
        if lines:
            return lines
    if host_arg:
        return [host_arg]
    return []
