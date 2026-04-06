"""
Tests for Phase 3.6 user/group write commands: create user, delete user,
create usergroup, delete usergroup.

Uses pytest-httpx to mock Zabbix API calls. No live server required.
Follows patterns from tests/test_template_commands.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
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


def _rpc_response(result: object, req_id: int = 1) -> dict:
    return {"jsonrpc": "2.0", "result": result, "id": req_id}


def _mock_cfg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ZABCTL_SERVER", _SERVER)
    monkeypatch.setenv("ZABCTL_API_TOKEN", _TOKEN)
    monkeypatch.setenv("ZABCTL_INSECURE", "false")
    monkeypatch.setattr(
        "zabctl.config.loader.CONFIG_PATH",
        tmp_path / "no_config.yaml",
    )


def _add_api_info(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=_API_URL, json=_rpc_response("7.0.0"))


# Sample API records.
_ROLE_RECORD = {"roleid": "2", "name": "Zabbix User"}
_GROUP_RECORD = {"usrgrpid": "8", "name": "Linux Team", "gui_access": "0", "users_status": "0"}
_USER_RECORD = {"userid": "5", "username": "alice", "name": "", "surname": "", "roleid": "2"}
_USERGROUP_RECORD = {"usrgrpid": "9", "name": "Ops Team", "gui_access": "0", "users_status": "0"}


# ---------------------------------------------------------------------------
# create user — success
# ---------------------------------------------------------------------------


def test_create_user_returns_userid(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """create user resolves role + group and returns the new userid."""
    _mock_cfg(monkeypatch, tmp_path)
    _add_api_info(httpx_mock)                                        # login
    httpx_mock.add_response(url=_API_URL, json=_rpc_response([_ROLE_RECORD]))   # role.get
    httpx_mock.add_response(url=_API_URL, json=_rpc_response([_GROUP_RECORD]))  # usergroup.get
    httpx_mock.add_response(url=_API_URL, json=_rpc_response({"userids": ["5"]}))  # user.create

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "user", "--username", "alice", "--password", "s3cr3t",
         "--role", "Zabbix User", "--group", "Linux Team", "--yes"],
    )
    assert result.exit_code == 0, result.output


def test_create_user_sends_correct_payload(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """create user sends username, passwd, roleid, usrgrps to user.create."""
    _mock_cfg(monkeypatch, tmp_path)

    captured: list[dict] = []

    def _capture(request: Request) -> Response:
        captured.append(json.loads(request.content))
        idx = len(captured) - 1
        if idx == 0:
            return Response(200, json=_rpc_response("7.0.0"))    # apiinfo.version
        if idx == 1:
            return Response(200, json=_rpc_response([_ROLE_RECORD]))  # role.get
        if idx == 2:
            return Response(200, json=_rpc_response([_GROUP_RECORD]))  # usergroup.get
        return Response(200, json=_rpc_response({"userids": ["5"]}))   # user.create

    for _ in range(4):
        httpx_mock.add_callback(_capture, url=_API_URL)

    CliRunner().invoke(
        cli,
        ["create", "user", "--username", "alice", "--password", "s3cr3t",
         "--role", "Zabbix User", "--group", "Linux Team", "--yes"],
    )

    create_body = captured[3]
    assert create_body["method"] == "user.create"
    params = create_body["params"]
    assert params["username"] == "alice"
    assert params["passwd"] == "s3cr3t"
    assert params["roleid"] == "2"
    assert params["usrgrps"] == [{"usrgrpid": "8"}]


# ---------------------------------------------------------------------------
# create user — hardblock: Admin username
# ---------------------------------------------------------------------------


def test_create_user_blocks_admin(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """create user refuses to create a user named 'Admin'."""
    _mock_cfg(monkeypatch, tmp_path)
    # No API calls needed — block fires before any network call.

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["create", "user", "--username", "Admin", "--password", "x",
         "--role", "1", "--group", "g", "--yes"],
    )
    assert result.exit_code == 5
    assert "protected" in result.output.lower() or "protected" in (result.output + "").lower()


# ---------------------------------------------------------------------------
# delete user — success
# ---------------------------------------------------------------------------


def test_delete_user_calls_user_delete(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """delete user resolves the user and calls user.delete."""
    _mock_cfg(monkeypatch, tmp_path)
    _add_api_info(httpx_mock)                                                   # login
    httpx_mock.add_response(url=_API_URL, json=_rpc_response([_USER_RECORD]))   # user.get (resolve)
    httpx_mock.add_response(url=_API_URL, json=_rpc_response(None))             # user.checkAuthentication (current_user_info — returns None → no error needed)
    httpx_mock.add_response(url=_API_URL, json=_rpc_response({"userids": ["5"]}))  # user.delete

    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "user", "alice", "--yes"])
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# delete user — hardblock: Admin
# ---------------------------------------------------------------------------


def test_delete_user_blocks_admin(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """delete user refuses to delete the Admin account."""
    _mock_cfg(monkeypatch, tmp_path)
    _add_api_info(httpx_mock)
    admin_record = {**_USER_RECORD, "username": "Admin", "userid": "1"}
    httpx_mock.add_response(url=_API_URL, json=_rpc_response([admin_record]))   # user.get

    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "user", "Admin", "--yes"])
    assert result.exit_code == 5
    assert "protected" in result.output.lower()


# ---------------------------------------------------------------------------
# delete user — hardblock: token-owner
# ---------------------------------------------------------------------------


def test_delete_user_blocks_token_owner(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """delete user refuses when the target is the currently authenticated user."""
    _mock_cfg(monkeypatch, tmp_path)
    _add_api_info(httpx_mock)
    httpx_mock.add_response(url=_API_URL, json=_rpc_response([_USER_RECORD]))   # user.get (resolve)
    # user.checkAuthentication returns alice as current user.
    httpx_mock.add_response(
        url=_API_URL,
        json=_rpc_response({**_USER_RECORD, "username": "alice"}),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "user", "alice", "--yes"])
    assert result.exit_code == 5
    assert "currently authenticated" in result.output.lower()


# ---------------------------------------------------------------------------
# create usergroup — success
# ---------------------------------------------------------------------------


def test_create_usergroup_success(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """create usergroup calls usergroup.create and reports the new usrgrpid."""
    _mock_cfg(monkeypatch, tmp_path)
    _add_api_info(httpx_mock)
    httpx_mock.add_response(url=_API_URL, json=_rpc_response({"usrgrpids": ["9"]}))

    runner = CliRunner()
    result = runner.invoke(cli, ["create", "usergroup", "--name", "Ops Team", "--yes"])
    assert result.exit_code == 0, result.output


def test_create_usergroup_sends_correct_payload(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """create usergroup sends name, gui_access, users_status to usergroup.create."""
    _mock_cfg(monkeypatch, tmp_path)

    captured: list[dict] = []

    def _capture(request: Request) -> Response:
        captured.append(json.loads(request.content))
        idx = len(captured) - 1
        if idx == 0:
            return Response(200, json=_rpc_response("7.0.0"))
        return Response(200, json=_rpc_response({"usrgrpids": ["9"]}))

    httpx_mock.add_callback(_capture, url=_API_URL)
    httpx_mock.add_callback(_capture, url=_API_URL)

    CliRunner().invoke(
        cli,
        ["create", "usergroup", "--name", "Read-Only", "--gui-access", "internal", "--disabled", "--yes"],
    )

    create_body = captured[1]
    assert create_body["method"] == "usergroup.create"
    params = create_body["params"]
    assert params["name"] == "Read-Only"
    assert params["gui_access"] == 1   # internal
    assert params["users_status"] == 1  # disabled


# ---------------------------------------------------------------------------
# delete usergroup — success
# ---------------------------------------------------------------------------


def test_delete_usergroup_success(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """delete usergroup resolves the group and calls usergroup.delete."""
    _mock_cfg(monkeypatch, tmp_path)
    _add_api_info(httpx_mock)
    httpx_mock.add_response(url=_API_URL, json=_rpc_response([_USERGROUP_RECORD]))  # usergroup.get
    httpx_mock.add_response(url=_API_URL, json=_rpc_response({"usrgrpids": ["9"]}))  # usergroup.delete

    runner = CliRunner()
    result = runner.invoke(cli, ["delete", "usergroup", "Ops Team", "--yes"])
    assert result.exit_code == 0, result.output
