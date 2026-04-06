"""
zabctl template commands.

Commands:
  template export <name|id>     Dump a live template to YAML (stdout or file)
  template import <file>        Push a YAML template to Zabbix
  template diff <name|id> <file> Compare live template vs local YAML file
  template export --host <name>  Export a host definition to YAML
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from zabctl.api.resources.configuration import (
    diff_template,
    export_host,
    export_template,
    import_template,
)
from zabctl.cli._common import _handle_api_error, _make_client, _resolve_output
from zabctl.config.loader import ZabctlConfig
from zabctl.output.formatter import format_output


@click.group("template")
def template_group() -> None:
    """Manage Zabbix templates and host config as code."""


# ---------------------------------------------------------------------------
# template export
# ---------------------------------------------------------------------------

@template_group.command("export")
@click.argument("name_or_id", required=False)
@click.option("--host", "host_name", default=None, help="Export a host definition instead of a template.")
@click.option(
    "--output-file", "-f",
    default=None,
    type=click.Path(),
    help="Write YAML to this file instead of stdout.",
)
@click.pass_obj
def template_export(
    cfg: ZabctlConfig,
    name_or_id: str | None,
    host_name: str | None,
    output_file: str | None,
) -> None:
    """Export a template (or host) as Zabbix YAML.

    \b
    Examples:
      zabctl template export "Linux by Zabbix agent"
      zabctl template export "Linux by Zabbix agent" -f template.yaml
      zabctl template export --host web01
      zabctl template export --host web01 -f web01.yaml
    """
    if host_name and name_or_id:
        click.echo("error: provide NAME_OR_ID or --host, not both", err=True)
        raise SystemExit(5)
    if not host_name and not name_or_id:
        click.echo("error: provide a template name/id or --host <name>", err=True)
        raise SystemExit(5)

    client = _make_client(cfg)
    try:
        if host_name:
            yaml_out = export_host(client, host_name)
        else:
            yaml_out = export_template(client, name_or_id)  # type: ignore[arg-type]
    except Exception as exc:
        _handle_api_error(exc)
        return

    if output_file:
        Path(output_file).write_text(yaml_out)
        click.echo(f"exported to {output_file}", err=True)
    else:
        click.echo(yaml_out, nl=False)


# ---------------------------------------------------------------------------
# template import
# ---------------------------------------------------------------------------

@template_group.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.option("--no-update", is_flag=True, default=False, help="Create missing only — do not update existing templates.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def template_import(
    cfg: ZabctlConfig,
    file: str,
    yes: bool,
    no_update: bool,
    output: str | None,
) -> None:
    """Import a template from a YAML file.

    Conflict resolution: createMissing + updateExisting (default).
    Use --no-update to create missing templates only (skip existing).
    deleteMissing is never set — too destructive.

    \b
    Example:
      zabctl template import template.yaml
      zabctl template import template.yaml --no-update
    """
    fmt = _resolve_output(cfg.output, output)

    if not yes:
        update_note = "create-only (no updates)" if no_update else "create + update existing"
        click.confirm(
            f"Import template from {file!r} ({update_note})?",
            abort=True,
        )

    source = Path(file).read_text()
    client = _make_client(cfg)
    try:
        result = import_template(
            client,
            source,
            create_missing=True,
            update_existing=not no_update,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return

    click.echo(f"imported {file!r} → success: {result['success']}", err=True)
    format_output(
        data=[result],
        output_format=fmt,
        command="template import",
        server=cfg.server,
        api_version=client.api_version,
        columns=["success"],
    )


# ---------------------------------------------------------------------------
# template diff
# ---------------------------------------------------------------------------

@template_group.command("diff")
@click.argument("name_or_id")
@click.argument("file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]), help="Output format.")
@click.pass_obj
def template_diff(
    cfg: ZabctlConfig,
    name_or_id: str,
    file: str,
    output: str | None,
) -> None:
    """Compare a live template against a local YAML file.

    Volatile fields (UUIDs, internal IDs) are stripped before comparison
    so only meaningful content changes are shown.

    Exits 0 if identical, 1 if differences found.

    \b
    Examples:
      zabctl template diff "Linux by Zabbix agent" template.yaml
      zabctl template diff 10001 template.yaml
    """
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        diff = diff_template(client, name_or_id, file)
    except FileNotFoundError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(5)
    except Exception as exc:
        _handle_api_error(exc)
        return

    if not diff:
        if fmt in ("json", "jsonl", "yaml"):
            format_output(
                data=[{"identical": True, "diff": ""}],
                output_format=fmt,
                command="template diff",
                server=cfg.server,
                api_version=client.api_version,
                columns=["identical", "diff"],
            )
        else:
            click.echo("no differences (after normalizing volatile fields)")
        raise SystemExit(0)

    if fmt in ("json", "jsonl", "yaml"):
        format_output(
            data=[{"identical": False, "diff": diff}],
            output_format=fmt,
            command="template diff",
            server=cfg.server,
            api_version=client.api_version,
            columns=["identical", "diff"],
        )
    else:
        click.echo(diff, nl=False)
    raise SystemExit(1)
