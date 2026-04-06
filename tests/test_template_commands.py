"""
Tests for Phase 4 template commands: export, import, diff.

Uses pytest-httpx to mock Zabbix API calls. No live server required.
Follows patterns from tests/test_config.py.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner
from httpx import Request, Response
from pytest_httpx import HTTPXMock

from zabctl.cli import cli


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_SERVER = "http://zabbix.test"
_TOKEN = "test-token"
_API_URL = f"{_SERVER}/api_jsonrpc.php"

# Minimal Zabbix export YAML for a template.
_TEMPLATE_YAML = textwrap.dedent("""\
    zabbix_export:
      version: '6.0'
      templates:
        - uuid: aaaabbbbccccdddd
          template: Linux by Zabbix agent
          name: Linux by Zabbix agent
          description: ''
          items:
            - uuid: 11112222333344445555
              name: System uptime
              key_: system.uptime
              delay: 1m
          triggers:
            - uuid: aabbccdd11223344
              expression: last(/Linux by Zabbix agent/system.uptime)<600
              name: Host has been restarted
              priority: WARNING
""")

# Minimal Zabbix export YAML for a host.
_HOST_YAML = textwrap.dedent("""\
    zabbix_export:
      version: '6.0'
      hosts:
        - uuid: hosthost1111
          host: web01
          name: web01
          status: DISABLED
          interfaces:
            - main: 1
              type: AGENT
              useip: 1
              ip: 127.0.0.1
              dns: ''
              port: '10050'
          groups:
            - name: Linux Servers
          templates:
            - name: Linux by Zabbix agent
          items: []
          triggers: []
""")

# Fake template.get result (what the API returns for a single template).
_TEMPLATE_RECORD = {
    "templateid": "10001",
    "name": "Linux by Zabbix agent",
    "description": "",
    "items": [],
    "triggers": [],
    "graphs": [],
    "items_count": 0,
    "triggers_count": 0,
    "graphs_count": 0,
}


def _rpc_response(result: object, req_id: int = 1) -> dict:
    return {"jsonrpc": "2.0", "result": result, "id": req_id}


def _mock_cfg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point config at test server with token auth; isolate from real config."""
    monkeypatch.setenv("ZABCTL_SERVER", _SERVER)
    monkeypatch.setenv("ZABCTL_API_TOKEN", _TOKEN)
    monkeypatch.setenv("ZABCTL_INSECURE", "false")
    monkeypatch.setattr(
        "zabctl.config.loader.CONFIG_PATH",
        tmp_path / "no_config.yaml",
    )


def _add_api_info(httpx_mock: HTTPXMock) -> None:
    """Add the apiinfo.version response consumed by ZabbixClient.login()."""
    httpx_mock.add_response(url=_API_URL, json=_rpc_response("7.0.0"))


# ---------------------------------------------------------------------------
# template export — template
# ---------------------------------------------------------------------------


def test_template_export_stdout(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """template export <name> prints YAML to stdout."""
    _mock_cfg(monkeypatch, tmp_path)
    _add_api_info(httpx_mock)                                   # login → apiinfo.version
    httpx_mock.add_response(
        url=_API_URL, json=_rpc_response([_TEMPLATE_RECORD])    # template.get
    )
    httpx_mock.add_response(url=_API_URL, json=_rpc_response(_TEMPLATE_YAML))  # config.export

    runner = CliRunner()
    result = runner.invoke(cli, ["template", "export", "Linux by Zabbix agent"])
    assert result.exit_code == 0, result.output
    assert "zabbix_export" in result.output
    assert "Linux by Zabbix agent" in result.output


def test_template_export_to_file(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """template export <name> -f <path> writes YAML to a file."""
    _mock_cfg(monkeypatch, tmp_path)
    out_file = tmp_path / "template.yaml"

    _add_api_info(httpx_mock)
    httpx_mock.add_response(url=_API_URL, json=_rpc_response([_TEMPLATE_RECORD]))
    httpx_mock.add_response(url=_API_URL, json=_rpc_response(_TEMPLATE_YAML))

    runner = CliRunner()
    result = runner.invoke(
        cli, ["template", "export", "Linux by Zabbix agent", "-f", str(out_file)]
    )
    assert result.exit_code == 0, result.output
    assert out_file.exists()
    assert "zabbix_export" in out_file.read_text()


# ---------------------------------------------------------------------------
# template export — host
# ---------------------------------------------------------------------------


def test_template_export_host(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """template export --host <name> exports a host definition."""
    _mock_cfg(monkeypatch, tmp_path)
    _add_api_info(httpx_mock)
    # _resolve_hostid → host.get
    httpx_mock.add_response(
        url=_API_URL,
        json=_rpc_response([{"hostid": "20001", "host": "web01"}]),
    )
    httpx_mock.add_response(url=_API_URL, json=_rpc_response(_HOST_YAML))

    runner = CliRunner()
    result = runner.invoke(cli, ["template", "export", "--host", "web01"])
    assert result.exit_code == 0, result.output
    assert "zabbix_export" in result.output
    assert "web01" in result.output


# ---------------------------------------------------------------------------
# template import
# ---------------------------------------------------------------------------


def test_template_import_success(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """template import <file> calls configuration.import and reports success."""
    _mock_cfg(monkeypatch, tmp_path)
    yaml_file = tmp_path / "template.yaml"
    yaml_file.write_text(_TEMPLATE_YAML)

    _add_api_info(httpx_mock)
    httpx_mock.add_response(url=_API_URL, json=_rpc_response(True))  # config.import

    runner = CliRunner()
    result = runner.invoke(cli, ["template", "import", str(yaml_file), "--yes"])
    assert result.exit_code == 0, result.output


def test_template_import_sends_correct_rules(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """template import sends createMissing+updateExisting rules by default."""
    _mock_cfg(monkeypatch, tmp_path)
    yaml_file = tmp_path / "template.yaml"
    yaml_file.write_text(_TEMPLATE_YAML)

    captured_bodies: list[dict] = []

    def _capture(request: Request) -> Response:
        captured_bodies.append(json.loads(request.content))
        # Return apiinfo.version for login, then True for import.
        idx = len(captured_bodies) - 1
        if idx == 0:
            return Response(200, json=_rpc_response("7.0.0"))
        return Response(200, json=_rpc_response(True))

    httpx_mock.add_callback(_capture, url=_API_URL)
    httpx_mock.add_callback(_capture, url=_API_URL)

    runner = CliRunner()
    runner.invoke(cli, ["template", "import", str(yaml_file), "--yes"])

    import_body = captured_bodies[1]  # [0] is apiinfo.version, [1] is config.import
    assert import_body["method"] == "configuration.import"
    rules = import_body["params"]["rules"]
    assert rules["templates"]["createMissing"] is True
    assert rules["templates"]["updateExisting"] is True
    assert rules["templates"].get("deleteMissing") is not True


def test_template_import_no_update_flag(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """template import --no-update sets updateExisting=False."""
    _mock_cfg(monkeypatch, tmp_path)
    yaml_file = tmp_path / "template.yaml"
    yaml_file.write_text(_TEMPLATE_YAML)

    captured_bodies: list[dict] = []

    def _capture(request: Request) -> Response:
        captured_bodies.append(json.loads(request.content))
        idx = len(captured_bodies) - 1
        if idx == 0:
            return Response(200, json=_rpc_response("7.0.0"))
        return Response(200, json=_rpc_response(True))

    httpx_mock.add_callback(_capture, url=_API_URL)
    httpx_mock.add_callback(_capture, url=_API_URL)

    runner = CliRunner()
    runner.invoke(cli, ["template", "import", str(yaml_file), "--yes", "--no-update"])

    import_body = captured_bodies[1]
    assert import_body["params"]["rules"]["templates"]["updateExisting"] is False


# ---------------------------------------------------------------------------
# template diff
# ---------------------------------------------------------------------------


def test_template_diff_identical(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """template diff reports no differences when content is logically identical."""
    _mock_cfg(monkeypatch, tmp_path)
    local_file = tmp_path / "template.yaml"
    local_file.write_text(_TEMPLATE_YAML)

    _add_api_info(httpx_mock)
    httpx_mock.add_response(url=_API_URL, json=_rpc_response([_TEMPLATE_RECORD]))
    httpx_mock.add_response(url=_API_URL, json=_rpc_response(_TEMPLATE_YAML))

    runner = CliRunner()
    result = runner.invoke(
        cli, ["template", "diff", "Linux by Zabbix agent", str(local_file)]
    )
    assert result.exit_code == 0, result.output
    assert "no differences" in result.output


def test_template_diff_detects_changed_field(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """template diff exits 1 and shows a unified diff when content differs."""
    _mock_cfg(monkeypatch, tmp_path)
    local_yaml = _TEMPLATE_YAML.replace("description: ''", "description: 'local change'")
    local_file = tmp_path / "template.yaml"
    local_file.write_text(local_yaml)

    _add_api_info(httpx_mock)
    httpx_mock.add_response(url=_API_URL, json=_rpc_response([_TEMPLATE_RECORD]))
    httpx_mock.add_response(url=_API_URL, json=_rpc_response(_TEMPLATE_YAML))

    runner = CliRunner()
    result = runner.invoke(
        cli, ["template", "diff", "Linux by Zabbix agent", str(local_file)]
    )
    assert result.exit_code == 1, result.output
    assert "---" in result.output or "+++" in result.output


def test_template_diff_strips_volatile_fields(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """template diff treats UUID-only differences as identical after normalization."""
    _mock_cfg(monkeypatch, tmp_path)
    local_yaml = _TEMPLATE_YAML.replace(
        "uuid: aaaabbbbccccdddd", "uuid: different-uuid-value"
    )
    local_file = tmp_path / "template.yaml"
    local_file.write_text(local_yaml)

    _add_api_info(httpx_mock)
    httpx_mock.add_response(url=_API_URL, json=_rpc_response([_TEMPLATE_RECORD]))
    httpx_mock.add_response(url=_API_URL, json=_rpc_response(_TEMPLATE_YAML))

    runner = CliRunner()
    result = runner.invoke(
        cli, ["template", "diff", "Linux by Zabbix agent", str(local_file)]
    )
    assert result.exit_code == 0, result.output
    assert "no differences" in result.output
