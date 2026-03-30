# zabctl — TODO & Ideas Tracker

Track ideas, decisions pending, and open questions here.
Move items to PHASES.md once they are scoped and committed.

---

## 🔴 Blocking / Must Decide Before Starting

- [x] **GPL v2 vs v3** — ✅ decided: **GPL v3**. Closes Tivoization loophole; stronger modern copyleft.
- [x] **Zabbix version target** — ✅ decided: **7.0 LTS** (current long-term support release).
- [x] **PyPI package name** — ✅ confirmed: `zabctl` is available on PyPI.

---

## 🟡 Phase 0 Open Items

- [ ] Docker Compose `.env` file strategy — postgres creds, gitignore pattern
- [ ] Decide on pre-seeded Zabbix data for dev (import a template + dummy host on first `up`?)
- [ ] `.env.example` contents — document every `ZABCTL_*` variable with description and example value
- [ ] `CHANGELOG.md` format — Keep a Changelog (keepachangelog.com) is the standard, confirm preference
- [ ] Decide whether to warn or error on missing config file (first-run UX)
- [ ] TLS: test `ca_bundle` as both a single PEM file and a directory (httpx supports both via ssl module)
- [ ] Proxy: confirm behavior when `HTTPS_PROXY` / `HTTP_PROXY` system env vars are set — should `ZABCTL_PROXY` override them or should system vars serve as a lower-priority fallback?
- [ ] Mutual TLS (`client_cert` + `client_key`) — determine if this is needed for Phase 0 or can slip to Phase 1
- [ ] `--insecure` should emit a visible stderr warning every time it is used (not silently skip verification)
- [ ] `zabctl llm capabilities` — decide whether Click introspection is sufficient or if commands need explicit metadata annotations
- [ ] Pipeline stdin: confirm behavior when stdin is a TTY but `--from-stdin` is passed (should error with clear message, not hang)
- [ ] `--field` dotted-path syntax — define supported syntax (e.g. `host`, `interfaces[0].ip`) and document limits
- [ ] Token storage — plaintext in config file for now with a stderr warning, or `keyring` from day one?

---

## 🟢 Phase 1 Open Items

- [ ] Severity mapping — Zabbix uses numeric severity (0–5), decide on display labels and `--severity` filter format (name vs number vs both)
- [ ] `get latestdata` — confirm which API method: `item.get` with `selectLastValues`? Check API version support.
- [ ] Host identity — accept both `hostid` (numeric) and `host` (technical name) and `name` (visible name) in commands? Flag or auto-detect?
- [ ] Timestamp display — Unix epoch vs ISO 8601 in table output? Always ISO in JSON output.
- [x] `get alerts` vs `get problems` — ✅ decided: **`get problems`**. Matches Zabbix internal terminology. Renamed in 0.2.0.

---

## 🟡 Phase 2 Open Items

- [ ] `get host <id|name>` and `get template <id|name>` do not accept piped ids — these single-object commands have `stdin_accepts: null` and will fail silently in pipelines. Add `--from-stdin` support so agents can pipe a list of IDs to them.
- [ ] `auth status` only outputs table format — a JSON output mode would let agents check auth state programmatically without screen-scraping.

---
/
## 💡 Ideas & Future Features (unscheduled)

### Output & UX
- [ ] `--output wide` extra columns — define what "wide" means per resource (e.g., hosts: add IP, agent version, last seen)
- [ ] `--output jsonl` for streaming large result sets to agent pipelines
- [ ] Colorized severity levels in table output (red=disaster, orange=high, etc.)
- [ ] `--watch` polling mode: `zabctl get problems --watch --interval 30`
- [ ] Sparkline graph in terminal for `get latestdata` via Rich

### Agent / Automation Ergonomics
- [ ] `--explain` flag — print the raw JSON-RPC request without executing (Phase 2)
- [ ] `--dry-run` on write commands — show what would happen without doing it
- [ ] Machine-readable exit codes — document a full exit code reference (0=ok, 1=error, 2=not found, 3=auth failure, etc.)
- [ ] `zabctl doctor` — connectivity check, auth test, API version report, config validation

### Multi-Environment
- [ ] `--all-contexts` flag — run a read command across all configured contexts and merge output
- [ ] `context compare` — diff host/trigger counts between two contexts

### TUI (Future Phase)
- [ ] `zabctl tui` — full terminal UI using [Textual](https://textual.textualize.io/)
- [ ] API layer is already abstracted for this — TUI calls same resource functions as CLI

### Config as Code (Phase 4+)
- [ ] `export template` / `import template` YAML roundtrip
- [ ] `diff template` live vs file
- [ ] Git-friendly YAML output (stable key ordering, no timestamps that change every export)

### Distribution
- [ ] `uv tool install zabctl` — test this flow end to end before 1.0
- [ ] GitHub Releases with pre-built wheels for Linux/Mac/Windows
- [ ] Consider PyInstaller single binary as optional release artifact for non-Python users
- [ ] Homebrew tap (post 1.0)

---

## 🗒️ Design Notes & Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| — | GPL v3 | Stronger copyleft than v2; closes Tivoization loophole; standard for new projects |
| — | TLS/proxy first-class | Infra tooling is frequently behind corporate proxies and custom CAs; must work out of the box |
| — | PyPI package name `zabctl` | Confirmed available |
| — | Zabbix 7.0 LTS | Current LTS; better API than 6.4; build against latest from day one |
| — | `zabctl llm` command group | Self-describing CLI prevents doc drift; agents bootstrap from the binary itself |
| — | Pipeline via `--field` / `--stdin-field` | Avoids `jq` dependency; composable without external tooling; works in agent subprocesses |
| — | Click over Typer | More control, Typer is Click underneath anyway |
| — | env → param → config resolution order | Env for automation, params override defaults, config is fallback |
| — | Token over user/pass when both present | Security; agents should never use passwords |
| — | JSON envelope with `data` + `meta` | Consistent for LLM agents; meta carries context |
| — | uv as package manager | Fast; lockfile; uv tool install; uv publish |
| — | `~/.config/zabctl/config.yaml` | XDG-compliant config location |
| — | Python over Go | Learning focus; faster iteration; TUI path exists via Textual |

---

## 🐛 Known Issues / Tech Debt

_Nothing yet — project not started._

---

## 📚 Reference Links

- [Zabbix API Documentation](https://www.zabbix.com/documentation/current/en/manual/api)
- [Click Documentation](https://click.palletsprojects.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [httpx Documentation](https://www.python-httpx.org/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Textual (future TUI)](https://textual.textualize.io/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Zabbix Docker Images](https://hub.docker.com/u/zabbix)
