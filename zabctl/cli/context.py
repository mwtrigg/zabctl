"""
zabctl context commands.

context list      — list all configured contexts
context use <name> — switch the active context
"""

from __future__ import annotations

import click
import yaml

from zabctl.config.loader import CONFIG_PATH, ZabctlConfig


@click.group()
def context() -> None:
    """Manage named Zabbix server contexts."""


@context.command("list")
@click.pass_obj
def context_list(cfg: ZabctlConfig) -> None:
    """List all configured contexts."""
    if not CONFIG_PATH.exists():
        click.echo("No config file found at ~/.config/zabctl/config.yaml", err=True)
        return

    raw = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    contexts: dict[str, object] = raw.get("contexts", {})  # type: ignore[assignment]
    current: str | None = raw.get("current_context")  # type: ignore[assignment]

    if not contexts:
        click.echo("No contexts configured.")
        return

    for name in contexts:
        marker = "* " if name == current else "  "
        click.echo(f"{marker}{name}")


@context.command("use")
@click.argument("name")
@click.pass_obj
def context_use(cfg: ZabctlConfig, name: str) -> None:
    """Switch the active context in the config file."""
    if not CONFIG_PATH.exists():
        click.echo("No config file found at ~/.config/zabctl/config.yaml", err=True)
        raise SystemExit(1)

    raw = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    contexts: dict[str, object] = raw.get("contexts", {})  # type: ignore[assignment]

    if name not in contexts:
        click.echo(f"error: context '{name}' not found in config file", err=True)
        raise SystemExit(2)

    raw["current_context"] = name
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(yaml.dump(raw, default_flow_style=False, allow_unicode=True))
    click.echo(f"Switched to context '{name}'.")
