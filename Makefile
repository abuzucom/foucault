.PHONY: sync check lint test identity changelog audit-check

# Overridable so a platform without this name can supply its own:
#   make test PYTHON=py
PYTHON ?= python3

# AUDIT.md is absent on purpose. AGENTS.md exempts the second-person system
# prompt from the governance prose rules. CI runs make lint over this list.
PROSE_FILES = AGENTS.md README.md CHANGELOG.md CONTRIBUTING.md SECURITY.md \
	eval/README.md adopters/README.md docs/gate-threat-model.md \
	docs/template-drift.md docs/pr-quality-review.md \
	docs/pr-security-review.md docs/agent-policy/adoption.md \
	docs/agent-policy/clients.md docs/agent-policy/enforcement.md \
	docs/agent-policy/github.md docs/agent-policy/security.md

sync:
	$(PYTHON) scripts/sync.py

check:
	$(PYTHON) scripts/sync.py --check

changelog:
	$(PYTHON) scripts/check_changelog.py

audit-check:
	$(PYTHON) scripts/check_audit_policy.py
	$(PYTHON) scripts/check_policy_size.py
	$(PYTHON) eval/run_eval.py

lint:
	$(PYTHON) scripts/check_ascii.py $(PROSE_FILES)
	$(PYTHON) scripts/lint_style.py
	$(PYTHON) scripts/check_us_spelling.py $(PROSE_FILES)
	$(PYTHON) scripts/check_english_only.py $(PROSE_FILES)
	$(PYTHON) scripts/check_hedging.py $(PROSE_FILES)
	$(PYTHON) scripts/check_conflict_markers.py

test:
	$(PYTHON) scripts/run_tests.py

identity:
	$(PYTHON) scripts/check_git_identity.py --advise
