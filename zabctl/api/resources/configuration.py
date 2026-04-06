"""
Zabbix configuration export/import resource.

Wraps configuration.export and configuration.import API methods.
These are the foundation for template and host config-as-code workflows.

Export returns a raw YAML string (not a JSON-RPC data envelope).
Import takes a YAML string and applies conflict-resolution rules.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from zabctl.api.client import ZabbixClient, ZabbixNotFoundError
from zabctl.api.resources.hosts import _resolve_hostid
from zabctl.api.resources.templates import get_template


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_template(
    client: ZabbixClient,
    template_id_or_name: str,
) -> str:
    """Export a template as a YAML string via configuration.export.

    Returns the raw Zabbix export YAML, suitable for writing to a file
    or passing to import_template / diff_template.
    """
    # Resolve to ID first.
    tmpl = get_template(client, template_id_or_name)
    template_id = tmpl["templateid"]

    result: str = client.call(
        "configuration.export",
        {
            "format": "yaml",
            "options": {"templates": [template_id]},
        },
    )
    return result


def export_host(
    client: ZabbixClient,
    host_id_or_name: str,
) -> str:
    """Export a host definition as a YAML string via configuration.export.

    Includes the host definition (groups, interfaces, macros, tags, linked
    templates) plus directly-assigned items and triggers.
    """
    host_id = _resolve_hostid(client, host_id_or_name)

    result: str = client.call(
        "configuration.export",
        {
            "format": "yaml",
            "options": {"hosts": [host_id]},
        },
    )
    return result


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def import_template(
    client: ZabbixClient,
    yaml_source: str,
    *,
    create_missing: bool = True,
    update_existing: bool = True,
) -> dict[str, Any]:
    """Import a template from a YAML string via configuration.import.

    Conflict resolution defaults:
    - createMissing: True — create templates that don't exist yet
    - updateExisting: True — update templates that already exist
    - deleteMissing: always False — too destructive as a default

    Returns the raw API result (True on success in Zabbix 6.2+; older
    versions may return a different truthy value).
    """
    rules: dict[str, Any] = {
        "templates": {
            "createMissing": create_missing,
            "updateExisting": update_existing,
        },
        "templateDashboards": {
            "createMissing": create_missing,
            "updateExisting": update_existing,
            "deleteMissing": False,
        },
        "templateLinkage": {
            "createMissing": create_missing,
            "deleteMissing": False,
        },
        "items": {
            "createMissing": create_missing,
            "updateExisting": update_existing,
            "deleteMissing": False,
        },
        "discoveryRules": {
            "createMissing": create_missing,
            "updateExisting": update_existing,
            "deleteMissing": False,
        },
        "triggers": {
            "createMissing": create_missing,
            "updateExisting": update_existing,
            "deleteMissing": False,
        },
        "graphs": {
            "createMissing": create_missing,
            "updateExisting": update_existing,
            "deleteMissing": False,
        },
        "httptests": {
            "createMissing": create_missing,
            "updateExisting": update_existing,
            "deleteMissing": False,
        },
        "valueMaps": {
            "createMissing": create_missing,
            "updateExisting": update_existing,
            "deleteMissing": False,
        },
    }

    result: Any = client.call(
        "configuration.import",
        {
            "format": "yaml",
            "rules": rules,
            "source": yaml_source,
        },
    )
    return {"success": bool(result)}


# ---------------------------------------------------------------------------
# Diff / normalization
# ---------------------------------------------------------------------------

# Fields that Zabbix auto-generates and that change between exports even when
# the logical content is identical. Strip these before diffing.
_VOLATILE_KEYS = frozenset({
    "uuid",
    "templateid",
    "hostid",
    "itemid",
    "triggerid",
    "graphid",
    "httptestid",
    "valuemapid",
    "interfaceid",
    "groupid",
    "usrgrpid",
    # Timestamps
    "lastchange",
    "clock",
})


def _normalize(obj: Any) -> Any:
    """Recursively strip volatile keys from a parsed YAML structure."""
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items() if k not in _VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_normalize(item) for item in obj]
    return obj


def _stable_dump(obj: Any) -> str:
    """Dump a normalized object to YAML with stable key ordering."""
    return yaml.dump(
        obj,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=True,
    )


def diff_template(
    client: ZabbixClient,
    template_id_or_name: str,
    local_file: str | Path,
) -> str:
    """Compare the live template against a local YAML file.

    Returns a unified diff string (empty string if identical after normalization).
    Volatile fields (UUIDs, internal IDs) are stripped before comparison so
    only meaningful changes are surfaced.
    """
    import difflib

    # Live export.
    live_yaml = export_template(client, template_id_or_name)
    live_parsed = yaml.safe_load(live_yaml) or {}
    live_normalized = _stable_dump(_normalize(live_parsed))

    # Local file.
    local_path = Path(local_file)
    if not local_path.exists():
        raise FileNotFoundError(f"Local file not found: {local_path}")
    local_parsed = yaml.safe_load(local_path.read_text()) or {}
    local_normalized = _stable_dump(_normalize(local_parsed))

    if live_normalized == local_normalized:
        return ""

    diff = difflib.unified_diff(
        live_normalized.splitlines(keepends=True),
        local_normalized.splitlines(keepends=True),
        fromfile=f"live:{template_id_or_name}",
        tofile=str(local_path),
    )
    return "".join(diff)
