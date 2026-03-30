"""
Zabbix JSON-RPC 2.0 API client.

All API calls must go through this module. CLI code must never call httpx directly.
Resource modules call methods on ZabbixClient; the client handles auth, TLS, proxy,
error detection, and JSON-RPC wrapping.

Phase 0: stub implementation — no real network calls.
"""

from __future__ import annotations

from typing import Any

from zabctl.config.loader import ZabctlConfig

_rpc_id = 0


def _next_id() -> int:
    global _rpc_id
    _rpc_id += 1
    return _rpc_id


class ZabbixAPIError(Exception):
    """Raised when the Zabbix API returns an error object."""

    def __init__(self, code: int, message: str, data: str = "") -> None:
        self.code = code
        self.data = data
        super().__init__(
            f"Zabbix API error {code}: {message} — {data}"
            if data
            else f"Zabbix API error {code}: {message}"
        )


class ZabbixAuthError(ZabbixAPIError):
    """Raised on authentication failures (API error codes -32602, -32500, etc.)."""


class ZabbixNotFoundError(Exception):
    """Raised when a resource lookup returns no results."""


class ZabbixClient:
    """
    Thin wrapper around the Zabbix JSON-RPC 2.0 API.

    Endpoint: POST <server>/api_jsonrpc.php
    Auth: session token from user.login, OR a pre-issued API token (Zabbix 5.4+).
    When both token and username/password are present, token always wins.
    """

    def __init__(self, config: ZabctlConfig) -> None:
        self._config = config
        self._session_token: str | None = None
        self._api_version: str = "unknown"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def api_version(self) -> str:
        return self._api_version

    @property
    def server(self) -> str | None:
        return self._config.server

    def call(self, method: str, params: dict[str, Any]) -> Any:
        """
        Execute a Zabbix JSON-RPC method and return the ``result`` value.

        Raises:
            ZabbixAuthError: On authentication/authorization errors.
            ZabbixAPIError: On other API-level errors.
            NotImplementedError: Phase 0 stub — real HTTP call not yet implemented.
        """
        raise NotImplementedError(
            "ZabbixClient.call() is not yet implemented (Phase 0 stub). "
            "Implement the httpx transport in Phase 1."
        )

    def login(self) -> None:
        """
        Authenticate and store the session token.

        If an API token is configured, no login call is needed — the token is used directly.
        If username/password are configured (and no API token), performs user.login.

        Raises:
            ZabbixAuthError: On bad credentials.
            NotImplementedError: Phase 0 stub.
        """
        raise NotImplementedError(
            "ZabbixClient.login() is not yet implemented (Phase 0 stub)."
        )

    def logout(self) -> None:
        """
        Invalidate the current session token (user.logout).
        No-op if using an API token (those are not session-based).

        Raises:
            NotImplementedError: Phase 0 stub.
        """
        raise NotImplementedError(
            "ZabbixClient.logout() is not yet implemented (Phase 0 stub)."
        )

    def api_info(self) -> str:
        """
        Return the Zabbix API version string (apiinfo.version — no auth required).

        Raises:
            NotImplementedError: Phase 0 stub.
        """
        raise NotImplementedError(
            "ZabbixClient.api_info() is not yet implemented (Phase 0 stub)."
        )

    # ------------------------------------------------------------------
    # Internal helpers (implemented in Phase 1)
    # ------------------------------------------------------------------

    def _build_rpc_payload(
        self, method: str, params: dict[str, Any], auth: str | None
    ) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "auth": auth,
            "id": _next_id(),
        }

    def _check_response(self, response: dict[str, Any]) -> Any:
        """
        Raise ZabbixAPIError if the response contains an ``error`` key.
        Returns the ``result`` value otherwise.
        """
        if "error" in response:
            err = response["error"]
            code: int = err.get("code", 0)
            message: str = err.get("message", "unknown error")
            data: str = err.get("data", "")
            if code in (-32602, -32500, -32602):
                raise ZabbixAuthError(code, message, data)
            raise ZabbixAPIError(code, message, data)
        return response.get("result")
