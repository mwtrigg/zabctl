"""Zabbix host resource."""

from __future__ import annotations

from typing import Any

import yaml

from zabctl.api.client import ZabbixClient, ZabbixNotFoundError

_HOST_OUTPUT = ["hostid", "host", "name", "status", "description"]
_HOST_SELECT = {
    "selectInterfaces": ["ip", "dns", "port", "type", "main"],
    "selectGroups": ["groupid", "name"],
    "selectTemplates": ["templateid", "name"],
}

_STATUS_MAP = {"monitored": "0", "unmonitored": "1"}


def _parse_sort(sort_by: str) -> tuple[str, str]:
    """Parse 'field' or 'field:desc' into (field, ORDER)."""
    if ":" in sort_by:
        field, order = sort_by.rsplit(":", 1)
        return field, order.upper()
    return sort_by, "ASC"


def get_hosts(
    client: ZabbixClient,
    *,
    group: str | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int | None = None,
    sort_by: str | None = None,
    extra_params: dict[str, Any] | None = None,
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

    if limit is not None:
        params["limit"] = limit

    if sort_by:
        field, order = _parse_sort(sort_by)
        params["sortfield"] = [field]
        params["sortorder"] = order

    if extra_params:
        existing = params.get("filter", {})
        params["filter"] = {**existing, **extra_params}

    result: list[dict[str, Any]] = client.call("host.get", params)
    return result


_HOST_DETAIL_SELECT = {
    **_HOST_SELECT,
    "selectTags": ["tag", "value"],
    "selectMacros": ["macro", "value", "description"],
    "selectParentTemplates": ["templateid", "name"],
}


def get_host(
    client: ZabbixClient,
    host_id_or_name: str,
) -> dict[str, Any]:
    """Return a single host with full detail (tags, macros, templates)."""
    params: dict[str, Any] = {
        "output": _HOST_OUTPUT,
        **_HOST_DETAIL_SELECT,
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


def add_host_tag(
    client: ZabbixClient,
    host_id_or_name: str,
    tag: str,
    value: str = "",
) -> dict[str, Any]:
    """Add a tag to a host (non-destructive: merges with existing tags)."""
    hostid = _resolve_hostid(client, host_id_or_name)
    # Fetch current tags to merge rather than replace.
    existing: list[dict[str, Any]] = client.call(
        "host.get",
        {"output": [], "hostids": [hostid], "selectTags": ["tag", "value"]},
    )
    current_tags: list[dict[str, Any]] = existing[0].get("tags", []) if existing else []
    # Avoid duplicates.
    for t in current_tags:
        if t.get("tag") == tag and t.get("value") == value:
            return {"hostids": [hostid]}  # already present, no-op
    new_tags = current_tags + [{"tag": tag, "value": value}]
    result: dict[str, Any] = client.call(
        "host.update", {"hostid": hostid, "tags": new_tags}
    )
    return result


def remove_host_tag(
    client: ZabbixClient,
    host_id_or_name: str,
    tag: str,
    value: str | None = None,
) -> dict[str, Any]:
    """Remove a tag from a host. If value is given, only removes the exact tag+value pair."""
    hostid = _resolve_hostid(client, host_id_or_name)
    existing: list[dict[str, Any]] = client.call(
        "host.get",
        {"output": [], "hostids": [hostid], "selectTags": ["tag", "value"]},
    )
    current_tags: list[dict[str, Any]] = existing[0].get("tags", []) if existing else []
    if value is not None:
        new_tags = [t for t in current_tags if not (t.get("tag") == tag and t.get("value") == value)]
    else:
        new_tags = [t for t in current_tags if t.get("tag") != tag]
    result: dict[str, Any] = client.call(
        "host.update", {"hostid": hostid, "tags": new_tags}
    )
    return result


def enable_host(client: ZabbixClient, host_id_or_name: str) -> dict[str, Any]:
    """Set host status=0 (monitored). Returns {"hostids": [...]}."""
    hostid = _resolve_hostid(client, host_id_or_name)
    result: dict[str, Any] = client.call("host.update", {"hostid": hostid, "status": 0})
    return result


def disable_host(client: ZabbixClient, host_id_or_name: str) -> dict[str, Any]:
    """Set host status=1 (not monitored). Returns {"hostids": [...]}."""
    hostid = _resolve_hostid(client, host_id_or_name)
    result: dict[str, Any] = client.call("host.update", {"hostid": hostid, "status": 1})
    return result


def delete_host(client: ZabbixClient, host_id_or_name: str) -> dict[str, Any]:
    """Delete a host. Returns {"hostids": [...]}."""
    hostid = _resolve_hostid(client, host_id_or_name)
    result: dict[str, Any] = client.call("host.delete", [hostid])
    return result


def create_host(
    client: ZabbixClient,
    *,
    host: str,
    group_names: list[str],
    name: str | None = None,
    interface_ip: str = "127.0.0.1",
    interface_port: str = "10050",
    template_names: list[str] | None = None,
) -> dict[str, Any]:
    """Create a host. Returns {"hostids": [...]}."""
    group_ids = [{"groupid": gid} for gid in _resolve_group_ids(client, group_names)]
    if not group_ids:
        raise ValueError(f"No matching host groups found: {group_names!r}")

    params: dict[str, Any] = {
        "host": host,
        "groups": group_ids,
        "interfaces": [
            {
                "type": 1,  # Zabbix agent
                "main": 1,
                "useip": 1,
                "ip": interface_ip,
                "dns": "",
                "port": interface_port,
            }
        ],
    }

    if name:
        params["name"] = name

    if template_names:
        template_ids = _resolve_template_ids(client, template_names)
        params["templates"] = [{"templateid": tid} for tid in template_ids]

    result: dict[str, Any] = client.call("host.create", params)
    return result


def create_host_from_file(client: ZabbixClient, path: str) -> dict[str, Any]:
    """Create a host from a YAML definition file."""
    with open(path) as f:
        spec = yaml.safe_load(f)

    host = spec.get("host")
    if not host:
        raise ValueError("YAML file must contain a 'host' key")
    group_names = spec.get("groups")
    if not group_names:
        raise ValueError("YAML file must contain a 'groups' key with at least one group")

    iface = spec.get("interface", {})
    return create_host(
        client,
        host=host,
        group_names=group_names,
        name=spec.get("name"),
        interface_ip=iface.get("ip", "127.0.0.1"),
        interface_port=str(iface.get("port", "10050")),
        template_names=spec.get("templates"),
    )


def _resolve_hostid(client: ZabbixClient, host_id_or_name: str) -> str:
    """Return the hostid for a given id or host name."""
    if host_id_or_name.isdigit():
        return host_id_or_name
    result: list[dict[str, Any]] = client.call(
        "host.get", {"output": ["hostid"], "filter": {"host": host_id_or_name}}
    )
    if not result:
        raise ZabbixNotFoundError(f"Host not found: {host_id_or_name!r}")
    return str(result[0]["hostid"])


def _resolve_group_ids(client: ZabbixClient, group_names: list[str]) -> list[str]:
    """Return groupids for a list of group names."""
    result: list[dict[str, Any]] = client.call(
        "hostgroup.get",
        {"output": ["groupid", "name"], "filter": {"name": group_names}},
    )
    return [g["groupid"] for g in result]


def _resolve_template_ids(client: ZabbixClient, template_names: list[str]) -> list[str]:
    """Return templateids for a list of template names."""
    result: list[dict[str, Any]] = client.call(
        "template.get",
        {"output": ["templateid"], "filter": {"name": template_names}},
    )
    return [t["templateid"] for t in result]


def _resolve_group_id(client: ZabbixClient, group_name: str) -> list[str]:
    """Return groupids matching the given name (exact match)."""
    result: list[dict[str, Any]] = client.call(
        "hostgroup.get",
        {"output": ["groupid"], "filter": {"name": group_name}},
    )
    return [g["groupid"] for g in result]
