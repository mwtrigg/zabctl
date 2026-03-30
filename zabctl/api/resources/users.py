"""Zabbix user resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient, ZabbixNotFoundError

_USER_OUTPUT = ["userid", "username", "name", "surname", "roleid"]


def _parse_sort(sort_by: str) -> tuple[str, str]:
    if ":" in sort_by:
        field, order = sort_by.rsplit(":", 1)
        return field, order.upper()
    return sort_by, "ASC"


def get_users(
    client: ZabbixClient,
    *,
    limit: int | None = None,
    sort_by: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return all users."""
    params: dict[str, Any] = {
        "output": _USER_OUTPUT,
        "selectUsrgrps": ["usrgrpid", "name"],
        "sortfield": "username",
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

    result: list[dict[str, Any]] = client.call("user.get", params)
    return result


def get_user(
    client: ZabbixClient,
    user_id_or_name: str,
) -> dict[str, Any]:
    """Return a single user by userid or username."""
    params: dict[str, Any] = {
        "output": _USER_OUTPUT,
        "selectUsrgrps": ["usrgrpid", "name"],
        "selectRole": ["roleid", "name"],
    }

    if user_id_or_name.isdigit():
        params["userids"] = [user_id_or_name]
    else:
        params["filter"] = {"username": user_id_or_name}

    result: list[dict[str, Any]] = client.call("user.get", params)
    if not result:
        raise ZabbixNotFoundError(f"User not found: {user_id_or_name!r}")
    return result[0]
