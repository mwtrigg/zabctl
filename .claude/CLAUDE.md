# zabctl — Claude Code Instructions

## Project Overview

`zabctl` is a CLI tool for managing Zabbix monitoring environments. It is written in Python,
distributed via PyPI (installed with `uv`), and designed to be consumed by humans and LLM agents
alike. Output must be machine-parseable. The codebase is released under GPL v3.

Primary consumers: the author, a colleague, and LLM agents running in an infrastructure context.

---

## Tech Stack

| Concern | Tool |
|---|---|
| Language | Python 3.12+ |
| CLI framework | Click |
| HTTP client | httpx |
| Config/env | python-dotenv + manual resolution |
| Table output | rich |
| Serialization | PyYAML, stdlib json |
| Package manager | uv |
| Linting/formatting | ruff |
| Type checking | mypy |
| Testing | pytest |
| Distribution | PyPI via `uv publish` |

---

## Repository Layout

```
zabctl/
├── zabctl/
│   ├── __init__.py          # version string only
│   ├── cli/
│   │   ├── __init__.py      # root Click group, --version, global options
│   │   ├── auth.py          # zabctl auth login/logout/status
│   │   ├── context.py       # zabctl context list/use
│   │   └── get.py           # zabctl get hosts/items/triggers/etc.
│   ├── api/
│   │   ├── client.py        # httpx session, JSON-RPC wrapper
│   │   └── resources/
│   │       ├── hosts.py
│   │       ├── items.py
│   │       ├── triggers.py
│   │       ├── problems.py
│   │       ├── templates.py
│   │       ├── events.py
│   │       ├── groups.py
│   │       ├── users.py
│   │       └── usergroups.py
│   ├── config/
│   │   └── loader.py        # env → param → config file resolution
│   └── output/
│       └── formatter.py     # table / json / jsonl / yaml / wide
├── tests/
├── docs/
│   └── PHASES.md
├── docker/
│   └── docker-compose.yml   # local Zabbix dev stack
├── .claude/
│   └── CLAUDE.md            # this file
├── .vscode/
│   ├── extensions.json
│   ├── settings.json
│   └── launch.json
├── pyproject.toml
├── .pre-commit-config.yaml
├── .env.example
├── .gitignore
├── README.md
├── CHANGELOG.md
└── LICENSE                  # GPL v3
```

---

## Configuration

### File Location
`~/.config/zabctl/config.yaml`

### Resolution Order (strict — do not deviate)
1. Environment variables (`ZABCTL_*`)
2. CLI parameters (`--server`, `--token`, etc.)
3. Config file

### Environment Variables

| Variable | Purpose |
|---|---|
| `ZABCTL_SERVER` | Zabbix server URL (e.g. `http://zabbix.local/`) |
| `ZABCTL_API_TOKEN` | API token (preferred for automation/agents) |
| `ZABCTL_USERNAME` | Username (fallback auth) |
| `ZABCTL_PASSWORD` | Password (fallback auth) |
| `ZABCTL_CONTEXT` | Named context to use from config file |
| `ZABCTL_OUTPUT` | Default output format |
| `ZABCTL_INSECURE` | Skip TLS verification (`true`/`false`) |
| `ZABCTL_CA_BUNDLE` | Path to custom CA bundle or directory (PEM) |
| `ZABCTL_CLIENT_CERT` | Path to client certificate file (PEM) for mutual TLS |
| `ZABCTL_CLIENT_KEY` | Path to client private key file (PEM) for mutual TLS |
| `ZABCTL_PROXY` | Proxy URL (e.g. `http://proxy.corp:8080`) — all requests |
| `ZABCTL_NO_PROXY` | Comma-separated hostnames/CIDRs to bypass proxy |

### Config File Format

```yaml
current_context: homelab

contexts:
  homelab:
    server: http://zabbix.homelab/
    api_token: zbx_xxx...          # prefer token over user/pass
    # username: admin              # only if token not available
    # password: ""                 # warn if plaintext password present
    tls:
      insecure: false
      ca_bundle: /etc/ssl/certs/corp-ca.pem   # custom CA or bundle
      client_cert: ~/.config/zabctl/client.crt # mutual TLS cert
      client_key: ~/.config/zabctl/client.key  # mutual TLS key
    proxy:
      http: http://proxy.corp:8080
      https: http://proxy.corp:8080
      no_proxy: localhost,127.0.0.1,.homelab
  production:
    server: https://zabbix.prod.example.com/
    api_token: zbx_yyy...
    tls:
      ca_bundle: /etc/ssl/certs/prod-ca-bundle.pem
    proxy:
      no_proxy: zabbix.prod.example.com
```

### Auth Priority
When both token and username/password are present, **token always wins**.
Emit a warning to stderr if plaintext password is detected in config file.

---

## Output System

### Formats
| Flag | Behavior |
|---|---|
| `table` | Default. Human-readable, colored via Rich |
| `json` | JSON envelope (see below). Primary agent format |
| `jsonl` | Newline-delimited JSON records, no envelope |
| `yaml` | YAML envelope |
| `wide` | Table with additional columns |

### JSON Envelope (all `json` output must conform)
```json
{
  "data": [...],
  "meta": {
    "count": 42,
    "server": "http://zabbix.homelab/",
    "api_version": "6.4.0",
    "command": "get hosts"
  }
}
```

### Global Output Flags
- `--output` / `-o` — format selector
- `--no-headers` — suppress table headers (scripting)
- `--quiet` / `-q` — suppress all output except errors; rely on exit codes

---

## LLM Agent Interface

The `zabctl llm` command group exists specifically for agent bootstrapping and discoverability.
Agents should call `zabctl llm capabilities` on first use to understand the full command surface.
All `llm` subcommand output is always JSON regardless of `--output` setting.

### Agent Bootstrap Sequence
```
1. zabctl llm capabilities          # discover all commands and flags
2. zabctl llm pipeline              # understand composition patterns
3. zabctl llm schema <command>      # get output schema before parsing
4. zabctl <command> --output json   # execute with structured output
```

### `zabctl llm capabilities` Output Shape
```json
{
  "version": "0.2.0",
  "commands": [
    {
      "name": "get hosts",
      "description": "List Zabbix hosts",
      "flags": [...],
      "filters": [...],
      "output_formats": ["table", "json", "jsonl", "yaml", "wide"],
      "pipeable": true,
      "stdin_accepts": null
    }
  ],
  "pipeline_flags": {
    "--field": "Extract a single field from jsonl output for piping",
    "--stdin-field": "Field name to map stdin records to for this command",
    "--from-stdin": "Explicitly read input records from stdin"
  },
  "exit_codes": {
    "0": "success",
    "1": "general error",
    "2": "not found",
    "3": "auth failure",
    "4": "connection error",
    "5": "invalid arguments"
  }
}
```

---

## Pipelining

zabctl supports Unix-style pipelining between commands without requiring `jq` or external tools.

### Pipeline Flags (all commands)
- `--field <name>` — extract a single field from each jsonl record; output is newline-delimited values
- `--stdin-field <name>` — read newline-delimited values from stdin, map to this field for the command
- `--from-stdin` — explicitly read jsonl records from stdin (bypasses TTY detection)
- `--batch-size <n>` — when fanning out from stdin, group into batches for API efficiency (default: 10)

### TTY Detection
If stdin is not a TTY (i.e. data is being piped in), zabctl automatically reads stdin as jsonl.
Use `--from-stdin` to force this behavior explicitly in agent contexts where TTY state is ambiguous.

### Pipeline Examples
```bash
# Get all items for every host in a group
zabctl get hosts --group "Linux Servers" -o jsonl --field host   | zabctl get items --stdin-field host

# Get latest data for hosts matching a search
zabctl get hosts --search "web" -o jsonl --field host   | zabctl get latestdata --stdin-field host

# Acknowledge all active critical problems
zabctl get problems --severity critical -o jsonl --field eventid   | zabctl acknowledge --stdin-field eventid --message "Auto-ack by agent"

# Extract just IPs from hosts for external tooling
zabctl get hosts -o jsonl --field interfaces[0].ip
```

### Exit Code Contract
| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | General / unexpected error |
| 2 | Resource not found |
| 3 | Authentication failure |
| 4 | Connection / network error |
| 5 | Invalid arguments |

Exit codes are stable across versions. Agents may branch on them without parsing stderr.

---

## CLI Structure

```
zabctl
├── --version / -V
├── --output / -o
├── --server
├── --token
├── --username
├── --password
├── --context
├── --insecure
├── --ca-bundle       path to custom CA bundle (PEM)
├── --client-cert     path to client certificate (PEM)
├── --client-key      path to client private key (PEM)
├── --proxy           proxy URL for all requests
├── --no-proxy        comma-separated bypass list
│
├── auth
│   ├── login
│   ├── logout
│   └── status
│
├── context
│   ├── list
│   └── use <name>
│
└── get
    ├── hosts          [--group] [--status] [--search]
    ├── host <id|name>
    ├── items <host>   [--key] [--type] [--status]
    ├── triggers       [--severity] [--host] [--status]
    ├── problems       [--severity] [--host] [--since] [--acknowledged]
    ├── templates      [--search]
    ├── template <id|name>
    ├── latestdata <host>
    ├── groups
    ├── users
    ├── user <id|username>
    ├── usergroups
    └── events         [--host] [--since] [--until] [--limit]
```

---

## API Layer Rules

- All Zabbix API calls go through `zabctl/api/client.py` — never call httpx directly from CLI code
- The client wraps Zabbix's JSON-RPC 2.0 API (`POST /api_jsonrpc.php`)
- Each resource module (`hosts.py`, etc.) exposes typed functions that return Python dicts/lists
- The CLI layer formats output; the API layer never formats output
- The output layer formats data; it never calls the API

This separation exists so a future TUI can use the API layer directly without touching CLI code.

---

## Zabbix API Notes

- Endpoint: `POST <server>/api_jsonrpc.php`
- Auth: session token obtained via `user.login`, passed as `auth` field in every request
- API token (Zabbix 5.4+): passed as `auth` field directly, no login call needed
- JSON-RPC version: `"2.0"`
- Always check `error` key in response before `result`

---

## Versioning

- Semantic versioning: `MAJOR.MINOR.PATCH`
- Version lives in `zabctl/__init__.py` as `__version__ = "0.1.0"`
- `pyproject.toml` reads it dynamically: `dynamic = ["version"]`
- `--version` / `-V` flag on root command reads from package metadata

---

## Code Standards

- Python 3.12+
- All functions typed (mypy strict)
- `ruff` for lint and format — no exceptions
- Tests for all API resource functions (mock httpx)
- Tests for config resolution order
- No plaintext secrets in code, tests, or committed `.env` files
- `.env.example` provided with all variables documented, no values


---

## VS Code Setup

### Required Extensions

Install these extensions before writing any code. Claude Code should create
`.vscode/extensions.json` so VS Code prompts automatically on repo open:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.mypy-type-checker",
    "charliermarsh.ruff",
    "ms-python.debugpy",
    "tamasfe.even-better-toml",
    "redhat.vscode-yaml",
    "ms-azuretools.vscode-docker",
    "mutantdino.resourcemonitor",
    "usernamehw.errorlens",
    "streetsidesoftware.code-spell-checker"
  ]
}
```

| Extension | Purpose |
|---|---|
| `ms-python.python` | Core Python support, IntelliSense |
| `ms-python.mypy-type-checker` | Inline mypy type errors |
| `charliermarsh.ruff` | Linting and formatting (replaces pylint, black, isort) |
| `ms-python.debugpy` | Debugger — set breakpoints and step through CLI commands |
| `tamasfe.even-better-toml` | `pyproject.toml` syntax and validation |
| `redhat.vscode-yaml` | YAML support for config files and compose |
| `ms-azuretools.vscode-docker` | Compose file support, container management sidebar |
| `usernamehw.errorlens` | Inline error messages on the offending line |
| `streetsidesoftware.code-spell-checker` | Catches typos in comments and strings |

### Workspace Settings

Claude Code should create `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit",
    "source.organizeImports.ruff": "explicit"
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "mypy-type-checker.importStrategy": "fromEnvironment",
  "ruff.importStrategy": "fromEnvironment",
  "ruff.lint.enable": true,
  "ruff.format.enable": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/.mypy_cache": true,
    "**/.ruff_cache": true,
    "**/*.pyc": true
  },
  "editor.rulers": [88],
  "yaml.schemas": {
    "https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json": [
      "docker/docker-compose.yml",
      "docker-compose*.yml"
    ]
  }
}
```

### Launch Config for Debugging

Claude Code should create `.vscode/launch.json` so you can set breakpoints
and step through any `zabctl` command directly in VS Code:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "zabctl get hosts",
      "type": "debugpy",
      "request": "launch",
      "module": "zabctl.cli",
      "args": ["get", "hosts", "--output", "json"],
      "console": "integratedTerminal",
      "justMyCode": true
    },
    {
      "name": "zabctl auth status",
      "type": "debugpy",
      "request": "launch",
      "module": "zabctl.cli",
      "args": ["auth", "status"],
      "console": "integratedTerminal",
      "justMyCode": true
    },
    {
      "name": "zabctl llm capabilities",
      "type": "debugpy",
      "request": "launch",
      "module": "zabctl.cli",
      "args": ["llm", "capabilities"],
      "console": "integratedTerminal",
      "justMyCode": true
    },
    {
      "name": "zabctl (custom args)",
      "type": "debugpy",
      "request": "launch",
      "module": "zabctl.cli",
      "args": ["${input:cliArgs}"],
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ],
  "inputs": [
    {
      "id": "cliArgs",
      "type": "promptString",
      "description": "zabctl arguments (space separated)",
      "default": "get hosts --output json"
    }
  ]
}
```

### ruff Configuration

Claude Code should add this to `pyproject.toml` under `[tool.ruff]`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "ARG",  # flake8-unused-arguments
    "SIM",  # flake8-simplify
]
ignore = [
    "E501",  # line length — handled by formatter
]

[tool.ruff.lint.isort]
known-first-party = ["zabctl"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
```

### File Structure Addition

```
zabctl/
├── .vscode/
│   ├── extensions.json    ← auto-prompts extension install on repo open
│   ├── settings.json      ← ruff, mypy, formatter, rulers
│   └── launch.json        ← debug configs for common commands
```

---

## .gitignore

Claude Code must create a `.gitignore` covering all of the following. Nothing in this list
should ever be committed:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.egg
*.egg-info/
dist/
build/
.eggs/
wheels/

# uv
.venv/
.uv/
uv.lock.bak

# Testing
.pytest_cache/
.coverage
htmlcov/
coverage.xml

# Type checking
.mypy_cache/

# Linting
.ruff_cache/

# Secrets and local config — NEVER commit these
.env
docker/.env
*.pem
*.key
*.crt

# VS Code — settings.json and launch.json ARE committed (team defaults)
# extensions.json IS committed (prompts teammates to install)
.vscode/local.*.json

# OS
.DS_Store
Thumbs.db

# Distribution artifacts
*.whl
*.tar.gz
```

**Critical rules:**
- `.env` is gitignored — `.env.example` is committed with all variables documented, no values
- `docker/.env` is gitignored — postgres credentials must never be committed
- `*.pem`, `*.key`, `*.crt` — TLS material must never be committed
- `uv.lock` IS committed — lockfile belongs in version control for reproducible installs

---

## Local Dev Setup

```bash
# Clone and set up
git clone <repo>
cd zabctl
uv sync

# Run locally
uv run zabctl --help

# Run tests
uv run pytest

# Lint + format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy zabctl/

# Start local Zabbix stack
docker compose -f docker/docker-compose.yml up -d
```

---

## Publishing

```bash
uv build
uv publish
```

Version bump flow: edit `zabctl/__init__.py` → update `CHANGELOG.md` → tag → push → publish.

---

## Design Review Checkpoints

These are the key moments to pause Claude Code and bring output back to Claude (claude.ai)
for a design review. Each checkpoint includes the exact commands to run to gather what is needed.

---

### Checkpoint 1 — After Phase 0 Scaffold (before writing any API code)

**When:** Project structure exists, `pyproject.toml` is complete, `uv run zabctl --help` works.

**Why:** Catch structural problems before the API layer is built on top of them.

**Run these commands and paste all output into claude.ai:**

```bash
# Project structure
find . -type f | grep -v __pycache__ | grep -v .git | sort

# Dependency manifest
cat pyproject.toml

# Config loader implementation
cat zabctl/config/loader.py

# Root CLI entrypoint
cat zabctl/cli/__init__.py

# Confirm the tool runs
uv run zabctl --help
uv run zabctl --version
```

---

### Checkpoint 2 — After `client.py` is written (before any resource modules)

**When:** `zabctl/api/client.py` is complete and can make a real JSON-RPC call.

**Why:** The HTTP client is the foundation. TLS, proxy, error handling, and auth all live here.
Mistakes here ripple into every resource module.

**Run these commands and paste all output into claude.ai:**

```bash
# Full client implementation
cat zabctl/api/client.py

# Auth command to confirm login flow works
uv run zabctl auth status
uv run zabctl auth login   # use lab credentials

# Confirm a raw API call works against the lab stack
curl -s -X POST http://localhost:8080/api_jsonrpc.php \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"apiinfo.version","params":{},"id":1}'
```

---

### Checkpoint 3 — After Phase 1 (all `get` commands working)

**When:** All `get` commands return real data from the lab stack.

**Why:** This is the most important review point. The agent surface, pipeline flags,
and output envelope all need to be consistent before Phase 2 builds on them.

**Run these commands and paste all output into claude.ai:**

```bash
# Full LLM capabilities dump — the single most useful artifact
uv run zabctl llm capabilities

# Spot-check output envelope shape
uv run zabctl get hosts --output json
uv run zabctl get triggers --output json

# Pipeline smoke test
uv run zabctl get hosts --output jsonl --field host \
  | uv run zabctl get items --stdin-field host --output json

# Exit code check
uv run zabctl get host nonexistent-host-xyz; echo "exit: $?"
uv run zabctl get hosts --output json 2>/dev/null; echo "exit: $?"

# Test suite results
uv run pytest -v
```

---

### Checkpoint 4 — After Phase 3 (write operations)

**When:** Enable/disable, acknowledge, create, and delete commands are working.

**Why:** Write operations need stricter review — confirmation prompts, `--force` behavior,
stderr messaging in json mode, and exit codes on partial failures.

**Run these commands and paste all output into claude.ai:**

```bash
# Updated capabilities
uv run zabctl llm capabilities

# Dry-run / confirmation behavior check
uv run zabctl delete host some-test-host   # should prompt
uv run zabctl delete host some-test-host --force  # should skip prompt

# Write command JSON output shape
uv run zabctl enable host some-test-host --output json
uv run zabctl acknowledge <problem-id> --message "test" --output json

# Confirm stderr message appears even in json mode
uv run zabctl enable host some-test-host --output json 2>&1

# Full test suite
uv run pytest -v
```

---

### Ad-hoc Review — Any Time Something Feels Off

If a design decision feels awkward in practice, don't push through it.
Run this and bring it to claude.ai with a description of what feels wrong:

```bash
uv run zabctl llm capabilities
uv run zabctl llm pipeline
cat zabctl/api/client.py
cat zabctl/config/loader.py
```

These four artifacts give enough context to diagnose almost any structural issue.
