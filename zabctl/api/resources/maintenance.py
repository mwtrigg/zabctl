"""Zabbix maintenance resource."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient, ZabbixNotFoundError


def create_maintenance(
    client: ZabbixClient,
    *,
    name: str,
    host_ids: list[str],
    start_epoch: int,
    duration_minutes: int,
    no_data: bool = False,
) -> dict[str, Any]:
    """Create a maintenance window. Returns {"maintenanceids": [...]}."""
    active_till = start_epoch + duration_minutes * 60
    result: dict[str, Any] = client.call(
        "maintenance.create",
        {
            "name": name,
            "active_since": start_epoch,
            "active_till": active_till,
            "hostids": host_ids,
            "timeperiods": [
                {
                    "timeperiod_type": 0,  # one-time
                    "start_date": start_epoch,
                    "period": duration_minutes * 60,
                }
            ],
            "maintenance_type": 1 if no_data else 0,  # 0=with data, 1=no data
        },
    )
    return result


def delete_maintenance(client: ZabbixClient, maintenance_id: str) -> dict[str, Any]:
    """Delete a maintenance window. Returns {"maintenanceids": [...]}."""
    result: dict[str, Any] = client.call("maintenance.delete", [maintenance_id])
    return result


def get_maintenances(
    client: ZabbixClient,
    *,
    host_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return maintenance windows, optionally filtered by host."""
    params: dict[str, Any] = {
        "output": ["maintenanceid", "name", "active_since", "active_till", "maintenance_type"],
        "selectHosts": ["hostid", "host"],
    }
    if host_ids:
        params["hostids"] = host_ids
    result: list[dict[str, Any]] = client.call("maintenance.get", params)
    return result


def _resolve_maintenance_id(client: ZabbixClient, maintenance_id_or_name: str) -> str:
    """Return maintenanceid for a given id or name."""
    if maintenance_id_or_name.isdigit():
        return maintenance_id_or_name
    result: list[dict[str, Any]] = client.call(
        "maintenance.get",
        {"output": ["maintenanceid"], "filter": {"name": maintenance_id_or_name}},
    )
    if not result:
        raise ZabbixNotFoundError(f"Maintenance not found: {maintenance_id_or_name!r}")
    return str(result[0]["maintenanceid"])
