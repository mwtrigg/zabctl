"""Zabbix host group resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient


def get_groups(
    client: ZabbixClient,
) -> list[dict[str, Any]]:
    """Return host groups."""
    result: list[dict[str, Any]] = client.call(
        "hostgroup.get",
        {
            "output": ["groupid", "name"],
            "sortfield": "name",
        },
    )
    return result
