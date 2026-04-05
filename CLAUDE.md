# Agent Instructions

Before doing anything else, read:

  .author/PROJECT_WELCOME.md

All orchestrator state, agent instructions, task tracking, and project
context live in `.author/`. That directory is not committed to this repo.

## What lives where

| Location | Contents |
|---|---|
| `.author/PROJECT_WELCOME.md` | Project context, rules, current phase |
| `.author/orchestrator/PLAN_STATE.yaml` | Phase and task tracking |
| `.author/orchestrator/AGENT_LOG.md` | Append-only action log |
| `.author/orchestrator/BLOCKERS.md` | Items requiring human input |
| `.author/orchestrator/BRANCH_REGISTRY.yaml` | Active agent/ branches |
| `.author/agents/CONVENTIONS.md` | Agent rules and sub-agent roster |
| `.author/scratch/` | Test outputs, notes, artifacts |

## Hard rules

- All branches in this repo: `agent/<descriptive-name>`
- Never commit to `main` directly
- Never create an `orchestrator/` directory in this repo
- Never commit agent tracking files here — everything goes through `.author/`
- Secrets never in git — env vars or `.env` only
- When blocked: write to `.author/orchestrator/BLOCKERS.md`, skip, continue

## Single-agent mode

If you cannot spawn sub-agents, you are the orchestrator and all sub-agents
simultaneously. Work one PLAN_STATE task at a time. Update PLAN_STATE.yaml
and AGENT_LOG.md after each task. Skip the signals/ directory entirely.
Branch and PR conventions still apply — they are about git hygiene, not
multi-agent coordination. See `.author/agents/CONVENTIONS.md` for the full
single-agent operating model.
