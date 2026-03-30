"""Zabbix host resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient, ZabbixNotFoundError

_HOST_OUTPUT = ["hostid", "host", "name", "status", "description"]
_HOST_SELECT = {
    "selectInterfaces": ["ip", "dns", "port", "type", "main"],
    "selectGroups": ["groupid", "name"],
    "selectTemplates": ["templateid", "name"],
}

_STATUS_MAP = {"monitored": "0", "unmonitored": "1"}


def get_hosts(
    client: ZabbixClient,
    *,
    group: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Return a list of hosts."""
    params: dict[str, Any] = {
        "output": _HOST_OUTPUT,
        **_HOST_SELECT,
    }

    if group:
        params["groupids"] = _resolve_group_id(client, group)

    if status:
        params["filter"] = {"status": _STATUS_MAP.get(status, status)}

    if search:
        params["search"] = {"host": search, "name": search}
        params["searchByAny"] = True

    result: list[dict[str, Any]] = client.call("host.get", params)
    return result


def get_host(
    client: ZabbixClient,
    host_id_or_name: str,
) -> dict[str, Any]:
    """Return a single host by id or name."""
    params: dict[str, Any] = {
        "output": _HOST_OUTPUT,
        **_HOST_SELECT,
    }

    # Try numeric id first, then host name.
    if host_id_or_name.isdigit():
        params["hostids"] = [host_id_or_name]
    else:
        params["filter"] = {"host": host_id_or_name}

    result: list[dict[str, Any]] = client.call("host.get", params)
    if not result:
        raise ZabbixNotFoundError(f"Host not found: {host_id_or_name!r}")
    return result[0]


def _resolve_group_id(client: ZabbixClient, group_name: str) -> list[str]:
    """Return groupids matching the given name (exact match)."""
    result: list[dict[str, Any]] = client.call(
        "hostgroup.get",
        {"output": ["groupid"], "filter": {"name": group_name}},
    )
    return [g["groupid"] for g in result]
