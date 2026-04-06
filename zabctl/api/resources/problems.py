"""Zabbix problems resource.

Zabbix calls these "problems" internally; we expose them via the `get problems` command.
"""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient
from zabctl.api.utils import parse_sort, parse_time

_PROBLEM_OUTPUT = ["eventid", "objectid", "severity", "name", "clock", "acknowledged", "r_eventid"]

_SEVERITY_MAP = {
    "not_classified": "0",
    "information": "1",
    "warning": "2",
    "average": "3",
    "high": "4",
    "disaster": "5",
}


def get_alerts(
    client: ZabbixClient,
    *,
    severity: str | None = None,
    host: str | None = None,
    since: str | None = None,
    acknowledged: bool | None = None,
    limit: int | None = None,
    sort_by: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return active alerts (problems)."""
    params: dict[str, Any] = {
        "output": _PROBLEM_OUTPUT,
        "sortfield": ["eventid"],
        "sortorder": "DESC",
        "recent": True,  # active + recently resolved
    }

    if severity is not None:
        sev = _SEVERITY_MAP.get(severity.lower(), severity)
        params["severities"] = [sev]

    if host:
        params["hostids"] = _resolve_host_id(client, host)

    if since:
        params["time_from"] = parse_time(since)

    if acknowledged is not None:
        params["acknowledged"] = bool(acknowledged)

    if limit is not None:
        params["limit"] = limit

    if sort_by:
        field, order = parse_sort(sort_by)
        params["sortfield"] = [field]
        params["sortorder"] = order

    if extra_params:
        params.update(extra_params)

    result: list[dict[str, Any]] = client.call("problem.get", params)
    return result


def _resolve_host_id(client: ZabbixClient, host: str) -> list[str]:
    result: list[dict[str, Any]] = client.call(
        "host.get",
        {"output": ["hostid"], "filter": {"host": host}},
    )
    return [h["hostid"] for h in result]
