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
        params.update(extra_params)

    result: list[dict[str, Any]] = client.call("usergroup.get", params)
    return result
