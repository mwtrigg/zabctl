Give me a quick status report without starting any new work.

Read:
- .author/orchestrator/PLAN_STATE.yaml
- .author/orchestrator/BLOCKERS.md
- .author/orchestrator/AGENT_LOG.md (last 20 lines)

Report in this format:

**Phase:** [current phase name and number]
**Progress:** [X of Y tasks complete]
**Last action:** [one line from AGENT_LOG]
**Blockers:** [open count, or "none"]
**PRs open:** [run: gh pr list --label agent]
**Next task:** [what should happen next]

Keep it to 6 lines. Do not start work.
