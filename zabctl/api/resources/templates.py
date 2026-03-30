"""Zabbix template resource — Phase 0 stub."""

from __future__ import annotations

from typing import Any

from zabctl.api.client import ZabbixClient


def get_templates(
    client: ZabbixClient,
    *,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Return templates. Stub: not yet implemented."""
    raise NotImplementedError("templates.get_templates() — Phase 0 stub")


def get_template(
    client: ZabbixClient,
    template_id_or_name: str,
) -> dict[str, Any]:
    """Return a single template by id or name. Stub: not yet implemented."""
    raise NotImplementedError("templates.get_template() — Phase 0 stub")
