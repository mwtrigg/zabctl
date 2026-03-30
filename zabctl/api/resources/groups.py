"""Zabbix host group resource — Phase 0 stub."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient


def get_groups(
    client: ZabbixClient,
) -> list[dict[str, Any]]:
    """Return host groups. Stub: not yet implemented."""
    raise NotImplementedError("groups.get_groups() — Phase 0 stub")
