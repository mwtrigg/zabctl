"""
Tests for config resolution order: ENV > CLI params > config file.

These tests verify the strict resolution order documented in config/loader.py.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import patch

from zabctl.config.loader import load_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path, content: str) -> Path:
    cfg_dir = tmp_path / ".config" / "zabctl"
    cfg_dir.mkdir(parents=True)
    cfg_file = cfg_dir / "config.yaml"
    cfg_file.write_text(textwrap.dedent(content))
    return cfg_file


# ---------------------------------------------------------------------------
# Config file (lowest priority)
# ---------------------------------------------------------------------------


def test_config_file_values_are_loaded(tmp_path: Path) -> None:
    cfg_file = _write_config(
        tmp_path,
        """
        current_context: lab
        contexts:
          lab:
            server: http://zabbix.lab/
            api_token: zbx_from_file
        """,
    )
    with patch("zabctl.config.loader.CONFIG_PATH", cfg_file):
        cfg = load_config()
    assert cfg.server == "http://zabbix.lab/"
    assert cfg.api_token == "zbx_from_file"


def test_missing_config_file_returns_defaults(tmp_path: Path) -> None:
    nonexistent = tmp_path / "no_such_file.yaml"
    with patch("zabctl.config.loader.CONFIG_PATH", nonexistent):
        cfg = load_config()
    assert cfg.server is None
    assert cfg.api_token is None
    assert cfg.output == "table"


# ---------------------------------------------------------------------------
# CLI params override config file
# ---------------------------------------------------------------------------


def test_cli_params_override_config_file(tmp_path: Path) -> None:
    cfg_file = _write_config(
        tmp_path,
        """
        current_context: lab
        contexts:
          lab:
            server: http://zabbix.lab/
            api_token: zbx_from_file
        """,
    )
    with patch("zabctl.config.loader.CONFIG_PATH", cfg_file):
        cfg = load_config(server="http://zabbix.override/", api_token="zbx_cli")
    assert cfg.server == "http://zabbix.override/"
    assert cfg.api_token == "zbx_cli"


# ---------------------------------------------------------------------------
# ENV vars override CLI params (highest priority)
# ---------------------------------------------------------------------------


def test_env_overrides_cli_params() -> None:
    env = {
        "ZABCTL_SERVER": "http://zabbix.env/",
        "ZABCTL_API_TOKEN": "zbx_env",
    }
    with patch.dict(os.environ, env, clear=False):
        cfg = load_config(server="http://zabbix.cli/", api_token="zbx_cli")
    assert cfg.server == "http://zabbix.env/"
    assert cfg.api_token == "zbx_env"


def test_env_overrides_config_file(tmp_path: Path) -> None:
    cfg_file = _write_config(
        tmp_path,
        """
        current_context: lab
        contexts:
          lab:
            server: http://zabbix.lab/
            api_token: zbx_from_file
        """,
    )
    env = {"ZABCTL_SERVER": "http://zabbix.env/"}
    with (
        patch("zabctl.config.loader.CONFIG_PATH", cfg_file),
        patch.dict(os.environ, env, clear=False),
    ):
        cfg = load_config()
    assert cfg.server == "http://zabbix.env/"
    # api_token from file is still present (only server was overridden by env)
    assert cfg.api_token == "zbx_from_file"


def test_full_priority_chain(tmp_path: Path) -> None:
    """ENV > CLI > config file for every relevant field."""
    cfg_file = _write_config(
        tmp_path,
        """
        current_context: lab
        contexts:
          lab:
            server: http://file.server/
            api_token: zbx_file
        """,
    )
    env = {"ZABCTL_SERVER": "http://env.server/"}
    with (
        patch("zabctl.config.loader.CONFIG_PATH", cfg_file),
        patch.dict(os.environ, env, clear=False),
    ):
        # CLI says http://cli.server/ — but ENV should win
        cfg = load_config(server="http://cli.server/")
    assert cfg.server == "http://env.server/"
    # api_token was only in config file — should be loaded from there
    assert cfg.api_token == "zbx_file"


# ---------------------------------------------------------------------------
# TLS settings
# ---------------------------------------------------------------------------


def test_tls_insecure_from_env() -> None:
    with patch.dict(os.environ, {"ZABCTL_INSECURE": "true"}, clear=False):
        cfg = load_config()
    assert cfg.tls.insecure is True


def test_tls_insecure_false_by_default() -> None:
    cfg = load_config()
    assert cfg.tls.insecure is False


def test_ca_bundle_from_env() -> None:
    with patch.dict(
        os.environ, {"ZABCTL_CA_BUNDLE": "/etc/ssl/corp-ca.pem"}, clear=False
    ):
        cfg = load_config()
    assert cfg.tls.ca_bundle == "/etc/ssl/corp-ca.pem"


# ---------------------------------------------------------------------------
# Context selection
# ---------------------------------------------------------------------------


def test_context_selection_from_cli(tmp_path: Path) -> None:
    cfg_file = _write_config(
        tmp_path,
        """
        current_context: lab
        contexts:
          lab:
            server: http://lab.server/
          prod:
            server: http://prod.server/
        """,
    )
    with patch("zabctl.config.loader.CONFIG_PATH", cfg_file):
        cfg = load_config(context_name="prod")
    assert cfg.server == "http://prod.server/"


def test_context_selection_from_env(tmp_path: Path) -> None:
    cfg_file = _write_config(
        tmp_path,
        """
        current_context: lab
        contexts:
          lab:
            server: http://lab.server/
          prod:
            server: http://prod.server/
        """,
    )
    with (
        patch("zabctl.config.loader.CONFIG_PATH", cfg_file),
        patch.dict(os.environ, {"ZABCTL_CONTEXT": "prod"}, clear=False),
    ):
        cfg = load_config()
    assert cfg.server == "http://prod.server/"


# ---------------------------------------------------------------------------
# Output default
# ---------------------------------------------------------------------------


def test_output_defaults_to_table() -> None:
    cfg = load_config()
    assert cfg.output == "table"


def test_output_from_env() -> None:
    with patch.dict(os.environ, {"ZABCTL_OUTPUT": "json"}, clear=False):
        cfg = load_config()
    assert cfg.output == "json"
