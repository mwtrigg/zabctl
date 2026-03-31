# Changelog

All notable changes to zabctl are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-03-31

### Added
- `enable host <id|name>` / `disable host <id|name>` — toggle host monitoring status.
- `enable trigger <id>` / `disable trigger <id>` — toggle trigger status.
- `acknowledge <event-id> --message <msg>` — acknowledge a problem event; `--close` also closes it.
- `maintenance create` — create a maintenance window (`--host`, `--start`, `--duration`, `--name`, `--no-data`).
- `maintenance delete <id>` — delete a maintenance window.
- `create host` — create a host from flags (`--host`, `--group`, `--template`, `--ip`, `--port`) or `--from-file <yaml>`.
- `delete host <id|name>` — delete a host with confirmation prompt; `--yes` to skip.
- All destructive commands prompt for confirmation and accept `--yes`/`-y` to skip.
- Write commands always emit a human-readable summary to stderr regardless of `--output` setting.
- `llm capabilities` now includes write commands with `mutates` and `confirmation_required` fields.

### Changed
- Extracted `parse_time` / `parse_sort` to `zabctl/api/utils.py` (shared across resource modules).
- Extracted `_make_client` / `_handle_api_error` / `_resolve_output` to `zabctl/cli/_common.py`.

## [0.2.1] - 2026-03-30

### Changed
- `get host <id|name>` now returns richer detail than `get hosts`: adds `tags`, `macros` (user macros), and `parentTemplates` (directly linked templates). Inventory intentionally excluded.

## [0.2.0] - 2026-03-30

### Added
- `ZabbixClient`: full JSON-RPC 2.0 HTTP client with TLS, proxy, API token and user.login auth, context manager support, and `--explain` transparency mode.
- All `get` commands fully functional against live Zabbix: hosts, host, items, triggers, problems, templates, template, latestdata, groups, events, users, user, usergroups.
- `get problems` command (replaces `get alerts`; uses Zabbix `problem.get` API — the live active-problem list).
- `get users` / `get user <id|username>` / `get usergroups` commands (opportunistic addition; not in original Phase 1 spec — added to PHASES.md retroactively).
- `--limit`, `--sort-by FIELD[:desc]`, `--filter KEY=VALUE` flags on all collection commands.
- `--explain` global flag: dumps JSON-RPC requests to stderr for debugging and agent transparency.
- `zabctl completions bash|zsh|fish` — prints shell completion activation line.
- Config `defaults:` block (global and per-context) for setting preferred output, sort order, limit, etc.
- `docker/seed.py` — stdlib-only idempotent Zabbix data seeder (4 groups, 5 hosts).
- `docker/README.md` — local stack setup, seeding, reset, and credential documentation.

### Changed
- Renamed `get alerts` → `get problems` to match Zabbix internal terminology.
- `--acknowledged` on `get problems` now shows only acknowledged problems; default (flag absent) returns all problems regardless of acknowledgement state.
- `get events` description clarified: raw event log, distinct from the active-problem list.
- Version bumped to 0.2.0 (Phase 1 complete per PHASES.md).

## [0.1.0] - 2026-03-01

### Added
- Phase 0 scaffold: project structure, `pyproject.toml`, config loader, auth/context/get/llm CLI stubs, output formatter, and Docker Compose Zabbix 7.0 LTS dev stack.
- Config resolution with strict priority: ENV vars > CLI params > config file.
- `zabctl auth status` — shows current auth configuration state.
- `zabctl context list` / `zabctl context use <name>` — context management from config file.
- `zabctl llm capabilities` — machine-readable command surface for agent bootstrapping.
- `zabctl llm pipeline` — pipeline documentation and examples as JSON.
- `zabctl llm schema <command>` — output schema for a given command.
- Output formatter supporting table, json, jsonl, yaml, wide formats.
- JSON envelope with `data` + `meta` (count, server, api_version, command).
- Pipeline flags on all `get` commands: `--field`, `--stdin-field`, `--from-stdin`, `--batch-size`.
- VS Code workspace config: extensions.json, settings.json, launch.json.
- Docker Compose stack: postgres:16, zabbix-server-pgsql:alpine-7.0-latest, zabbix-web-nginx-pgsql:alpine-7.0-latest, zabbix-agent2:alpine-7.0-latest.

[Unreleased]: https://github.com/mwtrigg/zabctl/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/mwtrigg/zabctl/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/mwtrigg/zabctl/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mwtrigg/zabctl/releases/tag/v0.1.0
