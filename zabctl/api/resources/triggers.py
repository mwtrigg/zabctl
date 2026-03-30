"""Zabbix trigger resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient

_TRIGGER_OUTPUT = ["triggerid", "description", "priority", "status", "value", "lastchange"]

_SEVERITY_MAP = {
    "not_classified": "0",
    "information": "1",
    "warning": "2",
    "average": "3",
    "high": "4",
    "disaster": "5",
}

_STATUS_MAP = {"enabled": "0", "disabled": "1"}


def get_triggers(
    client: ZabbixClient,
    *,
    severity: str | None = None,
    host: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return triggers."""
    params: dict[str, Any] = {
        "output": _TRIGGER_OUTPUT,
        "selectHosts": ["hostid", "host", "name"],
        "expandDescription": True,
        "sortfield": "lastchange",
        "sortorder": "DESC",
    }

    if severity is not None:
        params["filter"] = params.get("filter", {})
        sev = _SEVERITY_MAP.get(severity.lower(), severity)
        params["filter"]["priority"] = sev

    if host:
        params["host"] = host

    if status:
        params.setdefault("filter", {})
        params["filter"]["status"] = _STATUS_MAP.get(status, status)

    result: list[dict[str, Any]] = client.call("trigger.get", params)
    return result
