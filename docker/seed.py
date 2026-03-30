#!/usr/bin/env python3
"""
seed.py — Seed the local Zabbix 7.0 dev stack with realistic test data.

Idempotent: safe to run multiple times. Uses only stdlib (no httpx/requests).

Usage:
    python docker/seed.py
    python docker/seed.py --url http://localhost:8080 --user Admin --password zabbix
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_URL = "http://localhost:8080/api_jsonrpc.php"
DEFAULT_USER = "Admin"
DEFAULT_PASSWORD = "zabbix"

created = 0
existed = 0
failed = 0


# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------

def _rpc(url: str, method: str, params: Any, auth: str | None = None) -> Any:
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }
    if auth:
        payload["auth"] = auth

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
    except urllib.error.URLError as exc:
        print(f"  [error] connection failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if "error" in body:
        raise RuntimeError(body["error"].get("data", body["error"]))

    return body["result"]


def login(url: str, user: str, password: str) -> str:
    token = _rpc(url, "user.login", {"username": user, "password": password})
    assert isinstance(token, str)
    return token


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def _ok(action: str, name: str) -> None:
    global created, existed
    if action == "created":
        created += 1
    else:
        existed += 1
    print(f"  [{action}] {name}")


def _fail(name: str, reason: str) -> None:
    global failed
    failed += 1
    print(f"  [error]   {name}: {reason}", file=sys.stderr)


def _skip(name: str, reason: str) -> None:
    global existed
    existed += 1
    print(f"  [skipped] {name}: {reason}")


# ---------------------------------------------------------------------------
# Host groups
# ---------------------------------------------------------------------------

GROUPS = [
    "Linux Servers",
    "Windows Servers",
    "Network Devices",
    "Database Servers",
]


def ensure_groups(url: str, auth: str) -> dict[str, str]:
    """Return {name: groupid} for all required groups, creating missing ones."""
    print("\n==> Host Groups")
    existing_raw = _rpc(url, "hostgroup.get", {"output": ["groupid", "name"]}, auth)
    existing: dict[str, str] = {g["name"]: g["groupid"] for g in existing_raw}

    result: dict[str, str] = {}
    for name in GROUPS:
        if name in existing:
            _ok("exists", f"group: {name}")
            result[name] = existing[name]
        else:
            try:
                res = _rpc(url, "hostgroup.create", {"name": name}, auth)
                gid = res["groupids"][0]
                _ok("created", f"group: {name}")
                result[name] = gid
            except RuntimeError as exc:
                _fail(f"group: {name}", str(exc))
    return result


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATE_NAMES = [
    "Linux by Zabbix agent",
    "Windows by Zabbix agent",
    "Cisco IOS by SNMP",
]


def fetch_templates(url: str, auth: str) -> dict[str, str]:
    """Return {name: templateid} for templates that exist on this server."""
    raw = _rpc(
        url,
        "template.get",
        {"output": ["templateid", "name"], "filter": {"name": TEMPLATE_NAMES}},
        auth,
    )
    return {t["name"]: t["templateid"] for t in raw}


# ---------------------------------------------------------------------------
# Hosts
# ---------------------------------------------------------------------------

def _host_exists(url: str, auth: str, hostname: str) -> str | None:
    """Return hostid if host exists, else None."""
    res = _rpc(
        url,
        "host.get",
        {"output": ["hostid"], "filter": {"host": [hostname]}},
        auth,
    )
    return res[0]["hostid"] if res else None


def ensure_host(
    url: str,
    auth: str,
    hostname: str,
    ip: str,
    group_ids: list[str],
    template_ids: list[str],
    interface_type: int = 1,  # 1=Agent, 2=SNMP
) -> None:
    existing_id = _host_exists(url, auth, hostname)
    if existing_id:
        _ok("exists", f"host: {hostname}")
        return

    if interface_type == 2:
        interface: dict[str, Any] = {
            "type": 2,        # SNMP
            "main": 1,
            "useip": 1,
            "ip": ip,
            "dns": "",
            "port": "161",
            "details": {
                "version": 2,
                "community": "{$SNMP_COMMUNITY}",
            },
        }
    else:
        interface = {
            "type": 1,        # Agent
            "main": 1,
            "useip": 1,
            "ip": ip,
            "dns": "",
            "port": "10050",
        }

    params: dict[str, Any] = {
        "host": hostname,
        "interfaces": [interface],
        "groups": [{"groupid": gid} for gid in group_ids],
        "templates": [{"templateid": tid} for tid in template_ids],
        "status": 1,  # disabled — no real agent behind these
    }

    try:
        _rpc(url, "host.create", params, auth)
        _ok("created", f"host: {hostname} ({ip})")
    except RuntimeError as exc:
        _fail(f"host: {hostname}", str(exc))


# ---------------------------------------------------------------------------
# Host definitions
# ---------------------------------------------------------------------------

def seed_hosts(
    url: str, auth: str, groups: dict[str, str], templates: dict[str, str]
) -> None:
    print("\n==> Hosts")

    def tids(*names: str) -> list[str]:
        ids = []
        for n in names:
            if n in templates:
                ids.append(templates[n])
            else:
                print(f"  [skipped] template not found, skipping for host binding: {n}")
        return ids

    linux_tid = tids("Linux by Zabbix agent")
    windows_tid = tids("Windows by Zabbix agent")
    cisco_tid = tids("Cisco IOS by SNMP")

    hosts: list[tuple[str, str, list[str], list[str]]] = [
        (
            "web01.lab",
            "10.0.0.11",
            [groups["Linux Servers"]],
            linux_tid,
        ),
        (
            "web02.lab",
            "10.0.0.12",
            [groups["Linux Servers"]],
            linux_tid,
        ),
        (
            "db01.lab",
            "10.0.0.21",
            [groups["Database Servers"]],
            linux_tid,
        ),
        (
            "win-dc01.lab",
            "10.0.0.31",
            [groups["Windows Servers"]],
            windows_tid,
        ),
    ]

    for hostname, ip, gids, tids_list in hosts:
        ensure_host(url, auth, hostname, ip, gids, tids_list)

    # core-sw01.lab needs an SNMP interface for the Cisco template
    ensure_host(
        url, auth,
        "core-sw01.lab", "10.0.0.1",
        [groups["Network Devices"]],
        cisco_tid,
        interface_type=2,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a local Zabbix 7.0 dev stack with test data."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Zabbix API endpoint URL")
    parser.add_argument("--user", default=DEFAULT_USER, help="Zabbix username")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Zabbix password")
    args = parser.parse_args()

    print(f"Connecting to {args.url} as {args.user} ...")
    try:
        auth = login(args.url, args.user, args.password)
    except RuntimeError as exc:
        print(f"[error] login failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Authenticated.")

    groups = ensure_groups(args.url, auth)
    templates = fetch_templates(args.url, auth)

    if not templates:
        print(
            "\n  [warning] no matching templates found — "
            "hosts will be created without template links",
            file=sys.stderr,
        )

    seed_hosts(args.url, auth, groups, templates)

    print(
        f"\n==> Done. created={created} existed={existed} failed={failed}"
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
