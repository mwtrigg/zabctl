"""Zabbix item resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient

_ITEM_OUTPUT = ["itemid", "hostid", "key_", "name", "lastvalue", "lastclock", "units", "type", "status"]

_STATUS_MAP = {"enabled": "0", "disabled": "1"}


def _host_ids(client: ZabbixClient, host: str) -> list[str]:
    """Resolve a hostname to a list of hostids."""
    result: list[dict[str, Any]] = client.call(
        "host.get",
        {"output": ["hostid"], "filter": {"host": host}},
    )
    return [h["hostid"] for h in result]


def get_items(
    client: ZabbixClient,
    host: str,
    *,
    key: str | None = None,
    item_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return items for a host."""
    params: dict[str, Any] = {
        "output": _ITEM_OUTPUT,
        "hostids": _host_ids(client, host),
    }

    if key:
        params["search"] = {"key_": key}

    if item_type:
        params["filter"] = params.get("filter", {})
        params["filter"]["type"] = item_type

    if status:
        params.setdefault("filter", {})
        params["filter"]["status"] = _STATUS_MAP.get(status, status)

    result: list[dict[str, Any]] = client.call("item.get", params)
    return result


def get_latestdata(
    client: ZabbixClient,
    host: str,
) -> list[dict[str, Any]]:
    """Return items with their most recent values for a host."""
    params: dict[str, Any] = {
        "output": _ITEM_OUTPUT,
        "hostids": _host_ids(client, host),
        "monitored": True,
        "sortfield": "name",
        "sortorder": "ASC",
    }
    result: list[dict[str, Any]] = client.call("item.get", params)
    return result
