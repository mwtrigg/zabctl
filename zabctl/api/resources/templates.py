"""Zabbix template resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient, ZabbixNotFoundError

_TEMPLATE_OUTPUT = ["templateid", "name", "description"]


def get_templates(
    client: ZabbixClient,
    *,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Return templates."""
    params: dict[str, Any] = {"output": _TEMPLATE_OUTPUT}

    if search:
        params["search"] = {"name": search}

    result: list[dict[str, Any]] = client.call("template.get", params)
    return result


def get_template(
    client: ZabbixClient,
    template_id_or_name: str,
) -> dict[str, Any]:
    """Return a single template by id or name."""
    params: dict[str, Any] = {
        "output": _TEMPLATE_OUTPUT,
        "selectGroups": ["groupid", "name"],
        "selectHosts": ["hostid", "host", "name"],
    }

    if template_id_or_name.isdigit():
        params["templateids"] = [template_id_or_name]
    else:
        params["filter"] = {"name": template_id_or_name}

    result: list[dict[str, Any]] = client.call("template.get", params)
    if not result:
        raise ZabbixNotFoundError(f"Template not found: {template_id_or_name!r}")
    return result[0]
