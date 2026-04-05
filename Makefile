.PHONY: help status blockers log check-env

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  %-22s %s\n", $$1, $$2}'

status: ## Show plan state and open blockers
	@echo "=== PLAN STATE ===" && cat .author/orchestrator/PLAN_STATE.yaml
	@echo "" && echo "=== OPEN BLOCKERS ===" \
		&& grep -A6 "Status: OPEN" .author/orchestrator/BLOCKERS.md \
		|| echo "  None"

blockers: ## Show all blockers
	@cat .author/orchestrator/BLOCKERS.md

log: ## Show recent agent log entries
	@tail -60 .author/orchestrator/AGENT_LOG.md

check-env: ## Check .env exists
	@test -f .env \
		&& echo "  .env found" \
		|| echo "  WARNING: .env missing — copy .env.example"
