# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows SemVer. Pin a tag or commit SHA when loading `AUDIT.md`
into a deployment.

## [1.0.0]: first tagged release

### Changed (breaking)

- Renamed the distributed audit-agent system prompt from `SECURITY.md` to
  `AUDIT.md`. `SECURITY.md` is now this repository's own vulnerability-
  disclosure policy, resolving a filename collision with GitHub's native
  convention and with `abuzucom/agents`' own `SECURITY.md.example`
  adoption step. A deployment loading the old `SECURITY.md` path as its
  audit prompt needs its load path updated to `AUDIT.md`.

### Added

- `VERDICT_JSON` machine-readable companion to `AUDIT.md` section 6. Lets
  CI gate on structure instead of parsing the prose verdict line.
- `eval/`: a golden-corpus harness (`run_eval.py`) and eight fixtures
  validating verdicts across hard blockers, mode-specific behavior, and
  false-positive discipline.
- `.github/workflows/security-review.yml`: a reusable, adoptable reference
  CI workflow that runs `AUDIT.md` against a pull request and posts the
  report.
- `AGENTS.md`: a bespoke, security-work-specific instruction file for this
  repository (not a copy of `abuzucom/agents`' generic template). Adopts
  the branch-name and git-identity Claude Code hooks in full, plus the
  style/prose checker scripts, from `abuzucom/agents`.
- `docs/template-drift.md`, `upstream-files.json`,
  `scripts/check_upstream_drift.py`: drift tracking against the pinned
  `abuzucom/agents` commit, and a mechanism for reviewing upstream changes
  for adoption.
- `adopters/`: adoption-tracking scaffold.
- `LICENSE` (BSD 3-Clause, matching `abuzucom/agents`), `CONTRIBUTING.md`,
  and a proper project `SECURITY.md`.
- An "Organization Policy Suite" section in `README.md` documenting the
  relationship between foucault and `abuzucom/agents`.

## [Unreleased before 1.0.0]

- `SECURITY.md` (now `AUDIT.md`). Four review modes, 15 failure-mode
  classes, an 8-step workflow, hard blockers, and false-positive rules.
