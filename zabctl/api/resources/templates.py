"""Zabbix template resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient, ZabbixNotFoundError

_TEMPLATE_OUTPUT = ["templateid", "name", "description"]


def _parse_sort(sort_by: str) -> tuple[str, str]:
    if ":" in sort_by:
        field, order = sort_by.rsplit(":", 1)
        return field, order.upper()
    return sort_by, "ASC"


def get_templates(
    client: ZabbixClient,
    *,
    search: str | None = None,
    limit: int | None = None,
    sort_by: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return templates."""
    params: dict[str, Any] = {"output": _TEMPLATE_OUTPUT}

    if search:
        params["search"] = {"name": search}

    if limit is not None:
        params["limit"] = limit

    if sort_by:
        field, order = _parse_sort(sort_by)
        params["sortfield"] = field
        params["sortorder"] = order

    if extra_params:
        params.update(extra_params)

    result: list[dict[str, Any]] = client.call("template.get", params)
    return result


def get_template(
    client: ZabbixClient,
    template_id_or_name: str,
) -> dict[str, Any]:
    """Return a single template by id or name, including items, triggers, and graphs."""
    params: dict[str, Any] = {
        "output": _TEMPLATE_OUTPUT,
        "selectGroups": ["groupid", "name"],
        "selectHosts": ["hostid", "host", "name"],
        "selectItems": ["itemid", "name", "key_"],
        "selectTriggers": ["triggerid", "description", "priority"],
        "selectGraphs": ["graphid", "name"],
    }

    if template_id_or_name.isdigit():
        params["templateids"] = [template_id_or_name]
    else:
        params["filter"] = {"name": template_id_or_name}

    result: list[dict[str, Any]] = client.call("template.get", params)
    if not result:
        raise ZabbixNotFoundError(f"Template not found: {template_id_or_name!r}")

    # Add computed count fields for convenient table display.
    record = result[0]
    record["items_count"] = len(record.get("items") or [])
    record["triggers_count"] = len(record.get("triggers") or [])
    record["graphs_count"] = len(record.get("graphs") or [])
    return record
