"""Zabbix event resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient

_EVENT_OUTPUT = ["eventid", "source", "object", "objectid", "clock", "value", "acknowledged", "name", "severity"]


def _parse_time(value: str) -> int:
    """Parse an ISO 8601 string or Unix epoch string to an integer timestamp."""
    import datetime

    value = value.strip()
    if value.isdigit():
        return int(value)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(value, fmt).replace(
                tzinfo=datetime.UTC
            )
            return int(dt.timestamp())
        except ValueError:
            continue
    raise ValueError(f"Cannot parse time: {value!r}")


def _parse_sort(sort_by: str) -> tuple[str, str]:
    if ":" in sort_by:
        field, order = sort_by.rsplit(":", 1)
        return field, order.upper()
    return sort_by, "ASC"


def get_events(
    client: ZabbixClient,
    *,
    host: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
    sort_by: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return events."""
    params: dict[str, Any] = {
        "output": _EVENT_OUTPUT,
        "sortfield": "clock",
        "sortorder": "DESC",
        "source": 0,   # trigger events
        "object": 0,   # trigger object
    }

    if host:
        hostids = _resolve_host_id(client, host)
        params["hostids"] = hostids

    if since:
        params["time_from"] = _parse_time(since)

    if until:
        params["time_till"] = _parse_time(until)

    if limit:
        params["limit"] = limit

    if sort_by:
        field, order = _parse_sort(sort_by)
        params["sortfield"] = field
        params["sortorder"] = order

    if extra_params:
        params.update(extra_params)

    result: list[dict[str, Any]] = client.call("event.get", params)
    return result


def _resolve_host_id(client: ZabbixClient, host: str) -> list[str]:
    result: list[dict[str, Any]] = client.call(
        "host.get",
        {"output": ["hostid"], "filter": {"host": host}},
    )
    return [h["hostid"] for h in result]
