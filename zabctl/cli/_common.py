"""Shared CLI helpers used by get.py and write.py."""

from __future__ import annotations

import httpx

from zabctl.api.client import (
    ZabbixAPIError,
    ZabbixAuthError,
    ZabbixClient,
    ZabbixNotFoundError,
)
from zabctl.config.loader import ZabctlConfig
from zabctl.output.formatter import format_error


def _resolve_output(ctx_output: str, local_output: str | None) -> str:
    return local_output or ctx_output or "table"


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
