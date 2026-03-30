"""
Zabbix JSON-RPC 2.0 API client.

All API calls must go through this module. CLI code must never call httpx directly.
Resource modules call methods on ZabbixClient; the client handles auth, TLS, proxy,
error detection, and JSON-RPC wrapping.
"""

from __future__ import annotations

import contextlib
import ssl
from typing import Any

import httpx

from zabctl.config.loader import ZabctlConfig

# NOTE: not thread-safe — zabctl is a single-threaded CLI tool, this is intentional
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


# Auth error codes returned by Zabbix
_AUTH_ERROR_CODES = {-32602, -32500, -32600}


def _build_ssl_context(
    insecure: bool,
    ca_bundle: str | None,
    client_cert: str | None,
    client_key: str | None,
) -> ssl.SSLContext | bool:
    """Build an SSL context from TLS config. Returns False to disable verification."""
    if insecure:
        return False

    ctx = ssl.create_default_context()
    if ca_bundle:
        ctx.load_verify_locations(cafile=ca_bundle)
    if client_cert and client_key:
        ctx.load_cert_chain(certfile=client_cert, keyfile=client_key)
    elif client_cert:
        ctx.load_cert_chain(certfile=client_cert)
    return ctx


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
        self._http: httpx.Client = self._build_http_client()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def api_version(self) -> str:
        return self._api_version

    @property
    def server(self) -> str | None:
        return self._config.server

    def api_info(self) -> str:
        """Return the Zabbix API version string (no auth required)."""
        result = self._send("apiinfo.version", {}, auth=None)
        assert isinstance(result, str)
        self._api_version = result
        return result

    def login(self) -> None:
        """
        Authenticate and store the session token.

        If an API token is configured, no login call is needed — the token is
        used directly. If username/password are configured, performs user.login.
        """
        if self._config.api_token:
            # API token is used directly; no user.login call required.
            self._session_token = self._config.api_token
            # Fetch API version as a connectivity check (best-effort).
            with contextlib.suppress(Exception):
                self.api_info()
            return

        if not self._config.username:
            raise ZabbixAuthError(0, "No credentials configured (set api_token or username)")

        password = self._config.password or ""
        result = self._send(
            "user.login",
            {"username": self._config.username, "password": password},
            auth=None,
        )
        if not isinstance(result, str):
            raise ZabbixAuthError(0, "user.login returned unexpected result")
        self._session_token = result
        with contextlib.suppress(Exception):
            self.api_info()

    def logout(self) -> None:
        """
        Invalidate the current session token (user.logout).
        No-op if using an API token (those are not session-based).
        """
        if not self._session_token:
            return
        # API tokens are not session-based; only invalidate user.login sessions.
        if self._config.api_token:
            self._session_token = None
            return
        self._send("user.logout", {}, auth=self._session_token)
        self._session_token = None

    def __enter__(self) -> ZabbixClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self._http.close()

    def call(self, method: str, params: dict[str, Any]) -> Any:
        """
        Execute a Zabbix JSON-RPC method and return the ``result`` value.

        Raises:
            ZabbixAuthError: On authentication/authorization errors.
            ZabbixAPIError: On other API-level errors.
            httpx.ConnectError / httpx.TimeoutException: On network failures.
        """
        return self._send(method, params, auth=self._session_token)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_http_client(self) -> httpx.Client:
        tls = self._config.tls
        proxy = self._config.proxy

        ssl_context = _build_ssl_context(
            insecure=tls.insecure,
            ca_bundle=tls.ca_bundle,
            client_cert=tls.client_cert,
            client_key=tls.client_key,
        )

        # Build per-scheme proxy mounts.
        mounts: dict[str, httpx.BaseTransport | None] = {}
        if proxy.http:
            mounts["http://"] = httpx.HTTPTransport(proxy=proxy.http)
        if proxy.https:
            mounts["https://"] = httpx.HTTPTransport(proxy=proxy.https)
        if proxy.no_proxy:
            for host in proxy.no_proxy.split(","):
                host = host.strip()
                if host:
                    mounts[f"http://{host}"] = None
                    mounts[f"https://{host}"] = None

        kwargs: dict[str, Any] = {
            "verify": ssl_context,
            "timeout": 30.0,
            "headers": {"Content-Type": "application/json"},
        }
        if mounts:
            kwargs["mounts"] = mounts

        return httpx.Client(**kwargs)

    def _endpoint(self) -> str:
        server = (self._config.server or "").rstrip("/")
        if not server:
            raise ZabbixAuthError(0, "No server configured (set ZABCTL_SERVER or --server)")
        return f"{server}/api_jsonrpc.php"

    def _build_rpc_payload(
        self, method: str, params: dict[str, Any], auth: str | None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": _next_id(),
        }
        if auth is not None:
            payload["auth"] = auth
        return payload

    def _check_response(self, response: dict[str, Any]) -> Any:
        """Raise ZabbixAPIError if the response contains an ``error`` key."""
        if "error" in response:
            err = response["error"]
            code: int = err.get("code", 0)
            message: str = err.get("message", "unknown error")
            data: str = err.get("data", "")
            if code in _AUTH_ERROR_CODES:
                raise ZabbixAuthError(code, message, data)
            raise ZabbixAPIError(code, message, data)
        return response.get("result")

    def _send(self, method: str, params: dict[str, Any], auth: str | None) -> Any:
        payload = self._build_rpc_payload(method, params, auth)
        try:
            resp = self._http.post(self._endpoint(), json=payload)
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise httpx.ConnectError(
                f"Cannot connect to Zabbix server at {self._config.server}: {exc}"
            ) from exc
        body: dict[str, Any] = resp.json()
        return self._check_response(body)
