"""Zabbix item resource — Phase 0 stub."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient


def get_items(
    client: ZabbixClient,
    host: str,
    *,
    key: str | None = None,
    item_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return items for a host. Stub: not yet implemented."""
    raise NotImplementedError("items.get_items() — Phase 0 stub")
