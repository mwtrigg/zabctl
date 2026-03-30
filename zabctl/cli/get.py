"""
zabctl get commands.

All get subcommands share pipeline flags (--field, --stdin-field, --from-stdin, --batch-size)
and respect the global --output / -o flag from ctx.obj.

Phase 0: stubs — commands are wired up and flags are defined, but no API calls are made.
The commands print a stub notice and exit 0.
"""

from __future__ import annotations

import click

from zabctl.config.loader import ZabctlConfig
from zabctl.output.formatter import format_output

# Pipeline flags are added to every get subcommand via this decorator helper.
_PIPELINE_OPTIONS = [
    click.option(
        "--field",
        default=None,
        metavar="PATH",
        help="Extract one field per record (e.g. host, interfaces[0].ip).",
    ),
    click.option(
        "--stdin-field",
        default=None,
        metavar="NAME",
        help="Read values from stdin, map to this field for lookup.",
    ),
    click.option(
        "--from-stdin",
        is_flag=True,
        default=False,
        help="Explicitly read jsonl records from stdin.",
    ),
    click.option(
        "--batch-size",
        default=10,
        show_default=True,
        help="Batch size when fanning out from stdin.",
    ),
    click.option(
        "--no-headers", is_flag=True, default=False, help="Suppress table headers."
    ),
    click.option(
        "--output",
        "-o",
        default=None,
        type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
        help="Output format (overrides global).",
    ),
]


def _add_pipeline_options(cmd: click.Command) -> click.Command:
    for opt in reversed(_PIPELINE_OPTIONS):
        cmd = opt(cmd)  # type: ignore[arg-type]
    return cmd


def _resolve_output(ctx_output: str, local_output: str | None) -> str:
    return local_output or ctx_output or "table"


def _stub_output(
    cfg: ZabctlConfig,
    command: str,
    output: str | None,
    no_headers: bool,
    field: str | None,
) -> None:
    """Phase 0: emit an empty result set with a stub notice on stderr."""
    resolved = _resolve_output(cfg.output, output)
    click.echo(f"[stub] {command} — no API call yet (Phase 0)", err=True)
    format_output(
        data=[],
        output_format=resolved,
        command=command,
        server=cfg.server,
        no_headers=no_headers,
        field=field,
    )


@click.group("get")
def get() -> None:
    """Retrieve resources from Zabbix."""


# ---------------------------------------------------------------------------
# get hosts
# ---------------------------------------------------------------------------


@get.command("hosts")
@click.option("--group", default=None, help="Filter by host group name.")
@click.option(
    "--status",
    default=None,
    type=click.Choice(["monitored", "unmonitored"]),
    help="Filter by monitoring status.",
)
@click.option("--search", default=None, help="Search string matched against host name.")
@click.option(
    "--field", default=None, metavar="PATH", help="Extract one field per record."
)
@click.option(
    "--stdin-field",
    default=None,
    metavar="NAME",
    help="Read values from stdin, map to this field.",
)
@click.option(
    "--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin."
)
@click.option(
    "--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out."
)
@click.option(
    "--no-headers", is_flag=True, default=False, help="Suppress table headers."
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format.",
)
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
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix hosts."""
    _stub_output(cfg, "get hosts", output, no_headers, field)


# ---------------------------------------------------------------------------
# get host <id|name>
# ---------------------------------------------------------------------------


@get.command("host")
@click.argument("id_or_name")
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format.",
)
@click.pass_obj
def get_host(cfg: ZabctlConfig, id_or_name: str, output: str | None) -> None:
    """Show a single Zabbix host by id or name."""
    _stub_output(cfg, "get host", output, False, None)


# ---------------------------------------------------------------------------
# get items <host>
# ---------------------------------------------------------------------------


@get.command("items")
@click.argument("host", required=False)
@click.option("--key", default=None, help="Filter by item key pattern.")
@click.option("--type", "item_type", default=None, help="Filter by item type.")
@click.option(
    "--status",
    default=None,
    type=click.Choice(["enabled", "disabled"]),
    help="Filter by item status.",
)
@click.option(
    "--field", default=None, metavar="PATH", help="Extract one field per record."
)
@click.option(
    "--stdin-field",
    default=None,
    metavar="NAME",
    help="Read values from stdin, map to this field.",
)
@click.option(
    "--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin."
)
@click.option(
    "--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out."
)
@click.option(
    "--no-headers", is_flag=True, default=False, help="Suppress table headers."
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format.",
)
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
    no_headers: bool,
    output: str | None,
) -> None:
    """List items for a host."""
    _stub_output(cfg, "get items", output, no_headers, field)


# ---------------------------------------------------------------------------
# get triggers
# ---------------------------------------------------------------------------


@get.command("triggers")
@click.option("--severity", default=None, help="Filter by severity (name or 0–5).")
@click.option("--host", default=None, help="Filter by host name.")
@click.option(
    "--status",
    default=None,
    type=click.Choice(["enabled", "disabled"]),
    help="Filter by trigger status.",
)
@click.option(
    "--field", default=None, metavar="PATH", help="Extract one field per record."
)
@click.option(
    "--stdin-field",
    default=None,
    metavar="NAME",
    help="Read values from stdin, map to this field.",
)
@click.option(
    "--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin."
)
@click.option(
    "--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out."
)
@click.option(
    "--no-headers", is_flag=True, default=False, help="Suppress table headers."
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format.",
)
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
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix triggers."""
    _stub_output(cfg, "get triggers", output, no_headers, field)


# ---------------------------------------------------------------------------
# get alerts
# ---------------------------------------------------------------------------


@get.command("alerts")
@click.option("--severity", default=None, help="Filter by severity (name or 0–5).")
@click.option("--host", default=None, help="Filter by host name.")
@click.option(
    "--since",
    default=None,
    help="Show alerts since this time (ISO 8601 or Unix epoch).",
)
@click.option(
    "--acknowledged",
    is_flag=True,
    default=False,
    help="Include only acknowledged alerts.",
)
@click.option(
    "--field", default=None, metavar="PATH", help="Extract one field per record."
)
@click.option(
    "--stdin-field",
    default=None,
    metavar="NAME",
    help="Read values from stdin, map to this field.",
)
@click.option(
    "--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin."
)
@click.option(
    "--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out."
)
@click.option(
    "--no-headers", is_flag=True, default=False, help="Suppress table headers."
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format.",
)
@click.pass_obj
def get_alerts(
    cfg: ZabctlConfig,
    severity: str | None,
    host: str | None,
    since: str | None,
    acknowledged: bool,
    field: str | None,
    stdin_field: str | None,
    from_stdin: bool,
    batch_size: int,
    no_headers: bool,
    output: str | None,
) -> None:
    """List active alerts (Zabbix problems)."""
    _stub_output(cfg, "get alerts", output, no_headers, field)


# ---------------------------------------------------------------------------
# get templates
# ---------------------------------------------------------------------------


@get.command("templates")
@click.option(
    "--search", default=None, help="Search string matched against template name."
)
@click.option(
    "--field", default=None, metavar="PATH", help="Extract one field per record."
)
@click.option(
    "--no-headers", is_flag=True, default=False, help="Suppress table headers."
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format.",
)
@click.pass_obj
def get_templates(
    cfg: ZabctlConfig,
    search: str | None,
    field: str | None,
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix templates."""
    _stub_output(cfg, "get templates", output, no_headers, field)


# ---------------------------------------------------------------------------
# get template <id|name>
# ---------------------------------------------------------------------------


@get.command("template")
@click.argument("id_or_name")
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format.",
)
@click.pass_obj
def get_template(cfg: ZabctlConfig, id_or_name: str, output: str | None) -> None:
    """Show a single template by id or name."""
    _stub_output(cfg, "get template", output, False, None)


# ---------------------------------------------------------------------------
# get latestdata <host>
# ---------------------------------------------------------------------------


@get.command("latestdata")
@click.argument("host", required=False)
@click.option(
    "--stdin-field",
    default=None,
    metavar="NAME",
    help="Read values from stdin, map to this field.",
)
@click.option(
    "--from-stdin", is_flag=True, default=False, help="Read jsonl records from stdin."
)
@click.option(
    "--batch-size", default=10, show_default=True, help="Batch size for stdin fan-out."
)
@click.option(
    "--no-headers", is_flag=True, default=False, help="Suppress table headers."
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format.",
)
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
    _stub_output(cfg, "get latestdata", output, no_headers, None)


# ---------------------------------------------------------------------------
# get groups
# ---------------------------------------------------------------------------


@get.command("groups")
@click.option(
    "--field", default=None, metavar="PATH", help="Extract one field per record."
)
@click.option(
    "--no-headers", is_flag=True, default=False, help="Suppress table headers."
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format.",
)
@click.pass_obj
def get_groups(
    cfg: ZabctlConfig,
    field: str | None,
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix host groups."""
    _stub_output(cfg, "get groups", output, no_headers, field)


# ---------------------------------------------------------------------------
# get events
# ---------------------------------------------------------------------------


@get.command("events")
@click.option("--host", default=None, help="Filter by host name.")
@click.option(
    "--since",
    default=None,
    help="Show events since this time (ISO 8601 or Unix epoch).",
)
@click.option(
    "--until",
    default=None,
    help="Show events until this time (ISO 8601 or Unix epoch).",
)
@click.option(
    "--limit", default=None, type=int, help="Maximum number of events to return."
)
@click.option(
    "--field", default=None, metavar="PATH", help="Extract one field per record."
)
@click.option(
    "--no-headers", is_flag=True, default=False, help="Suppress table headers."
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format.",
)
@click.pass_obj
def get_events(
    cfg: ZabctlConfig,
    host: str | None,
    since: str | None,
    until: str | None,
    limit: int | None,
    field: str | None,
    no_headers: bool,
    output: str | None,
) -> None:
    """List Zabbix events."""
    _stub_output(cfg, "get events", output, no_headers, field)
