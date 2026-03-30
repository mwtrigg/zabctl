"""Zabbix trigger resource — Phase 0 stub."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient


def get_triggers(
    client: ZabbixClient,
    *,
    severity: str | None = None,
    host: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return triggers. Stub: not yet implemented."""
    raise NotImplementedError("triggers.get_triggers() — Phase 0 stub")
