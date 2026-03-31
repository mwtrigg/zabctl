"""Zabbix trigger resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient
from zabctl.api.utils import parse_sort

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
    limit: int | None = None,
    sort_by: str | None = None,
    extra_params: dict[str, Any] | None = None,
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

    if limit is not None:
        params["limit"] = limit

    if sort_by:
        field, order = parse_sort(sort_by)
        params["sortfield"] = field
        params["sortorder"] = order

    if extra_params:
        params.update(extra_params)

    result: list[dict[str, Any]] = client.call("trigger.get", params)
    return result


def enable_trigger(client: ZabbixClient, trigger_id: str) -> dict[str, Any]:
    """Set trigger status=0 (enabled). Returns {"triggerids": [...]}."""
    result: dict[str, Any] = client.call("trigger.update", {"triggerid": trigger_id, "status": 0})
    return result


def disable_trigger(client: ZabbixClient, trigger_id: str) -> dict[str, Any]:
    """Set trigger status=1 (disabled). Returns {"triggerids": [...]}."""
    result: dict[str, Any] = client.call("trigger.update", {"triggerid": trigger_id, "status": 1})
    return result
