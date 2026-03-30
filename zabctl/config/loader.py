"""
Config resolution: ENV vars > CLI params > config file.

This order is strict and must not be changed. Environment variables have
the highest priority so that automation and agents can override everything
without touching the config file or CLI invocation.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

CONFIG_PATH = Path("~/.config/zabctl/config.yaml").expanduser()


@dataclass
class TLSConfig:
    insecure: bool = False
    ca_bundle: str | None = None
    client_cert: str | None = None
    client_key: str | None = None


@dataclass
class ProxyConfig:
    http: str | None = None
    https: str | None = None
    no_proxy: str | None = None


@dataclass
class ZabctlConfig:
    server: str | None = None
    api_token: str | None = None
    username: str | None = None
    password: str | None = None
    context_name: str | None = None
    output: str = "table"
    explain: bool = False
    defaults: dict[str, object] = field(default_factory=dict)
    tls: TLSConfig = field(default_factory=TLSConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)


def _load_config_file(
    context_name: str | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    """Load the config file.

    Returns:
        (context_cfg, global_defaults) where context_cfg is the active context dict
        and global_defaults is the top-level defaults: block.  Either may be empty.
    """
    if not CONFIG_PATH.exists():
        return {}, {}

    try:
        raw = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    except yaml.YAMLError as exc:
        print(
            f"warning: could not parse config file {CONFIG_PATH}: {exc}",
            file=sys.stderr,
        )
        return {}, {}

    global_defaults: dict[str, object] = raw.get("defaults", {})  # type: ignore[assignment]
    if not isinstance(global_defaults, dict):
        global_defaults = {}

    contexts: dict[str, object] = raw.get("contexts", {})  # type: ignore[assignment]
    if not isinstance(contexts, dict):
        return {}, global_defaults

    active = context_name or raw.get("current_context")
    if active and active in contexts:
        ctx: dict[str, object] = contexts[active]  # type: ignore[assignment]
        if not isinstance(ctx, dict):
            return {}, global_defaults
        return ctx, global_defaults

    return {}, global_defaults


def _str_or_none(val: object) -> str | None:
    if val is None:
        return None
    return str(val)


def load_config(
    *,
    server: str | None = None,
    api_token: str | None = None,
    username: str | None = None,
    password: str | None = None,
    context_name: str | None = None,
    output: str | None = None,
    explain: bool = False,
    insecure: bool | None = None,
    ca_bundle: str | None = None,
    client_cert: str | None = None,
    client_key: str | None = None,
    proxy: str | None = None,
    no_proxy: str | None = None,
) -> ZabctlConfig:
    """
    Resolve configuration from all sources.

    Priority (highest → lowest):
      1. Environment variables (ZABCTL_*)
      2. CLI parameters passed to this function
      3. Config file (~/.config/zabctl/config.yaml)
    """
    load_dotenv()

    # --- Step 1: config file (lowest priority) ---
    ctx_name_for_file = os.environ.get("ZABCTL_CONTEXT") or context_name
    file_cfg, global_defaults = _load_config_file(ctx_name_for_file)
    file_tls: dict[str, object] = file_cfg.get("tls", {})  # type: ignore[assignment]
    if not isinstance(file_tls, dict):
        file_tls = {}
    file_proxy: dict[str, object] = file_cfg.get("proxy", {})  # type: ignore[assignment]
    if not isinstance(file_proxy, dict):
        file_proxy = {}

    resolved_server = _str_or_none(file_cfg.get("server"))
    resolved_token = _str_or_none(file_cfg.get("api_token"))
    resolved_username = _str_or_none(file_cfg.get("username"))
    resolved_password = _str_or_none(file_cfg.get("password"))
    resolved_output = _str_or_none(file_cfg.get("output")) or "table"
    # Merge defaults: global first, context-level overrides global.
    file_defaults: dict[str, object] = file_cfg.get("defaults", {})  # type: ignore[assignment]
    if not isinstance(file_defaults, dict):
        file_defaults = {}
    resolved_defaults: dict[str, object] = {**global_defaults, **file_defaults}
    resolved_insecure = bool(file_tls.get("insecure", False))
    resolved_ca_bundle = _str_or_none(file_tls.get("ca_bundle"))
    resolved_client_cert = _str_or_none(file_tls.get("client_cert"))
    resolved_client_key = _str_or_none(file_tls.get("client_key"))
    resolved_proxy_http = _str_or_none(file_proxy.get("http"))
    resolved_proxy_https = _str_or_none(file_proxy.get("https"))
    resolved_no_proxy = _str_or_none(file_proxy.get("no_proxy"))

    # --- Step 2: CLI params (override config file) ---
    if server is not None:
        resolved_server = server
    if api_token is not None:
        resolved_token = api_token
    if username is not None:
        resolved_username = username
    if password is not None:
        resolved_password = password
    if output is not None:
        resolved_output = output
    if insecure is not None:
        resolved_insecure = insecure
    if ca_bundle is not None:
        resolved_ca_bundle = ca_bundle
    if client_cert is not None:
        resolved_client_cert = client_cert
    if client_key is not None:
        resolved_client_key = client_key
    if proxy is not None:
        resolved_proxy_http = proxy
        resolved_proxy_https = proxy
    if no_proxy is not None:
        resolved_no_proxy = no_proxy

    # --- Step 3: ENV vars (highest priority, override everything) ---
    if env_server := os.environ.get("ZABCTL_SERVER"):
        resolved_server = env_server
    if env_token := os.environ.get("ZABCTL_API_TOKEN"):
        resolved_token = env_token
    if env_user := os.environ.get("ZABCTL_USERNAME"):
        resolved_username = env_user
    if env_pass := os.environ.get("ZABCTL_PASSWORD"):
        resolved_password = env_pass
    if env_output := os.environ.get("ZABCTL_OUTPUT"):
        resolved_output = env_output
    if (env_insecure := os.environ.get("ZABCTL_INSECURE")) is not None:
        resolved_insecure = env_insecure.lower() in ("1", "true", "yes")
    if env_ca := os.environ.get("ZABCTL_CA_BUNDLE"):
        resolved_ca_bundle = env_ca
    if env_cert := os.environ.get("ZABCTL_CLIENT_CERT"):
        resolved_client_cert = env_cert
    if env_key := os.environ.get("ZABCTL_CLIENT_KEY"):
        resolved_client_key = env_key
    if env_proxy := os.environ.get("ZABCTL_PROXY"):
        resolved_proxy_http = env_proxy
        resolved_proxy_https = env_proxy
    if env_no_proxy := os.environ.get("ZABCTL_NO_PROXY"):
        resolved_no_proxy = env_no_proxy

    # --- Auth: token always wins over username/password ---
    # (no action needed — just document: callers must check token first)

    # --- Warn on plaintext password in config file ---
    if _str_or_none(file_cfg.get("password")):
        print(
            "warning: plaintext password in config file — use api_token instead",
            file=sys.stderr,
        )

    # --- Warn on --insecure usage ---
    if resolved_insecure:
        print(
            "warning: TLS verification disabled (--insecure) — "
            "this is unsafe outside of local development",
            file=sys.stderr,
        )

    return ZabctlConfig(
        server=resolved_server,
        api_token=resolved_token,
        username=resolved_username,
        password=resolved_password,
        context_name=ctx_name_for_file,
        output=resolved_output,
        explain=explain,
        defaults=resolved_defaults,
        tls=TLSConfig(
            insecure=resolved_insecure,
            ca_bundle=resolved_ca_bundle,
            client_cert=resolved_client_cert,
            client_key=resolved_client_key,
        ),
        proxy=ProxyConfig(
            http=resolved_proxy_http,
            https=resolved_proxy_https,
            no_proxy=resolved_no_proxy,
        ),
    )
