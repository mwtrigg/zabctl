"""Zabbix event resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient
from zabctl.api.utils import parse_sort, parse_time

_EVENT_OUTPUT = ["eventid", "source", "object", "objectid", "clock", "value", "acknowledged", "name", "severity"]


def get_events(
    client: ZabbixClient,
    *,
    host: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
    sort_by: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return events."""
    params: dict[str, Any] = {
        "output": _EVENT_OUTPUT,
        "sortfield": "clock",
        "sortorder": "DESC",
        "source": 0,   # trigger events
        "object": 0,   # trigger object
    }

    if host:
        hostids = _resolve_host_id(client, host)
        params["hostids"] = hostids

    if since:
        params["time_from"] = parse_time(since)

    if until:
        params["time_till"] = parse_time(until)

    if limit:
        params["limit"] = limit

    if sort_by:
        field, order = parse_sort(sort_by)
        params["sortfield"] = field
        params["sortorder"] = order

    if extra_params:
        params.update(extra_params)

    result: list[dict[str, Any]] = client.call("event.get", params)
    return result


_ACK_CLOSE = 1         # Close problem
_ACK_ACKNOWLEDGE = 2   # Acknowledge event
_ACK_MESSAGE = 4       # Add message
_ACK_UNACKNOWLEDGE = 16  # Unacknowledge event (Zabbix 5.4+)
_ACK_SUPPRESS = 32     # Suppress event (Zabbix 6.0+)
_ACK_UNSUPPRESS = 64   # Unsuppress event (Zabbix 6.0+)


def acknowledge_event(
    client: ZabbixClient,
    event_id: str,
    message: str | None = None,
    close: bool = False,
    suppress: bool = False,
    unsuppress: bool = False,
    unacknowledge: bool = False,
) -> dict[str, Any]:
    """
    Perform an action on a problem event.

    action bitmask (Zabbix 6.0+):
      1=close, 2=acknowledge, 4=add message,
      16=unacknowledge, 32=suppress, 64=unsuppress
    """
    action = 0

    if suppress:
        action |= _ACK_SUPPRESS
    elif unsuppress:
        action |= _ACK_UNSUPPRESS
    elif unacknowledge:
        action |= _ACK_UNACKNOWLEDGE
    else:
        # Default: acknowledge the event.
        action |= _ACK_ACKNOWLEDGE

    if close:
        action |= _ACK_CLOSE
    if message:
        action |= _ACK_MESSAGE

    params: dict[str, Any] = {"eventids": [event_id], "action": action}
    if message:
        params["message"] = message

    result: dict[str, Any] = client.call("event.acknowledge", params)
    return result


def _resolve_host_id(client: ZabbixClient, host: str) -> list[str]:
    result: list[dict[str, Any]] = client.call(
        "host.get",
        {"output": ["hostid"], "filter": {"host": host}},
    )
    return [h["hostid"] for h in result]
