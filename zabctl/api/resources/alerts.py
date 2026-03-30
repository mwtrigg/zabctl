"""Zabbix alerts/problems resource.

Zabbix calls these "problems" internally; we expose them as "alerts" for friendliness.
"""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient

_PROBLEM_OUTPUT = ["eventid", "objectid", "severity", "name", "clock", "acknowledged", "r_eventid"]

_SEVERITY_MAP = {
    "not_classified": "0",
    "information": "1",
    "warning": "2",
    "average": "3",
    "high": "4",
    "disaster": "5",
}


def _parse_time(value: str) -> int:
    """Parse an ISO 8601 string or Unix epoch string to an integer timestamp."""
    import datetime

    value = value.strip()
    if value.isdigit():
        return int(value)
    # Try ISO 8601
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(value, fmt).replace(
                tzinfo=datetime.UTC
            )
            return int(dt.timestamp())
        except ValueError:
            continue
    raise ValueError(f"Cannot parse time: {value!r}")


def get_alerts(
    client: ZabbixClient,
    *,
    severity: str | None = None,
    host: str | None = None,
    since: str | None = None,
    acknowledged: bool | None = None,
) -> list[dict[str, Any]]:
    """Return active alerts (problems)."""
    params: dict[str, Any] = {
        "output": _PROBLEM_OUTPUT,
        "selectHosts": ["hostid", "host", "name"],
        "sortfield": ["eventid"],
        "sortorder": "DESC",
        "recent": True,  # active + recently resolved
    }

    if severity is not None:
        sev = _SEVERITY_MAP.get(severity.lower(), severity)
        params["severities"] = [sev]

    if host:
        # Resolve via trigger host filter
        params["hostids"] = _resolve_host_id(client, host)

    if since:
        params["time_from"] = _parse_time(since)

    if acknowledged is not None:
        params["acknowledged"] = 1 if acknowledged else 0

    result: list[dict[str, Any]] = client.call("problem.get", params)
    return result


def _resolve_host_id(client: ZabbixClient, host: str) -> list[str]:
    result: list[dict[str, Any]] = client.call(
        "host.get",
        {"output": ["hostid"], "filter": {"host": host}},
    )
    return [h["hostid"] for h in result]
