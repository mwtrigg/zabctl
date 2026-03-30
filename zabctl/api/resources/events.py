"""Zabbix event resource — Phase 0 stub."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient


def get_events(
    client: ZabbixClient,
    *,
    host: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return events. Stub: not yet implemented."""
    raise NotImplementedError("events.get_events() — Phase 0 stub")
