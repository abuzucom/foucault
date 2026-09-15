# Template drift against abuzucom/agents

`abuzucom/agents` is the upstream source for the adopted agent policy and
enforcement bundle. This repository adopts commit
`e1408dcfae9c8c714e8522d8236b58b6345ef2ba`, released upstream as 2.0.20.

The 2026-09-15 reconciliation audited upstream `main` at `ad632c4`.
The audit covered the complete GitHub wrapper path from argument validation
through repository context injection, authentication, execution, bounded
output, and failure classification.

## Adopted

- The complete upstream policy rules remain in `AGENTS.md`.
- Supporting policy documents live under `docs/agent-policy/`.
- The complete command, infrastructure, consent, lifecycle, branch, identity,
  and GitHub gate set lives under `hooks/`.
- Portable checkers, synchronization tooling, and trusted Git tooling live
  under `scripts/`.
- Shared gate files use `shared-files.json`.
- Gate tests and hook coverage tooling live under `tests/` and `tools/`.
- Claude, Codex, Gemini, and Antigravity configurations are installed.

## Locally adapted

- `AGENTS.md` omits upstream repository-only orientation and retains
  Foucault-specific audit, evaluator, fixture, and provenance rules.
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and
  `docs/gate-threat-model.md` describe this repository's product and CI.
- `scripts/trusted_gh.py` preserves Foucault's bounded diagnostics and token
  output denial while adopting current upstream repository-context routing.
- The wrapper retains attached and separated token-output denial, literal
  escape-text denial, sanitized exception text, and repository-local executable
  exclusion. These protections remain intentional local adaptations.
- Wrapper context injection receives a second gate evaluation after validated
  `--repo` and `--head` arguments are added. Explicit targets remain unchanged.
- Linked worktrees use common Git metadata resolution. Detached heads remain
  invalid for pull request head injection.
- `scripts/check_gate_adoption.py` validates all four client configurations.
- `.github/workflows/ci.yml` combines upstream checks with Foucault's eval and
  security-review jobs.
- `.github/workflows/ci.yml` and `.pre-commit-config.yaml` adapt the upstream
  test-first checker to the existing local workflow.
- `README.md`, `docs/agent-policy/enforcement.md`, and
  `docs/agent-policy/github.md` describe runtime approval and test-first
  boundaries for the newer upstream contract.
- Existing evaluator, delivery, workflow, and trusted GitHub tests remain
  alongside the upstream gate tests.

## Not adopted

- Upstream source-repository orientation in `AGENTS.md`.
- Upstream source-repository adopter records and example security documents.
- Upstream reusable compliance workflow files. Their checks are integrated
  into this repository's existing CI.
- Upstream `sync-check.yml`. Its new test-first step is integrated into the
  existing local CI and pre-commit configuration.
- The upstream project's own README, changelog, license, and project-only
  examples.

These omissions do not remove an applicable policy rule or enforcement gate.
They record repository-specific ownership and workflow choices.

## Drift review

`upstream-files.json` records exact adopted files and their normalized
SHA-256 hashes. `scripts/check_upstream_drift.py --check-local` detects local
changes to those files. Review the adopted source against the pinned commit
before changing the pin. Record every file as adopted, adapted, or declined.

`shared-files.json` records the local integrity hashes for files that must
remain identical across controlled adopters. Run
`python scripts/sync.py --check-shared` after every shared gate change.

The reconciliation changed four locally adapted files and refreshed their
normalized hashes in `upstream-files.json`. The manifest repair keeps CI's
local drift check aligned with the reviewed source. It does not replace
Foucault adaptations with upstream removals.
