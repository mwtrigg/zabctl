"""Zabbix user group resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient

_USERGROUP_OUTPUT = ["usrgrpid", "name", "gui_access", "users_status"]

# gui_access values
_GUI_ACCESS = {"0": "default", "1": "internal", "2": "ldap", "3": "disabled"}
# users_status values
_USERS_STATUS = {"0": "enabled", "1": "disabled"}


def _parse_sort(sort_by: str) -> tuple[str, str]:
    if ":" in sort_by:
        field, order = sort_by.rsplit(":", 1)
        return field, order.upper()
    return sort_by, "ASC"


def get_usergroups(
    client: ZabbixClient,
    *,
    limit: int | None = None,
    sort_by: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return all user groups."""
    params: dict[str, Any] = {
        "output": _USERGROUP_OUTPUT,
        "selectUsers": ["userid", "username"],
        "sortfield": "name",
        "sortorder": "ASC",
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

    result: list[dict[str, Any]] = client.call("usergroup.get", params)
    return result


def get_usergroup(client: ZabbixClient, id_or_name: str) -> dict[str, Any]:
    """Return a single usergroup by usrgrpid or name."""
    params: dict[str, Any] = {"output": _USERGROUP_OUTPUT}
    if id_or_name.isdigit():
        params["usrgrpids"] = [id_or_name]
    else:
        params["filter"] = {"name": id_or_name}
    result: list[dict[str, Any]] = client.call("usergroup.get", params)
    if not result:
        from zabctl.api.client import ZabbixNotFoundError
        raise ZabbixNotFoundError(f"User group not found: {id_or_name!r}")
    return result[0]


def create_usergroup(
    client: ZabbixClient,
    *,
    name: str,
    gui_access: int = 0,
    users_status: int = 0,
) -> dict[str, Any]:
    """Create a user group. Returns the API result dict with usrgrpids."""
    params: dict[str, Any] = {
        "name": name,
        "gui_access": gui_access,
        "users_status": users_status,
    }
    result: dict[str, Any] = client.call("usergroup.create", params)
    return result


def delete_usergroup(client: ZabbixClient, usrgrpid: str) -> dict[str, Any]:
    """Delete a usergroup by numeric usrgrpid. Returns the API result dict with usrgrpids."""
    result: dict[str, Any] = client.call("usergroup.delete", [usrgrpid])
    return result
