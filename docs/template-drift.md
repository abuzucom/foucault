# Template drift against abuzucom/agents

`abuzucom/agents` is the org's primary source of truth for AI-development
policy. This file records how foucault's adoption differs from it, per
agents' own `DRIFT.md` convention (`docs/template-drift.md` in the
adopting repository records local differences and reasons).

Pinned commit: `a7a066181a9995a26f5afcec95b0541ce99e9bab`
(`abuzucom/agents`, dated 2026-08-31). `upstream-files.json` records a
per-file hash of every file copied from this commit.

## Expected to differ

- `AGENTS.md` is a bespoke document adapted from `abuzucom/agents`'
  generic template. It keeps the non-negotiable core (parameterization,
  destructive-command authorization, test integrity, scope, draft PRs,
  API compatibility, hashing, secrets, dependency authorization, git
  identity), branch naming, git identity, and the full Style section
  (impersonal voice, terse sentences, no em dash, ASCII-only, American
  spelling, English-only, commit format). It drops container/runtime-root
  rules, dependency-lockfile rules beyond the eval harness's own minimal
  Python needs, concurrency and shared-mutable-state rules, and
  function-size/nesting/line-length code-quality rules. This repository
  has no application code, no Dockerfiles, and no concurrency for those
  rules to govern.
- No `scripts/sync.py`, no generated `CLAUDE.md`/`.cursorrules`/
  `.windsurfrules`/`GEMINI.md`/`CONVENTIONS.md` copies, and no
  `hooks/reinject_agents_policy.py` lifecycle reinjection. `AGENTS.md` is
  the only instruction file for v1. Add a synced copy later, and only if a
  specific tool in active use demonstrably ignores `AGENTS.md`.
- No `.pre-commit-config.yaml`, no `sync-check.yml`,
  `immutable-conflict-check.yml`, or `agents-md-compliance.yml`. This
  repository's own CI (once wired) runs the copied checkers and the eval
  harness directly rather than reusing agents' compliance workflows.
- `tests/test_enforce_branch_name.py` trims its `HOOK_MATCHERS` dict
  from agents' full five-hook matrix (`enforce_branch_name.py`,
  `enforce_git_identity.py`, `block_destructive_bash.py`,
  `block_destructive_powershell.py`, `require_consent.py`) to the two
  hooks foucault actually adopted, per agents' own adoption step 14
  ("adapt settings and wiring assertions when adopting a subset").
  `upstream-files.json` excludes this file because it deliberately departs
  from upstream's byte content.
- `hooks/claude-code-settings.example.json` and `.claude/settings.json`
  carry foucault's own two-hook subset rather than agents' four-hook
  example file content. `upstream-files.json` excludes both for the same
  reason.
- `AUDIT.md` (the product this repository ships) is exempt from
  `AGENTS.md`'s Style section. `AGENTS.md`'s Style section states the
  reasoning. A second-person system prompt by design, it differs from this
  repository's governance prose.

## Not adopted

- `scripts/check_banned_agents.py` (denied-vendor commit/PR-author check).
  Distinct risk (vendor policy enforcement) from the branch/identity
  misbehavior this adoption pass targets. Not copied.
- `hooks/block_destructive_bash.py`, `hooks/block_destructive_powershell.py`
  (destructive-command `PreToolUse` gate). Distinct risk (uncontrolled
  deletion) from branch/identity misbehavior. Not copied.
- `hooks/require_consent.py` (consent gate for direct edits to existing
  test files). Distinct risk (silently weakened tests) from branch/identity
  misbehavior. Not copied. `AGENTS.md` non-negotiable rule 2 covers the
  same ground as a textual rule without the hook.
- `scripts/check_persist_credentials.py`, `scripts/check_dockerfile_root.py`,
  `scripts/check_weak_hashing.py`, `scripts/check_secrets_heuristic.py`,
  `scripts/check_conflict_markers.py`, `scripts/check_compliance_tree.py`,
  `scripts/run_tests.py`, `scripts/check_hook_coverage.py`,
  `scripts/check_commit_message.py`, `scripts/check_pull_request_message.py`,
  `scripts/sync.py`. Not relevant to a repository with no application code,
  no Dockerfiles, and no multi-tool instruction sync.
- `plan/HANDOFF.md.example` and its handoff-exempt prose-policy carve-out.
  Not adopted; `scripts/prose_bans.txt`'s `[handoff-exempt]` section stays
  present verbatim (it is a shared, hash-tracked file) but is inert here
  since no `plan/HANDOFF.md.example` exists to exempt.

## True drift

None recorded. This section tracks a copied file's content diverging from
its pinned upstream commit over time. Run
`python scripts/check_upstream_drift.py --check-upstream --agents-path <checkout>`
periodically (before each foucault release) and record any finding here
with the reviewed outcome (adopted, declined, or partially adapted, and
why). Update `upstream-files.json`'s pinned commit after review either way.
Keeping the pin current keeps the record honest. For a foucault-side difference that looks like
it should upstream instead, open an issue in `abuzucom/agents` naming the
file and reason, per agents' own `DRIFT.md` "Opening a drift issue"
process.
