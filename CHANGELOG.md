# Changelog

All notable changes to zabctl are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 0 scaffold: project structure, `pyproject.toml`, config loader, auth/context/get/llm CLI stubs, output formatter, and Docker Compose Zabbix 7.0 LTS dev stack.
- Config resolution with strict priority: ENV vars > CLI params > config file.
- `zabctl auth status` — shows current auth configuration state.
- `zabctl context list` / `zabctl context use <name>` — context management from config file.
- `zabctl get` command group with all subcommands stubbed (hosts, host, items, triggers, alerts, templates, template, latestdata, groups, events).
- `zabctl llm capabilities` — machine-readable command surface for agent bootstrapping.
- `zabctl llm pipeline` — pipeline documentation and examples as JSON.
- `zabctl llm schema <command>` — output schema for a given command.
- Output formatter supporting table, json, jsonl, yaml, wide formats.
- JSON envelope with `data` + `meta` (count, server, api_version, command).
- Pipeline flags on all `get` commands: `--field`, `--stdin-field`, `--from-stdin`, `--batch-size`.
- VS Code workspace config: extensions.json, settings.json, launch.json.
- Docker Compose stack: postgres:16, zabbix-server-pgsql:alpine-7.0-latest, zabbix-web-nginx-pgsql:alpine-7.0-latest, zabbix-agent2:alpine-7.0-latest.

[Unreleased]: https://github.com/mwtrigg/zabctl/compare/HEAD...HEAD
