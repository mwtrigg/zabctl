"""
zabctl auth commands.

auth login   — acquire and store a session token
auth logout  — invalidate current session token
auth status  — show current auth state
"""

from __future__ import annotations

import click
import httpx

from zabctl.api.client import ZabbixAPIError, ZabbixAuthError, ZabbixClient
from zabctl.config.loader import ZabctlConfig
from zabctl.output.formatter import format_error


@click.group()
def auth() -> None:
    """Manage authentication to a Zabbix server."""


@auth.command("login")
@click.option("--username", "-u", default=None, help="Zabbix username (overrides config/env).")
@click.option("--password", "-p", default=None, hide_input=True, prompt=False, help="Zabbix password.")
@click.pass_obj
def auth_login(cfg: ZabctlConfig, username: str | None, password: str | None) -> None:
    """Authenticate to the Zabbix server and verify connectivity."""
    if not cfg.server:
        format_error("No server configured — set ZABCTL_SERVER or --server", exit_code=5)
        return

    # Apply local overrides to a temporary config.
    from dataclasses import replace
    effective = replace(cfg, username=username or cfg.username, password=password or cfg.password)

    client = ZabbixClient(effective)
    try:
        client.login()
    except ZabbixAuthError as exc:
        format_error(str(exc), exit_code=3)
        return
    except httpx.ConnectError as exc:
        format_error(str(exc), exit_code=4)
        return
    except httpx.TimeoutException:
        format_error(f"Connection to {cfg.server} timed out", exit_code=4)
        return
    except ZabbixAPIError as exc:
        format_error(str(exc), exit_code=1)
        return

    auth_method = "api_token" if cfg.api_token else "username/password"
    click.echo(f"authenticated to {cfg.server} via {auth_method}")
    click.echo(f"api_version: {client.api_version}")


@auth.command("logout")
@click.pass_obj
def auth_logout(cfg: ZabctlConfig) -> None:
    """Invalidate the current session token."""
    if not cfg.server:
        format_error("No server configured", exit_code=5)
        return
    if not cfg.api_token and not cfg.username:
        format_error("No credentials configured — nothing to log out", exit_code=1)
        return

    client = ZabbixClient(cfg)
    try:
        client.login()
        client.logout()
    except ZabbixAuthError as exc:
        format_error(str(exc), exit_code=3)
        return
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        format_error(str(exc), exit_code=4)
        return

    click.echo(f"logged out from {cfg.server}")


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
    click.echo(f"auth_via:  {'token' if has_token else 'username/password' if has_creds else 'none'}")
    click.echo(f"context:   {cfg.context_name or 'default'}")
    click.echo(f"output:    {cfg.output}")
    click.echo(f"insecure:  {cfg.tls.insecure}")

    # Live connectivity check if we have enough config.
    if cfg.server and (has_token or has_creds):
        client = ZabbixClient(cfg)
        try:
            client.login()
            click.echo(f"connected: yes (api_version: {client.api_version})")
        except ZabbixAuthError:
            click.echo("connected: auth failed", err=True)
        except (httpx.ConnectError, httpx.TimeoutException):
            click.echo("connected: no (connection failed)", err=True)
