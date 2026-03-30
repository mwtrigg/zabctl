"""Zabbix alerts/problems resource — Phase 0 stub.

Zabbix calls these "problems" internally; we expose them as "alerts" for friendliness.
"""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient


def get_alerts(
    client: ZabbixClient,
    *,
    severity: str | None = None,
    host: str | None = None,
    since: str | None = None,
    acknowledged: bool | None = None,
) -> list[dict[str, Any]]:
    """Return active alerts (problems). Stub: not yet implemented."""
    raise NotImplementedError("alerts.get_alerts() — Phase 0 stub")
