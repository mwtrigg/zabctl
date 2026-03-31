# zabctl — Project Phases

This document is the canonical source of truth for project scope, design decisions, and delivery phases.

---

## Design Decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.12+ | Learning focus; fast iteration; strong ecosystem |
| CLI framework | Click | Battle-tested; fine-grained control; used by major tools |
| Config resolution | env → param → config file | Env wins for automation; explicit params override defaults; config is the fallback |
| Auth preference | API token over user/pass | Safer for agents and automation |
| Output default | `table` | Human-friendly default |
| Output for agents | `--output json` with envelope | Consistent, parseable by LLMs and scripts |
| Package manager | uv | Fast; lockfile; `uv tool install`; `uv publish` |
| Distribution | PyPI | `pip install zabctl` / `uv tool install zabctl` |
| License | GPL v3 | Copyleft — contributions must remain open; closes Tivoization loophole |
| Versioning | Semantic (MAJOR.MINOR.PATCH) | Standard; compatible with PyPI |
| Config location | `~/.config/zabctl/config.yaml` | XDG-compliant |
| Env var prefix | `ZABCTL_` | Namespaced; no collisions |
| TLS / proxy | First-class config, env, and param support | Infra tooling must work behind corporate proxies and custom CAs |
| LLM discoverability | `zabctl llm` command group | Agents bootstrap via `llm capabilities`; always in sync with binary, no doc drift |
| Pipelining | `--field`, `--stdin-field`, TTY detection | Agents and scripts compose commands without requiring `jq` or external tools |

---

## Phase 0 — Lab + Project Foundation

**Goal:** A working local Zabbix environment and a scaffolded, runnable (but mostly stubbed) project.

### 0.1 — Zabbix Docker Stack

File: `docker/docker-compose.yml`

Services:
- `postgres` — database backend, persistent volume
- `zabbix-server-pgsql` — core Zabbix server, exposes port 10051
- `zabbix-web-nginx-pgsql` — web UI + API endpoint, exposes port 8080
- `zabbix-agent2` — agent running on the Docker host for something real to monitor

Notes:
- Web container is required — the JSON-RPC API lives there
- Default credentials: `Admin` / `zabbix` (change after first login)
- API endpoint: `http://localhost:8080/api_jsonrpc.php`
- Persistent volumes for DB data and Zabbix server data
- `.env` file for postgres credentials (gitignored)

Verification checklist:
- [ ] `docker compose up -d` succeeds
- [ ] Web UI reachable at `http://localhost:8080`
- [ ] Agent visible as a host in the UI
- [ ] API responds to a raw `curl` POST

### 0.2 — Project Scaffold

```
zabctl/
├── zabctl/
│   ├── __init__.py          # __version__ = "0.1.0"
│   ├── cli/
│   │   ├── __init__.py      # root group, --version, global options
│   │   ├── auth.py          # stubs
│   │   ├── context.py       # stubs
│   │   └── get.py           # stubs
│   ├── api/
│   │   ├── client.py        # JSON-RPC wrapper (httpx)
│   │   └── resources/
│   │       └── __init__.py
│   ├── config/
│   │   └── loader.py        # resolution logic
│   └── output/
│       └── formatter.py     # format switcher
├── tests/
│   ├── test_config.py
│   └── test_output.py
├── docs/
│   └── PHASES.md            # this file
├── docker/
│   └── docker-compose.yml
├── .claude/
│   └── CLAUDE.md
├── pyproject.toml
├── .pre-commit-config.yaml
├── .env.example
├── .gitignore
├── README.md
├── CHANGELOG.md
└── LICENSE
```

### 0.3 — pyproject.toml

Key fields:
- `[project] name = "zabctl"`
- `dynamic = ["version"]` reading from `zabctl/__init__.py`
- Dependencies: `click`, `httpx`, `rich`, `pyyaml`, `python-dotenv`
- Dev dependencies: `pytest`, `ruff`, `mypy`, `pre-commit`
- Entry point: `zabctl = "zabctl.cli:cli"`
- Requires Python `>=3.12`

### 0.4 — Config System

`zabctl/config/loader.py` implements:

1. Load `ZABCTL_*` env vars
2. Overlay CLI params (passed in from Click context)
3. Load `~/.config/zabctl/config.yaml` for any remaining unset values
4. Resolve active context from `current_context` key or `ZABCTL_CONTEXT`
5. Token takes precedence over user/pass when both present
6. Warn to stderr if plaintext password detected in config file

Config file format:
```yaml
current_context: homelab

contexts:
  homelab:
    server: http://localhost:8080/
    api_token: zbx_xxxxx
  production:
    server: https://zabbix.prod.example.com/
    api_token: zbx_yyyyy
```

### 0.5 — API Client Stub

`zabctl/api/client.py`:
- `ZabbixClient` class wrapping httpx
- `request(method, params)` → JSON-RPC call
- Auto-attach auth token to every request
- Raise typed exceptions on API errors (check `error` key before `result`)
- Configurable timeout and TLS settings
- TLS config via `TLSConfig` dataclass: `ca_bundle`, `client_cert`, `client_key`, `insecure`
- Proxy config via `ProxyConfig` dataclass: `http`, `https`, `no_proxy`
- httpx `SSLContext` built once at init from `TLSConfig`
- Proxy settings passed to httpx `proxies`/`mounts`; `no_proxy` supports hostnames and CIDRs
- Resolution order for all TLS/proxy settings: env var → CLI param → config file (same as auth)

### 0.6 — Auth Commands (wired, not fully functional)

```
zabctl auth login    # prompts for user/pass, stores token in config
zabctl auth logout   # removes cached token
zabctl auth status   # shows server, context, token present/absent
```

### 0.7 — Output System

`zabctl/output/formatter.py`:
- `format_output(data, meta, fmt)` dispatcher
- `table` — Rich table with color
- `json` — envelope: `{"data": [...], "meta": {...}}`
- `jsonl` — one JSON object per line, no envelope
- `yaml` — same structure as json envelope
- `wide` — table with extra columns
- `--no-headers` supported for table/wide
- `--quiet` suppresses all output, only exit codes

### 0.8 — LLM Command Group (stub)

`zabctl/cli/llm.py` — stubbed in Phase 0, completed alongside Phase 1

Commands:
- `zabctl llm capabilities` — introspects registered Click commands and emits full JSON catalog
- `zabctl llm usage <command>` — returns structured usage, examples, and flag descriptions
- `zabctl llm pipeline` — static + generated pipeline pattern documentation in JSON
- `zabctl llm schema <command>` — JSON schema for the output envelope of a given command

Implementation note: `capabilities` should introspect the live Click command tree at runtime
rather than being hand-maintained — ensures it never drifts from actual behavior.

### 0.9 — Pipeline Infrastructure

Implemented in `zabctl/output/formatter.py` and `zabctl/cli/__init__.py`:

- TTY detection: if `sys.stdin.isatty()` is False, attempt to read stdin as jsonl
- `--from-stdin` flag: force stdin reading regardless of TTY state
- `--field <name>` flag: extract a dotted-path field from each jsonl record
- `--stdin-field <name>` flag: map stdin values to this field when building API requests
- `--batch-size <n>` flag: group stdin records into batches (default 10) for API efficiency
- Exit code contract: codes 0–5 defined and stable; documented in `zabctl llm capabilities`

---

## Phase 1 — Core Read (Get) Operations

**Goal:** All primary read commands functional against the local lab stack.

### Commands

| Command | API Method | Key Filters |
|---|---|---|
| `get hosts` | `host.get` | `--group`, `--status`, `--search` |
| `get host <id\|name>` | `host.get` | single object detail |
| `get items <host>` | `item.get` | `--key`, `--type`, `--status` |
| `get triggers` | `trigger.get` | `--severity`, `--host`, `--status` |
| `get problems` | `problem.get` | `--severity`, `--host`, `--since`, `--acknowledged` |
| `get templates` | `template.get` | `--search` |
| `get template <id\|name>` | `template.get` | single object detail |
| `get latestdata <host>` | `item.get` + last value | most recent value per item |
| `get groups` | `hostgroup.get` | — |
| `get events` | `event.get` | `--host`, `--since`, `--until`, `--limit` |
| `get users` | `user.get` | — |
| `get user <id\|username>` | `user.get` | single object detail |
| `get usergroups` | `usergroup.get` | — |

### Resource Modules

Each file in `zabctl/api/resources/` exposes typed functions:
```python
def get_hosts(client, group=None, status=None, search=None) -> list[dict]: ...
```

CLI layer calls resource function → passes result to formatter. No API calls in CLI code.

### Acceptance Criteria
- [ ] All `get` commands return data from local lab in all four output formats
- [ ] `--output json` envelope validates against schema
- [ ] Errors return non-zero exit code and message on stderr
- [ ] `--help` on every command is accurate and complete
- [ ] `zabctl llm capabilities` returns valid JSON covering all Phase 1 commands
- [ ] At least two pipeline examples work end-to-end against the lab stack
- [ ] Exit codes are consistent and match the documented contract

---

## Phase 2 — Filtering, Pagination, Polish ✅ (0.2.0)

**Goal:** Power-user and agent-friendly ergonomics across all get commands.

- `--limit` / `--sort-by <field>` / `--filter key=value` on all collection commands ✅
- Shell completions: `zabctl completions bash|zsh|fish` ✅
- `--explain` flag — prints JSON-RPC requests to stderr (debug/agent transparency) ✅
- Config `defaults:` block (global + per-context) for preferred output, sort, limit ✅
- `get users` / `get user` / `get usergroups` (opportunistic addition) ✅
- Renamed `get alerts` → `get problems` (matches Zabbix internal terminology) ✅

Open items (tracked in TODO.md):
- `auth status --output json` for programmatic auth checks
- `get host` / `get template` / `get user` accepting piped IDs

---

## Phase 2.5 — Detail Views & Polish

**Goal:** Make single-object `get` commands meaningfully richer than their list counterparts.

### `get host <id|name>` — expanded detail ✅ (0.2.1)

Returns additional fields not included in `get hosts`:

| Field | API param | Contents |
|---|---|---|
| `tags` | `selectTags` | Host-level tags (`tag`, `value`) |
| `macros` | `selectMacros` | User macros (`macro`, `value`, `description`) |
| `parentTemplates` | `selectParentTemplates` | Directly linked templates (`templateid`, `name`) |

Note: `selectInventory` intentionally excluded — no identified use case yet.

### Planned

- `get template <id|name>` — add `selectItems`, `selectTriggers`, `selectGraphs` for a full template summary
- `get user <id|username>` — add `selectRole` detail (already fetched; surface in wide columns)
- `auth status --output json` — structured output for agent auth checks

---

## Phase 3 — Write Operations

**Goal:** Basic lifecycle management. Treat destructive operations with care.

| Command | API Method | Notes |
|---|---|---|
| `enable host <id\|name>` | `host.update` | Sets status=0 |
| `disable host <id\|name>` | `host.update` | Sets status=1 |
| `enable trigger <id>` | `trigger.update` | |
| `disable trigger <id>` | `trigger.update` | |
| `acknowledge <problem-id>` | `event.acknowledge` | `--message` required |
| `maintenance create` | `maintenance.create` | `--host`, `--start`, `--duration` |
| `maintenance delete <id>` | `maintenance.delete` | |
| `create host` | `host.create` | `--from-file <yaml>` or interactive |
| `delete host <id\|name>` | `host.delete` | Confirmation prompt; `--force` to skip |

Safety rules:
- All destructive commands prompt for confirmation unless `--force` or `--yes`
- `--output json` on write commands returns the affected object ID(s) in envelope
- Write commands always emit a human-readable summary to stderr even in json mode

---

## Phase 4 — Template & Config Management

**Goal:** Treat Zabbix config as code. Enable GitOps-style workflows.

| Command | Purpose |
|---|---|
| `export template <name>` | Dump template to YAML file |
| `import template <file>` | Push YAML template to server |
| `diff template <name> <file>` | Compare live template vs local file |
| `export host <name>` | Export host config as YAML |

These commands enable version-controlling Zabbix configuration and diffing environments.

---

## Future Ideas (unscheduled)

- TUI mode: `zabctl tui`
- `zabctl llm mcp` — expose zabctl as an MCP tool server so agents can call it natively without subprocess — Bubble Tea equivalent in Python via [Textual](https://textual.textualize.io/)
- Multi-server bulk operations: run a command across all configured contexts
- `watch` mode: `zabctl get problems --watch` (poll and refresh)
- `zabctl get latestdata --graph` — sparkline in terminal via Rich
- OpenTelemetry traces for agent observability
- `zabctl doctor` — validate config, test connectivity, check API version compatibility

---

## Version History

| Version | Phase | Notes |
|---|---|---|
| 0.1.0 | Phase 0 | Scaffold, config system, auth stubs |
| 0.2.0 | Phase 1 + 2 | All get commands, pagination, users/usergroups, config defaults |
| 0.2.1 | Phase 2.5 | get host detail view (tags, macros, templates) |
| 0.3.0 | Phase 3 | Write operations |
| 0.4.0 | Phase 4 | Template management |
| 1.0.0 | — | API stable, docs complete, production-ready |
