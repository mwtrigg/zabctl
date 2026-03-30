"""
zabctl root CLI group.

Global options are resolved here and stored in ctx.obj (a ZabctlConfig).
All subcommands access config via @click.pass_obj.

Resolution order (ENV > CLI params > config file) is enforced in config/loader.py.
"""

from __future__ import annotations

import importlib.metadata

import click

from zabctl.config.loader import load_config

from .auth import auth
from .context import context
from .get import get
from .llm import llm


@click.group()
@click.version_option(
    importlib.metadata.version("zabctl"),
    "-V",
    "--version",
    prog_name="zabctl",
)
@click.option(
    "--server", envvar="ZABCTL_SERVER", default=None, help="Zabbix server URL."
)
@click.option(
    "--token", envvar="ZABCTL_API_TOKEN", default=None, help="Zabbix API token."
)
@click.option(
    "--username", envvar="ZABCTL_USERNAME", default=None, help="Zabbix username."
)
@click.option(
    "--password",
    envvar="ZABCTL_PASSWORD",
    default=None,
    hide_input=True,
    help="Zabbix password (use API token instead where possible).",
)
@click.option(
    "--context",
    "context_name",
    envvar="ZABCTL_CONTEXT",
    default=None,
    help="Named context from config file.",
)
@click.option(
    "--output",
    "-o",
    envvar="ZABCTL_OUTPUT",
    default=None,
    type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]),
    help="Output format. Default: table.",
)
@click.option(
    "--insecure",
    is_flag=True,
    default=False,
    envvar="ZABCTL_INSECURE",
    help="Skip TLS certificate verification (unsafe — dev only).",
)
@click.option(
    "--ca-bundle",
    envvar="ZABCTL_CA_BUNDLE",
    default=None,
    help="Path to custom CA bundle or directory (PEM).",
)
@click.option(
    "--client-cert",
    envvar="ZABCTL_CLIENT_CERT",
    default=None,
    help="Path to client certificate (PEM) for mutual TLS.",
)
@click.option(
    "--client-key",
    envvar="ZABCTL_CLIENT_KEY",
    default=None,
    help="Path to client private key (PEM) for mutual TLS.",
)
@click.option(
    "--proxy", envvar="ZABCTL_PROXY", default=None, help="Proxy URL for all requests."
)
@click.option(
    "--no-proxy",
    envvar="ZABCTL_NO_PROXY",
    default=None,
    help="Comma-separated hostnames/CIDRs to bypass proxy.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    server: str | None,
    token: str | None,
    username: str | None,
    password: str | None,
    context_name: str | None,
    output: str | None,
    insecure: bool,
    ca_bundle: str | None,
    client_cert: str | None,
    client_key: str | None,
    proxy: str | None,
    no_proxy: str | None,
) -> None:
    """zabctl — CLI for managing Zabbix monitoring environments."""
    ctx.ensure_object(dict)
    ctx.obj = load_config(
        server=server,
        api_token=token,
        username=username,
        password=password,
        context_name=context_name,
        output=output,
        insecure=insecure if insecure else None,
        ca_bundle=ca_bundle,
        client_cert=client_cert,
        client_key=client_key,
        proxy=proxy,
        no_proxy=no_proxy,
    )


cli.add_command(auth)
cli.add_command(context)
cli.add_command(get)
cli.add_command(llm)
