"""
zabctl auth commands.

auth login   — acquire and store a session token
auth logout  — invalidate current session token
auth status  — show current auth state
"""

from __future__ import annotations

import click

from zabctl.config.loader import ZabctlConfig


@click.group()
def auth() -> None:
    """Manage authentication to a Zabbix server."""


@auth.command("login")
@click.option(
    "--username", "-u", default=None, help="Zabbix username (overrides config/env)."
)
@click.option(
    "--password",
    "-p",
    default=None,
    hide_input=True,
    prompt=False,
    help="Zabbix password.",
)
@click.pass_obj
def auth_login(cfg: ZabctlConfig, username: str | None, password: str | None) -> None:
    """Authenticate to the Zabbix server and store the session token."""
    # Phase 0 stub
    server = cfg.server or "(no server configured)"
    click.echo(f"[stub] Would authenticate to {server}", err=False)
    raise NotImplementedError("auth login — Phase 0 stub")


@auth.command("logout")
@click.pass_obj
def auth_logout(cfg: ZabctlConfig) -> None:
    """Invalidate the current session token."""
    # Phase 0 stub
    click.echo("[stub] Would log out", err=False)
    raise NotImplementedError("auth logout — Phase 0 stub")


@auth.command("status")
@click.pass_obj
def auth_status(cfg: ZabctlConfig) -> None:
    """Show current authentication status."""
    server = cfg.server or "(not configured)"
    has_token = bool(cfg.api_token)
    has_creds = bool(cfg.username)

    click.echo(f"server:    {server}")
    click.echo(f"api_token: {'set' if has_token else 'not set'}")
    click.echo(f"username:  {cfg.username or 'not set'}")
    click.echo(
        f"auth_via:  {'token' if has_token else 'username/password' if has_creds else 'none'}"
    )
    click.echo(f"context:   {cfg.context_name or 'default'}")
    click.echo(f"output:    {cfg.output}")
    click.echo(f"insecure:  {cfg.tls.insecure}")
