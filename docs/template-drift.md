# Template drift against abuzucom/agents

`abuzucom/agents` is the upstream source for the adopted agent policy and
enforcement bundle. This repository adopts commit
`7de83d04224784774dcfd1a21462bf23315bdeae`, released upstream as 2.0.20.

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
  output denial while adopting current upstream routing behavior.
- `scripts/check_gate_adoption.py` validates all four client configurations.
- `.github/workflows/ci.yml` combines upstream checks with Foucault's eval and
  security-review jobs.
- Existing evaluator, delivery, workflow, and trusted GitHub tests remain
  alongside the upstream gate tests.

## Not adopted

- Upstream source-repository orientation in `AGENTS.md`.
- Upstream source-repository adopter records and example security documents.
- Upstream reusable compliance workflow files. Their checks are integrated
  into this repository's existing CI.
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
