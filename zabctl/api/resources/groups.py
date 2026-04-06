"""Zabbix host group resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient


def _parse_sort(sort_by: str) -> tuple[str, str]:
    if ":" in sort_by:
        field, order = sort_by.rsplit(":", 1)
        return field, order.upper()
    return sort_by, "ASC"


def get_groups(
    client: ZabbixClient,
    *,
    limit: int | None = None,
    sort_by: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return host groups."""
    params: dict[str, Any] = {
        "output": ["groupid", "name"],
        "sortfield": "name",
    }

    if limit is not None:
        params["limit"] = limit

    if sort_by:
        field, order = _parse_sort(sort_by)
        params["sortfield"] = field
        params["sortorder"] = order

    if extra_params:
        existing = params.get("filter", {})
        params["filter"] = {**existing, **extra_params}

    result: list[dict[str, Any]] = client.call("hostgroup.get", params)
    return result
