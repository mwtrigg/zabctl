"""Zabbix host resource — Phase 0 stub."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient


def get_hosts(
    client: ZabbixClient,
    *,
    group: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Return a list of hosts. Stub: not yet implemented."""
    raise NotImplementedError("hosts.get_hosts() — Phase 0 stub")


def get_host(
    client: ZabbixClient,
    host_id_or_name: str,
) -> dict[str, Any]:
    """Return a single host by id or name. Stub: not yet implemented."""
    raise NotImplementedError("hosts.get_host() — Phase 0 stub")
